import os
import logging
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ChatAction

from gemini_service import GeminiService
from docx_generator import create_exam_document
from file_parser import extract_text_from_file
from utils import send_safe_message
import keyboards

logger = logging.getLogger(__name__)
router = Router()
gemini = GeminiService()

class DocExamState(StatesGroup):
    waiting_for_input = State()

DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

PROMPT_GUIDE_TEXT = """📑 **Генерация экзаменационного теста в Word (.docx) (50 + 10)**

Вы можете отправить:
1️⃣ **Название темы** (например: *«Лермонтов: жизнь и творчество»*, *«Правописание Н и НН в причастиях»*, *«Сложноподчинённые предложения»*).
2️⃣ **Файл (PDF, Word .docx или TXT)** — в подписи к файлу (caption) укажите, по какой теме или разделу составить тест.

⚡ **Искусственный интеллект Gemini составит:**
• Не менее **50 тестовых вопросов** с вариантами (A, B, C, D)
• **10 открытых письменных заданий** с модельными ответами
• **Итоговую таблицу ключей** (1–50)
и оформит всё в красивый документ Word! 📄

Напишите тему прямо сюда или отправьте файл 👇
"""

@router.message(F.text == "📑 Создать тест в Word (50+10)")
async def start_doc_generation(message: Message, state: FSMContext):
    await state.set_state(DocExamState.waiting_for_input)
    await send_safe_message(message, PROMPT_GUIDE_TEXT)

@router.message(DocExamState.waiting_for_input, F.text)
async def process_topic_text(message: Message, state: FSMContext):
    topic = message.text.strip()
    
    # Отмена или переход в меню
    if topic in ["/start", "📚 Русский язык", "📖 Литература", "🎯 Экспресс-тест (5 вопросов)", "💬 Спросить у ИИ", "📊 Моя статистика", "ℹ️ О сертификате"]:
        await state.clear()
        return

    await state.clear()
    await generate_and_send_exam(message, topic=topic, context_text=None)

@router.message(DocExamState.waiting_for_input, F.document)
async def process_document_in_state(message: Message, state: FSMContext):
    """Когда пользователь нажал кнопку 'Создать тест в Word' и прислал файл."""
    await state.clear()
    await handle_incoming_document(message, auto_generate=True)

@router.message(F.document)
async def process_document_direct(message: Message, state: FSMContext):
    """Когда пользователь просто прислал файл."""
    await state.clear()
    caption_lower = (message.caption or "").lower()
    has_test_intent = any(word in caption_lower for word in ["тест", "test", "savol", "состав", "создай", "сделай", "придумай"])
    await handle_incoming_document(message, auto_generate=has_test_intent)

async def handle_incoming_document(message: Message, auto_generate: bool = False):
    """Общий обработчик загрузки документа."""
    doc = message.document
    file_name = doc.file_name or "document"
    ext = os.path.splitext(file_name)[1].lower()

    if ext not in [".pdf", ".docx", ".doc", ".txt", ".md"]:
        await message.answer("⚠️ Пожалуйста, отправляйте файлы форматов PDF, Word (.docx) или TXT.", parse_mode=None)
        return

    topic = message.caption.strip() if message.caption else f"По материалу: {os.path.splitext(file_name)[0]}"
    
    # Отправляем сообщение без Markdown разметки, чтобы избежать ошибок с символами в имени файла
    status_msg = await message.answer(f"📥 Файл «{file_name}» получен.\nАнализирую текст...", parse_mode=None)
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # Скачивание файла
    dest_path = os.path.join(DOWNLOADS_DIR, f"{message.from_user.id}_{file_name}")
    try:
        file = await message.bot.get_file(doc.file_id)
        await message.bot.download_file(file.file_path, destination=dest_path)

        # Извлечение текста
        extracted_text = extract_text_from_file(dest_path, max_chars=40000)
        
        if not extracted_text:
            await status_msg.edit_text("⚠️ Не удалось извлечь текст из файла или файл пуст.", parse_mode=None)
            return

        # Сохраняем в сессию пользователя
        from storage import db
        session = db.get_session(message.from_user.id)
        session.saved_file_name = file_name
        session.saved_file_text = extracted_text
        session.saved_file_path = dest_path

        await status_msg.delete()

        if auto_generate:
            await generate_and_send_exam(message, topic=topic, context_text=extracted_text)
        else:
            # Спрашиваем, что сделать с файлом
            prompt_file = (
                f"📁 Файл «{file_name}» успешно сохранен в памяти!\n"
                f"📊 Объем извлеченного текста: {len(extracted_text)} символов.\n\n"
                f"Выберите действие с этим файлом ниже 👇"
            )
            await message.answer(prompt_file, reply_markup=keyboards.get_file_action_keyboard(), parse_mode=None)

    except Exception as e:
        logger.error(f"Ошибка обработки документа: {e}")
        await message.answer(f"⚠️ Ошибка при обработке файла: {e}", parse_mode=None)

@router.callback_query(F.data == "fileact_word_exam")
async def handle_fileact_word(call):
    from storage import db
    session = db.get_session(call.from_user.id)
    if not session.saved_file_text:
        await call.message.answer("⚠️ Файл не найден в памяти. Пожалуйста, отправьте файл снова.")
        await call.answer()
        return

    await call.answer()
    topic = f"По материалу: {session.saved_file_name}"
    await generate_and_send_exam(call.message, topic=topic, context_text=session.saved_file_text)

