import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from storage import db
import keyboards

logger = logging.getLogger(__name__)
router = Router()

START_TEXT = """👋 **Добро пожаловать в тренажер Национального сертификата!**

Я умный бот-репетитор на базе передовой модели **Google Gemini**. Я помогу вам подготовиться к экзамену по **русскому языку и литературе** на высший балл!

⚡ **Что я умею:**
• 📚 **Генерация тестов** по спецификации Национального сертификата (с 4 вариантами ответов).
• 💡 **Мгновенный разбор каждого вопроса**: ИИ подробно объясняет правила и ошибки.
• 🎯 **Экспресс-экзамены** для проверки знаний на скорость и точность.
• 💬 **Индивидуальный ИИ-репетитор**: пришлите мне любое сложное задание, текст или вопрос — я решу и разложу всё по полочкам!
• 📊 **Статистика**: отслеживание прогресса и процента правильных ответов.

Выберите раздел в меню ниже 👇
"""

ABOUT_CERTIFICATE_TEXT = """📋 **О Национальном сертификате по русскому языку и литературе**

Национальный сертификат подтверждает уровень владения языком и литературой (уровни B+, A, A+ дают льготные и максимальные баллы при поступлении в вузы).

📌 **Структура экзамена:**
1. **Русский язык:**
   • Орфография (корни, приставки, суффиксы, слитное/дефисное написание).
   • Пунктуация (простые и сложные предложения, обособления, прямая речь).
   • Морфология и грамматика (нормы склонения, спряжения, частей речи).
   • Синтаксис и культура речи (построение сложных предложений, стилистика).
   • Лексика, фразеология и комплексный анализ текста.

2. **Литература:**
   • Шедевры русской классики XIX века (Пушкин, Лермонтов, Гоголь, Толстой, Достоевский, Чехов и др.).
   • Литература XX века (Бунин, Куприн, Булгаков, поэзия Серебряного века, литература о войне).
   • Теория литературы (роды, жанры, стихотворные размеры, тропы: метафоры, эпитеты, гиперболы).
   • Анализ фрагментов произведений и цитатный материал.

💡 **Совет от ИИ:** Регулярно решайте по 10-15 тестов в день и всегда читайте подробный разбор ошибок!
"""

@router.message(CommandStart())
async def cmd_start(message: Message):
    session = db.get_session(message.from_user.id)
    session.current_mode = "menu"
    await message.answer(START_TEXT, parse_mode="Markdown", reply_markup=keyboards.get_main_menu_keyboard())

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(START_TEXT, parse_mode="Markdown", reply_markup=keyboards.get_main_menu_keyboard())

@router.message(F.text == "ℹ️ О сертификате")
async def show_about_certificate(message: Message):
    await message.answer(ABOUT_CERTIFICATE_TEXT, parse_mode="Markdown", reply_markup=keyboards.get_main_menu_keyboard())

@router.message(F.text == "📊 Моя статистика")
async def show_stats(message: Message):
    session = db.get_session(message.from_user.id)
    
    total = session.total_answered
    correct = session.total_correct
    accuracy = (correct / total * 100) if total > 0 else 0
    
    ru_stat = session.stats_by_subject.get("Русский язык", {"total": 0, "correct": 0})
    lit_stat = session.stats_by_subject.get("Литература", {"total": 0, "correct": 0})
    
    ru_pct = (ru_stat["correct"] / ru_stat["total"] * 100) if ru_stat["total"] > 0 else 0
    lit_pct = (lit_stat["correct"] / lit_stat["total"] * 100) if lit_stat["total"] > 0 else 0

    stats_msg = f"""📊 **Ваша статистика подготовки:**

Всего решено заданий: **{total}**
Правильных ответов: **{correct}**
Общая точность: **{accuracy:.1f}%**

📚 **Русский язык:**
• Решено: {ru_stat['total']} | Верно: {ru_stat['correct']} ({ru_pct:.1f}%)

📖 **Литература:**
• Решено: {lit_stat['total']} | Верно: {lit_stat['correct']} ({lit_pct:.1f}%)

{("🔥 Отличный темп! Продолжайте в том же духе!" if accuracy >= 75 and total >= 5 else "💡 Больше практики — и результат пойдет вверх! Решайте тесты с разбором от ИИ.")}
"""
    await message.answer(stats_msg, parse_mode="Markdown", reply_markup=keyboards.get_main_menu_keyboard())

@router.callback_query(F.data == "nav_main_menu")
async def callback_nav_main_menu(call: CallbackQuery):
    session = db.get_session(call.from_user.id)
    session.current_mode = "menu"
    session.current_question = None
    session.batch_questions = []
    
    await call.message.answer("Главное меню:", reply_markup=keyboards.get_main_menu_keyboard())
    await call.answer()
