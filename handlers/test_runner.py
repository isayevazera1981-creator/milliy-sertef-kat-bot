import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction
from storage import db
from gemini_service import GeminiService
from utils import send_safe_message
import keyboards

logger = logging.getLogger(__name__)
router = Router()
gemini = GeminiService()

def format_question_text(q_data: dict, index: int = None, total: int = None) -> str:
    """Красивое форматирование тестового вопроса."""
    header = f"📌 **Вопрос {index} из {total}**\n\n" if index and total else "📌 **Экзаменационный вопрос**\n\n"
    subject = q_data.get("subject", "Русский язык и литература")
    topic = q_data.get("topic", "")
    
    text = f"{header}🏷 **Предмет:** {subject}\n"
    if topic:
        text += f"📂 **Тема:** {topic}\n"
    text += f"\n❓ **Задание:**\n{q_data['question']}\n\n"
    
    text += "🔹 **Варианты ответа:**\n"
    for opt in q_data['options']:
        text += f"**{opt['key']})** {opt['text']}\n"
        
    text += "\nВыберите верный вариант ответа кнопками ниже 👇"
    return text

@router.message(F.text == "📚 Русский язык")
async def choose_russian_topic(message: Message):
    session = db.get_session(message.from_user.id)
    session.current_subject = "Русский язык"
    session.current_mode = "test_single"
    await message.answer(
        "📚 **Русский язык (Национальный сертификат)**\n\nВыберите раздел для тестирования или случайную тему:",
        reply_markup=keyboards.get_russian_topics_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "📖 Литература")
async def choose_lit_topic(message: Message):
    session = db.get_session(message.from_user.id)
    session.current_subject = "Литература"
    session.current_mode = "test_single"
    await message.answer(
        "📖 **Литература (Национальный сертификат)**\n\nВыберите тему или раздел для тестирования:",
        reply_markup=keyboards.get_lit_topics_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "🎯 Экспресс-тест (5 вопросов)")
