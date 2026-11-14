import logging
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

def split_text(text: str, max_len: int = 3800) -> list[str]:
    """Разбивает длинный текст по строкам, не разрывая слова и разметку посередине."""
    if len(text) <= max_len:
        return [text]
    
    chunks = []
    lines = text.split("\n")
    current_chunk = []
    current_len = 0
    
    for line in lines:
        if current_len + len(line) + 1 > max_len:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            while len(line) > max_len:
                chunks.append(line[:max_len])
                line = line[max_len:]
        current_chunk.append(line)
        current_len += len(line) + 1
        
    if current_chunk:
        chunks.append("\n".join(current_chunk))
        
    return chunks

async def send_safe_message(message: Message, text: str, reply_markup=None):
    """
    Безопасная отправка сообщения с защитой от ошибок парсинга Markdown в Telegram.
    Если Telegram не может распарсить спецсимволы разметки, отправляет чистым текстом.
    """
    chunks = split_text(text, max_len=3800)
    for i, chunk in enumerate(chunks):
        markup = reply_markup if i == len(chunks) - 1 else None
        try:
            await message.answer(chunk, parse_mode="Markdown", reply_markup=markup)
        except TelegramBadRequest as e:
            logger.warning(f"Ошибка парсинга Markdown Telegram: {e}. Отправка в обычном текстовом режиме.")
            await message.answer(chunk, parse_mode=None, reply_markup=markup)
        except Exception as e:
            logger.warning(f"Ошибка отправки: {e}. Пробуем без форматирования.")
            await message.answer(chunk, parse_mode=None, reply_markup=markup)
