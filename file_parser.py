import os
import logging
from typing import Optional
import pypdf
import docx

logger = logging.getLogger(__name__)

def extract_text_from_file(file_path: str, max_chars: int = 50000) -> str:
    """
    Извлекает текст из файлов форматов PDF, DOCX, TXT.
    Ограничивает максимальный размер текста до max_chars символов для оптимальной обработки.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    try:
        if ext == ".pdf":
            reader = pypdf.PdfReader(file_path)
            pages_text = []
            for i, page in enumerate(reader.pages):
                extracted = page.extract_text()
                if extracted:
                    pages_text.append(extracted)
                if sum(len(p) for p in pages_text) >= max_chars:
                    break
            text = "\n\n".join(pages_text)

        elif ext in [".docx", ".doc"]:
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)

        elif ext in [".txt", ".md"]:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="cp1251", errors="ignore") as f:
                    text = f.read()
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {ext}. Поддерживаются PDF, DOCX, TXT.")

    except Exception as e:
        logger.error(f"Ошибка при чтении файла {file_path}: {e}")
        raise e

    cleaned_text = text.strip()
    if len(cleaned_text) > max_chars:
        cleaned_text = cleaned_text[:max_chars] + "\n...[текст сокращен для анализа]..."

    return cleaned_text