async def start_express_test(message: Message):
    session = db.get_session(message.from_user.id)
    session.current_subject = "Русский язык и литература (Микс)"
    session.current_topic = "Комплексный экзамен"
    session.current_mode = "test_batch"
    
    await message.answer("🧠 **Генерирую экзаменационный блок из 5 вопросов по спецификации сертификата...**\nПожалуйста, подождите несколько секунд...")
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    try:
        questions = await gemini.generate_test_batch(
            subject="Русский язык и Литература",
            topic="Комплексный срез Национального сертификата (орфография, пунктуация, анализ текста, классическая литература)",
            count=5
        )
        if not questions:
            raise ValueError("Пустой список вопросов")
            
        session.batch_questions = questions
        session.batch_index = 0
        session.batch_correct = 0
        session.current_question = questions[0]
        
        q_text = format_question_text(questions[0], index=1, total=len(questions))
        await message.answer(q_text, reply_markup=keyboards.get_options_keyboard(questions[0]['options']), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка генерации экспресс-теста: {e}")
        await message.answer(
            f"⚠️ Не удалось сгенерировать тест: {e}\nУбедитесь, что GEMINI_API_KEY настроен в файле .env.",
            reply_markup=keyboards.get_main_menu_keyboard()
        )

@router.callback_query(F.data.startswith("topic_"))
async def handle_topic_selection(call: CallbackQuery):
    data = call.data
    session = db.get_session(call.from_user.id)
    
    if data.startswith("topic_ru_"):
        topic_name = data.replace("topic_ru_", "")
        session.current_subject = "Русский язык"
    else:
        topic_name = data.replace("topic_lit_", "")
        session.current_subject = "Литература"
        
    session.current_topic = None if topic_name == "random" else topic_name
    session.current_mode = "test_single"
    
    await call.message.edit_text(f"⏳ **ИИ Gemini генерирует вопрос по предмету «{session.current_subject}»...**", parse_mode="Markdown")
    await call.message.bot.send_chat_action(chat_id=call.message.chat.id, action=ChatAction.TYPING)
    
    try:
        q_data = await gemini.generate_test_question(session.current_subject, session.current_topic)
        session.current_question = q_data
        
        q_text = format_question_text(q_data)
        await call.message.edit_text(q_text, reply_markup=keyboards.get_options_keyboard(q_data['options']), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка генерации вопроса: {e}")
        await call.message.edit_text(
            f"⚠️ Не удалось сгенерировать вопрос: {e}\nПроверьте корректность GEMINI_API_KEY.",
            reply_markup=keyboards.get_main_menu_keyboard()
        )
    await call.answer()

@router.callback_query(F.data.startswith("ans_"))
async def handle_user_answer(call: CallbackQuery):
    chosen_key = call.data.replace("ans_", "").upper()
    session = db.get_session(call.from_user.id)
    q_data = session.current_question
    
    if not q_data:
        await call.message.answer("Вопрос уже устарел. Выберите новый тест в меню.", reply_markup=keyboards.get_main_menu_keyboard())
        await call.answer()
        return
        
    correct_key = str(q_data.get("correct_key", "")).strip().upper()
    is_correct = (chosen_key == correct_key)
    
    # Записываем в общую статистику
    db.record_answer(call.from_user.id, q_data.get("subject", session.current_subject or "Русский язык"), is_correct)
    
    if session.current_mode == "test_batch":
        if is_correct:
            session.batch_correct += 1
            
    # Собираем ответ пользователю
    result_emoji = "✅ **ВЕРНО!**" if is_correct else "❌ **НЕВЕРНО!**"
    user_choice_text = f"Ваш ответ: **{chosen_key}**"
    correct_choice_text = f"Правильный ответ: **{correct_key}**"
    
    explanation = q_data.get("explanation", "Разбор правила.")
    
    reply_msg = f"{result_emoji}\n\n{user_choice_text}\n{correct_choice_text}\n\n📖 **Разбор и правило:**\n{explanation}"
    
    has_batch_next = False
    if session.current_mode == "test_batch":
        if session.batch_index + 1 < len(session.batch_questions):
            has_batch_next = True
        else:
            # Конец батча
            total_b = len(session.batch_questions)
            pct = (session.batch_correct / total_b) * 100
            reply_msg += f"\n\n🏁 **Тест завершен!**\nИтоговый результат: **{session.batch_correct} из {total_b}** ({pct:.1f}%)."
            
    await call.message.reply(
        reply_msg, 
        reply_markup=keyboards.get_after_answer_keyboard(has_batch_next=has_batch_next),
        parse_mode="Markdown"
    )
    await call.answer()

@router.callback_query(F.data == "next_single_question")
async def handle_next_single(call: CallbackQuery):
    session = db.get_session(call.from_user.id)
    subject = session.current_subject or "Русский язык"
    topic = session.current_topic
    
    await call.message.answer(f"⏳ **Генерирую следующий вопрос по предмету «{subject}»...**", parse_mode="Markdown")
    await call.message.bot.send_chat_action(chat_id=call.message.chat.id, action=ChatAction.TYPING)
    
    try:
        q_data = await gemini.generate_test_question(subject, topic)
        session.current_question = q_data
        q_text = format_question_text(q_data)
        await call.message.answer(q_text, reply_markup=keyboards.get_options_keyboard(q_data['options']), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка следующего вопроса: {e}")
        await call.message.answer(f"⚠️ Ошибка: {e}", reply_markup=keyboards.get_main_menu_keyboard())
    await call.answer()

@router.callback_query(F.data == "batch_next")
async def handle_batch_next(call: CallbackQuery):
    session = db.get_session(call.from_user.id)
    session.batch_index += 1
    
    if session.batch_index < len(session.batch_questions):
        next_q = session.batch_questions[session.batch_index]
        session.current_question = next_q
        q_text = format_question_text(next_q, index=session.batch_index + 1, total=len(session.batch_questions))
        await call.message.answer(q_text, reply_markup=keyboards.get_options_keyboard(next_q['options']), parse_mode="Markdown")
    else:
        total_b = len(session.batch_questions)
        pct = (session.batch_correct / total_b) * 100
        await call.message.answer(
            f"🎉 **Экспресс-тест окончен!**\nВы набрали: **{session.batch_correct} из {total_b}** ({pct:.1f}%).\n\nВозвращаемся в меню.",
            reply_markup=keyboards.get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    await call.answer()

@router.callback_query(F.data == "explain_deep")
async def handle_explain_deep(call: CallbackQuery):
    session = db.get_session(call.from_user.id)
    q_data = session.current_question
    
    if not q_data:
        await call.message.answer("Задание не найдено для детального разбора.")
        await call.answer()
        return
        
    await call.message.answer("🔍 **ИИ формирует углубленный методический разбор задания...**", parse_mode="Markdown")
    await call.message.bot.send_chat_action(chat_id=call.message.chat.id, action=ChatAction.TYPING)
    
    try:
        deep_explanation = await gemini.explain_answer_deeply(
            question=q_data['question'],
            options=q_data['options'],
            chosen_key="пользователя",
            correct_key=q_data['correct_key'],
            original_explanation=q_data.get('explanation', '')
        )
        await send_safe_message(call.message, f"💡 **Углубленный методический разбор от ИИ Gemini:**\n\n{deep_explanation}")
    except Exception as e:
        logger.error(f"Ошибка глубокого разбора: {e}")
        await send_safe_message(call.message, f"⚠️ Ошибка формирования разбора: {e}")
    await call.answer()
