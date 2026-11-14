from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура бота."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📑 Создать тест в Word (50+10)")],
            [KeyboardButton(text="📚 Русский язык"), KeyboardButton(text="📖 Литература")],
            [KeyboardButton(text="🎯 Экспресс-тест (5 вопросов)"), KeyboardButton(text="💬 Спросить у ИИ")],
            [KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="ℹ️ О сертификате")]
        ],
        resize_keyboard=True
    )

def get_russian_topics_keyboard() -> InlineKeyboardMarkup:
    """Темы по русскому языку."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Орфография (правила правописания)", callback_data="topic_ru_Орфография")],
            [InlineKeyboardButton(text="✒️ Пунктуация (знаки препинания)", callback_data="topic_ru_Пунктуация")],
            [InlineKeyboardButton(text="🧩 Морфология и грамматика", callback_data="topic_ru_Морфология")],
            [InlineKeyboardButton(text="💬 Синтаксис и культура речи", callback_data="topic_ru_Синтаксис")],
            [InlineKeyboardButton(text="📜 Лексика и фразеология", callback_data="topic_ru_Лексика")],
            [InlineKeyboardButton(text="📑 Комплексный анализ текста", callback_data="topic_ru_Текст")],
            [InlineKeyboardButton(text="🎲 Случайная тема (как на экзамене)", callback_data="topic_ru_random")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="nav_main_menu")]
        ]
    )

def get_lit_topics_keyboard() -> InlineKeyboardMarkup:
    """Темы по литературе."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 Русская классика XIX века", callback_data="topic_lit_Классика 19 века")],
            [InlineKeyboardButton(text="🏛️ Литература XX века", callback_data="topic_lit_Литература 20 века")],
            [InlineKeyboardButton(text="🎭 Теория литературы, жанры и тропы", callback_data="topic_lit_Теория литературы")],
            [InlineKeyboardButton(text="📜 Поэзия и анализ стихотворных текстов", callback_data="topic_lit_Поэзия")],
            [InlineKeyboardButton(text="🧩 Знание персонажей и цитат", callback_data="topic_lit_Персонажи")],
            [InlineKeyboardButton(text="🎲 Случайная тема (как на экзамене)", callback_data="topic_lit_random")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="nav_main_menu")]
        ]
    )

def get_test_mode_keyboard(subject: str) -> InlineKeyboardMarkup:
    """Выбор режима тестирования: 1 вопрос или мини-экзамен."""
    prefix = "ru" if "рус" in subject.lower() else "lit"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ По одному вопросу (с разбором)", callback_data=f"mode_single_{prefix}")],
            [InlineKeyboardButton(text="📝 Блок из 5 вопросов (экзамен)", callback_data=f"mode_batch_{prefix}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_main_menu")]
        ]
    )

def get_options_keyboard(options: list) -> InlineKeyboardMarkup:
    """Кнопки ответов A, B, C, D."""
    buttons = []
    # Сетка: [A, B], [C, D]
    row1 = []
    row2 = []
    for opt in options:
        btn = InlineKeyboardButton(text=f"Вариант {opt['key']}", callback_data=f"ans_{opt['key']}")
        if opt['key'] in ['A', 'B']:
            row1.append(btn)
        else:
            row2.append(btn)
    
    inline_kb = []
    if row1:
        inline_kb.append(row1)
    if row2:
        inline_kb.append(row2)
    inline_kb.append([InlineKeyboardButton(text="❌ Завершить тест", callback_data="nav_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=inline_kb)

def get_file_action_keyboard() -> InlineKeyboardMarkup:
    """Меню действий с загруженным файлом."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📑 Создать тест в Word (50+10)", callback_data="fileact_word_exam")],
            [InlineKeyboardButton(text="📝 Краткий конспект и анализ файла", callback_data="fileact_summary")],
            [InlineKeyboardButton(text="🎯 Экспресс-тест по файлу (5 вопросов)", callback_data="fileact_quiz")],
            [InlineKeyboardButton(text="💬 Задать вопрос по файлу", callback_data="fileact_ask")],
            [InlineKeyboardButton(text="❌ Удалить файл из памяти", callback_data="fileact_delete")]
        ]
    )

def get_after_answer_keyboard(has_batch_next: bool = False) -> InlineKeyboardMarkup:
    """Кнопки после ответа: разбор, следующий вопрос или меню."""
    kb = []
    kb.append([InlineKeyboardButton(text="💡 Глубокий разбор от ИИ", callback_data="explain_deep")])
    if has_batch_next:
        kb.append([InlineKeyboardButton(text="➡️ Следующий вопрос", callback_data="batch_next")])
    else:
        kb.append([InlineKeyboardButton(text="🔄 Еще один вопрос", callback_data="next_single_question")])
    kb.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="nav_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)