@router.callback_query(F.data == "fileact_summary")
async def handle_fileact_summary(call):
    from storage import db
    session = db.get_session(call.from_user.id)
    if not session.saved_file_text:
        await call.message.answer("⚠️ Файл не найден в памяти.")
        await call.answer()
        return

    await call.message.answer("📝 **Составляю структурированный конспект по файлу...**", parse_mode="Markdown")
    await call.message.bot.send_chat_action(chat_id=call.message.chat.id, action=ChatAction.TYPING)
    await call.answer()

    try:
        summary = await gemini.summarize_text_material(session.saved_file_text)
        await send_safe_message(call.message, f"📚 **Краткий конспект и анализ файла «{session.saved_file_name}»:**\n\n{summary}")
    except Exception as e:
        logger.error(f"Ошибка конспекта: {e}")
        await call.message.answer(f"⚠️ Ошибка при создании конспекта: {e}")

@router.callback_query(F.data == "fileact_quiz")
async def handle_fileact_quiz(call):
    from storage import db
    session = db.get_session(call.from_user.id)
    if not session.saved_file_text:
        await call.message.answer("⚠️ Файл не найден в памяти.")
        await call.answer()
        return

    await call.message.answer("🎯 **Генерирую тест из 5 вопросов по содержанию вашего файла...**", parse_mode="Markdown")
    await call.message.bot.send_chat_action(chat_id=call.message.chat.id, action=ChatAction.TYPING)
    await call.answer()

    try:
        from handlers.test_runner import format_question_text
        questions = await gemini.generate_test_batch(
            subject=f"По файлу «{session.saved_file_name}»",
            topic=session.saved_file_text[:10000],
            count=5
        )
        if not questions:
            raise ValueError("Пустой список вопросов")

        session.current_subject = f"По файлу: {session.saved_file_name}"
        session.current_mode = "test_batch"
        session.batch_questions = questions
        session.batch_index = 0
        session.batch_correct = 0
        session.current_question = questions[0]

        q_text = format_question_text(questions[0], index=1, total=len(questions))
        await call.message.answer(q_text, reply_markup=keyboards.get_options_keyboard(questions[0]['options']), parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка генерации теста по файлу: {e}")
        await call.message.answer(f"⚠️ Ошибка: {e}")

@router.callback_query(F.data == "fileact_ask")
async def handle_fileact_ask(call):
    from storage import db
    session = db.get_session(call.from_user.id)
    session.current_mode = "ai_tutor"
    await call.message.answer(
        f"💬 **Файл «{session.saved_file_name}» активен в памяти!**\n\n"
        f"Теперь вы можете написать или наговорить **голосовым сообщением** любой вопрос по содержанию этого файла — ИИ ответит с учетом этого документа.",
        parse_mode="Markdown"
    )
    await call.answer()

@router.callback_query(F.data == "fileact_delete")
async def handle_fileact_delete(call):
    from storage import db
    session = db.get_session(call.from_user.id)
    if session.saved_file_path and os.path.exists(session.saved_file_path):
        try:
            os.remove(session.saved_file_path)
        except Exception:
            pass
    session.saved_file_name = None
    session.saved_file_text = None
    session.saved_file_path = None
    await call.message.edit_text("🗑️ Файл успешно удален из памяти бота.")
    await call.answer()

async def generate_and_send_exam(message: Message, topic: str, context_text: str = None):
    """
    Генерирует 50 тестовых + 10 письменных вопросов и отправляет готовый .docx файл пользователю.
    """
    progress_text = (
        f"🧠 ИИ Gemini генерирует полный экзаменационный комплект:\n"
        f"Тема: «{topic}»\n\n"
        f"⏳ Шаг 1: Составление 50 тестовых заданий с вариантами (A, B, C, D)...\n"
        f"⏳ Шаг 2: Разработка 10 открытых письменных заданий и критериев...\n"
        f"⏳ Шаг 3: Формирование таблицы ключей и вёрстка документа Word...\n\n"
        f"Это займет около 10–20 секунд. Пожалуйста, подождите..."
    )
    progress_msg = await message.answer(progress_text, parse_mode=None)
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)

    try:
        # Генерация пака тестов через Gemini
        exam_pack = await gemini.generate_full_exam_pack(topic=topic, context_text=context_text)
        
        mcq_list = exam_pack.get("mcq", [])
        written_list = exam_pack.get("written", [])

        if not mcq_list:
            raise ValueError("Не удалось сформировать тестовые вопросы.")

        await progress_msg.edit_text("📄 Задания успешно сгенерированы! Формирую файл Microsoft Word (.docx)...", parse_mode=None)

        # Создание стильного Word-документа
        doc_path = create_exam_document(
            topic=topic,
            multiple_choice_questions=mcq_list,
            written_questions=written_list
        )

        doc_file = FSInputFile(doc_path, filename=os.path.basename(doc_path))

        success_caption = (
            f"✅ Экзаменационный сборник успешно сформирован!\n\n"
            f"📌 Тема: {topic}\n"
            f"🔢 Содержание сборника:\n"
            f"• Часть I: 50 тестовых вопросов (A, B, C, D)\n"
            f"• Часть II: 10 открытых письменных заданий\n"
            f"• Часть III: Таблица ключей ответов и модельные критерии\n\n"
            f"Формат: Microsoft Word (.docx)"
        )

        try:
            await message.answer_document(
                document=doc_file,
                caption=success_caption,
                parse_mode=None
            )
        except Exception as e:
            logger.warning(f"Ошибка отправки документа: {e}")
            await message.answer_document(
                document=doc_file,
                caption=f"Экзаменационный тест: {topic}"
            )
        await progress_msg.delete()

    except Exception as e:
        logger.error(f"Ошибка при составлении теста: {e}")
        await progress_msg.edit_text(
            f"⚠️ Произошла ошибка при составлении теста: {e}\nПожалуйста, попробуйте еще раз или сформулируйте тему немного конкретнее.",
            parse_mode=None
        )
