import io
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatAction
from storage import db
from gemini_service import GeminiService
from utils import send_safe_message
import keyboards

logger = logging.getLogger(__name__)
router = Router()
gemini = GeminiService()

AI_TUTOR_PROMPT_INFO = """💬 **Режим «Вопрос к ИИ-репетитору» активен!**

Вы можете написать или **наговорить голосом** абсолютно любой вопрос по русскому языку и литературе:
• *«Объясни правописание Н и НН в причастиях и отглагольных прилагательных»*
• *«В чем конфликт Базарова и Павла Петровича в романе "Отцы и дети"?»*
• *«Реши это задание: Укажите ряд, где во всех словах пропущена безударная чередующаяся гласная...»*
• Или отправьте голосовое сообщение — ИИ поймет вашу речь и даст полный ответ!

Напишите или надиктуйте вопрос прямо в чат 👇
"""

@router.message(F.text == "💬 Спросить у ИИ")
async def enter_ai_tutor_mode(message: Message):
    session = db.get_session(message.from_user.id)
    session.current_mode = "ai_tutor"
    await message.answer(AI_TUTOR_PROMPT_INFO, parse_mode="Markdown")

@router.message(F.voice | F.audio)
async def handle_voice_message(message: Message):
    """
    Обработка голосового сообщения пользователя через мультимодальный Gemini.
    """
    session = db.get_session(message.from_user.id)
    
    status_msg = await message.answer("🎧 **Слушаю ваше голосовое сообщение и формирую ответ...**", parse_mode="Markdown")
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    file_id = message.voice.file_id if message.voice else message.audio.file_id
    mime_type = "audio/ogg" if message.voice else (message.audio.mime_type or "audio/mp3")

    try:
        file_info = await message.bot.get_file(file_id)
        audio_io = io.BytesIO()
        await message.bot.download_file(file_info.file_path, destination=audio_io)
        audio_bytes = audio_io.getvalue()

        # Формируем контекст (если есть сохраненный файл или вопрос теста)
        context = session.saved_file_text
        if session.current_question and not context:
            context = f"Вопрос теста: {session.current_question.get('question', '')}\nПравильный ответ: {session.current_question.get('correct_key', '')}"

        ai_response = await gemini.process_voice_message(
            audio_bytes=audio_bytes, 
            mime_type=mime_type, 
            context=context
        )
        
        await status_msg.delete()
        await send_safe_message(message, ai_response)

    except Exception as e:
        logger.error(f"Ошибка обработки голосового сообщения: {e}")
        await status_msg.edit_text(f"⚠️ Не удалось распознать голосовое сообщение: {e}")

@router.message(F.text)
async def handle_any_user_text(message: Message):
    """
    Обработка любого текстового вопроса пользователя с помощью ИИ Gemini.
    """
    user_text = message.text.strip()
    
    # Игнорируем стандартные служебные кнопки, если они вдруг дошли сюда
    if user_text in [
        "📚 Русский язык", "📖 Литература", 
        "🎯 Экспресс-тест (5 вопросов)", "💬 Спросить у ИИ", 
        "📊 Моя статистика", "ℹ️ О сертификате", 
        "📑 Создать тест в Word (50+10)"
    ]:
        return

    session = db.get_session(message.from_user.id)
    
    await message.answer("🤖 **ИИ Gemini анализирует ваш вопрос...**", parse_mode="Markdown")
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    context = session.saved_file_text
    if session.current_question and not context:
        context = f"Вопрос теста: {session.current_question.get('question', '')}\nПравильный ответ: {session.current_question.get('correct_key', '')}"
        
    try:
        ai_response = await gemini.answer_user_question(user_text, context=context)
        await send_safe_message(message, ai_response)
            
    except Exception as e:
        logger.error(f"Ошибка ответа ИИ: {e}")
        await send_safe_message(
            message,
            f"⚠️ Не удалось получить ответ от ИИ: {e}\nПожалуйста, убедитесь, что ваш GEMINI_API_KEY активен.",
            reply_markup=keyboards.get_main_menu_keyboard()
        )
