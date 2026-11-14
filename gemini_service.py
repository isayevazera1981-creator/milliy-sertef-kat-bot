import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types
import config

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.client: Optional[genai.Client] = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Ошибка инициализации Gemini Client: {e}")

    def is_configured(self) -> bool:
        return bool(self.client and self.api_key)

    async def _generate_with_fallback(
        self, 
        contents: Any, 
        system_instruction: str = config.SYSTEM_PROMPT,
        temperature: float = 0.7,
        response_mime_type: Optional[str] = None
    ) -> str:
        """
        Асинхронный вызов Gemini с автоматическим резервным переключением 
        между скоростными моделями для предотвращения зависаний.
        Поддерживает как текст, так и аудио/мультимодальные данные.
        """
        if not self.is_configured():
            raise ValueError("GEMINI_API_KEY не установлен. Пожалуйста, добавьте ключ в файл .env")

        models_to_try = [config.GEMINI_MODEL, config.GEMINI_FALLBACK_MODEL]

        last_error = None
        for model in models_to_try:
            try:
                cfg = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=temperature,
                    response_mime_type=response_mime_type,
                )
                
                # Таймаут 30 секунд для исключения подвисаний
                response = await asyncio.wait_for(
                    self.client.aio.models.generate_content(
                        model=model,
                        contents=contents,
                        config=cfg
                    ),
                    timeout=30.0
                )
                
                if response and response.text:
                    return response.text.strip()
            except asyncio.TimeoutError:
                logger.warning(f"Таймаут модели {model}, пробуем следующую...")
                last_error = TimeoutError("Превышено время ожидания ответа от ИИ.")
            except Exception as e:
                logger.warning(f"Ошибка при запросе к модели {model}: {e}")
                last_error = e

        raise RuntimeError(f"Не удалось получить ответ от Gemini: {last_error}")

    async def process_voice_message(self, audio_bytes: bytes, mime_type: str = "audio/ogg", context: Optional[str] = None) -> str:
        """
        Обработка голосового сообщения пользователя:
        1. Транскрипция речи пользователя в текст.
        2. Полный экспертный ответ репетитора на заданный вопрос.
        """
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        
        prompt = """Внимательно прослушай это голосовое сообщение от ученика.
1. В первой строке ОБЯЗАТЕЛЬНО напиши точную расшифровку того, что сказал ученик:
🗣 **Вы сказали:** «...точный текст из аудио...»

2. Затем сделай пустую строку и дай развернутый, понятный и экспертный ответ на этот вопрос по русскому языку или литературе, объясни правило или реши озвученную задачу для Национального сертификата.
"""
        if context:
            prompt += f"\nКонтекст сохраненного материала/файла:\n{context[:10000]}\n"

        return await self._generate_with_fallback(
            contents=[audio_part, prompt],
            temperature=0.7
        )

    async def summarize_text_material(self, text: str) -> str:
        """Создает краткий структурированный конспект учебного материала."""
        prompt = f"""Составь структурированный краткий конспект и анализ следующего учебного материала для подготовки к экзамену:

{text[:20000]}

Требования к оформлению:
1. 📌 **Главная тема и ключевая идея**
2. 🔑 **Основные правила / термины / сюжетные линии**
3. ⚠️ **Важные исключения и экзаменационные ловушки**
4. 💡 **Памятка для запоминания (лайфхак)**
"""
        return await self._generate_with_fallback(
            contents=prompt,
            temperature=0.6
        )

    async def generate_test_question(self, subject: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Генерирует один вопрос формата Национального сертификата с 4 вариантами ответа.
        Возвращает структурированный словарь.
        """
        topic_info = f"по теме «{topic}»" if topic else "по случайной теме спецификации экзамена"
        
        prompt = f"""Сгенерируй ОДНО экзаменационное тестовое задание по предмету: {subject} ({topic_info}).
Формат: строго в соответствии со спецификацией Национального сертификата (B2-C1 уровень).
Задание должно содержать 4 варианта ответа (A, B, C, D), из которых строго один верный.

Верни ответ ТОЛЬКО в виде валидного JSON-объекта (без лишних слов и markdown-тегов):
{{
  "subject": "{subject}",
  "topic": "Название темы (например, Правописание суффиксов или Анализ романа Отцы и дети)",
  "question": "Текст задания/вопроса...",
  "options": [
    {{"key": "A", "text": "Вариант 1"}},
    {{"key": "B", "text": "Вариант 2"}},
    {{"key": "C", "text": "Вариант 3"}},
    {{"key": "D", "text": "Вариант 4"}}
  ],
  "correct_key": "Буква верного ответа (A, B, C или D)",
  "explanation": "Подробный разбор ответа: формулировка правила, почему верный ответ именно этот, и какие ошибки в других вариантах."
}}
"""
        raw_text = await self._generate_with_fallback(
            contents=prompt,
            temperature=0.6,
            response_mime_type="application/json"
        )

        return self._clean_and_parse_json(raw_text)

    async def generate_test_batch(self, subject: str, topic: Optional[str] = None, count: int = 5) -> List[Dict[str, Any]]:
        """
        Генерирует пачку экзаменационных вопросов (например, 5 заданий).
        """
        topic_info = f"по теме «{topic}»" if topic else "разных ключевых тем спецификации экзамена"
        
        prompt = f"""Сгенерируй {count} тестовых заданий по предмету: {subject} ({topic_info}).
Формат заданий: строгий формат Национального сертификата. 
У каждого вопроса должно быть 4 варианта (A, B, C, D) и один верный ответ.

Верни ответ ТОЛЬКО в виде JSON-массива объектов:
[
  {{
    "subject": "{subject}",
    "topic": "Тема вопроса",
    "question": "Текст задания 1...",
    "options": [
      {{"key": "A", "text": "Вариант 1"}},
      {{"key": "B", "text": "Вариант 2"}},
      {{"key": "C", "text": "Вариант 3"}},
      {{"key": "D", "text": "Вариант 4"}}
    ],
    "correct_key": "A",
    "explanation": "Разбор и объяснение правила..."
  }}
]
"""
        raw_text = await self._generate_with_fallback(
            contents=prompt,
            temperature=0.6,
            response_mime_type="application/json"
        )

        data = self._clean_and_parse_json(raw_text)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "questions" in data:
            return data["questions"]
        return [data]

    async def answer_user_question(self, user_question: str, context: Optional[str] = None) -> str:
        """
        Интеллектуальный ответ репетитора на любой вопрос, задание, цитату или текст пользователя.
        """
        system_instruction = (
            config.SYSTEM_PROMPT + 
            "\nПользователь задал вопрос или прислал задание. Дай подробный, исчерпывающий, структурированный ответ с объяснением теории, примерами и подсказками для Национального сертификата. Оформляй красиво с использованием списков и выделения важного."
        )

        prompt = user_question
        if context:
            prompt = f"Контекст предыдущего задания:\n{context}\n\nВопрос пользователя:\n{user_question}"

        return await self._generate_with_fallback(
            contents=prompt,
            system_instruction=system_instruction,
            temperature=0.7
        )

    async def explain_answer_deeply(self, question: str, options: List[Dict[str, str]], chosen_key: str, correct_key: str, original_explanation: str) -> str:
        """
        Углубленный разбор задания от ИИ, если пользователь хочет дополнительное объяснение.
        """
        options_formatted = "\n".join([f"{opt['key']}) {opt['text']}" for opt in options])
        prompt = f"""Пользователь решает задание Национального сертификата:

Задание:
{question}

Варианты:
{options_formatted}

Выбранный пользователем ответ: {chosen_key}
Правильный ответ: {correct_key}
Краткий разбор: {original_explanation}

Задача:
Дай глубокий, понятный разбор этого задания для подготовки к Национальному сертификату:
1. Понятно сформулируй правило и алгоритм выбора.
2. Проанализируй каждый вариант (почему A, B, C, D верные или неверные).
3. Приведи памятку/лайфхак, чтобы не ошибаться в таких заданиях на экзамене.
"""
        return await self._generate_with_fallback(
            contents=prompt,
            temperature=0.6
        )

    async def generate_mcq_chunk(
        self, 
        topic: str, 
        start_num: int, 
        count: int, 
        context_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Генерирует порцию тестовых вопросов с вариантами A, B, C, D."""
        context_part = f"\nМатериал из предоставленного документа/файла:\n{context_text[:15000]}\n" if context_text else ""
        
        prompt = f"""Сгенерируй ровно {count} уникальных тестовых заданий по теме: «{topic}».
Номера заданий: с {start_num} по {start_num + count - 1}.
{context_part}
Требования:
- Уровень сложности: Национальный сертификат (B2-C1).
- Каждое задание должно иметь формулировку вопроса и ровно 4 варианта ответа (A, B, C, D).
- Ровно один вариант должен быть правильным.
- Формулируй вопросы четко, методически грамотно, без двусмысленностей.

Верни ответ ТОЛЬКО в виде JSON-массива:
[
  {{
    "question": "Текст задания...",
    "options": [
      {{"key": "A", "text": "Вариант 1"}},
      {{"key": "B", "text": "Вариант 2"}},
      {{"key": "C", "text": "Вариант 3"}},
      {{"key": "D", "text": "Вариант 4"}}
    ],
    "correct_key": "A"
  }}
]
"""
        raw_text = await self._generate_with_fallback(
            contents=prompt,
            temperature=0.7,
            response_mime_type="application/json"
        )
        parsed = self._clean_and_parse_json(raw_text)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict) and "questions" in parsed:
            return parsed["questions"]
        return [parsed]

    async def generate_written_chunk(
        self, 
        topic: str, 
        count: int = 10, 
        context_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Генерирует блок открытых письменных заданий с примерными ответами и критериями."""
        context_part = f"\nМатериал из предоставленного документа/файла:\n{context_text[:15000]}\n" if context_text else ""
        
        prompt = f"""Сгенерируй ровно {count} открытых письменных заданий (развернутый ответ, анализ текста, формулировка правил, мини-эссе) по теме: «{topic}».
{context_part}
Требования:
- Вопросы должны проверять глубокое понимание темы, аналитическое мышление и аргументацию.
- Для каждого задания составь примерный модельный ответ или критерии оценивания.

Верни ответ ТОЛЬКО в виде JSON-массива:
[
  {{
    "task": "Формулировка письменного задания...",
    "model_answer": "Примерный идеальный ответ ученика, ключевые тезисы и критерии оценивания."
  }}
]
"""
        raw_text = await self._generate_with_fallback(
            contents=prompt,
            temperature=0.7,
            response_mime_type="application/json"
        )
        parsed = self._clean_and_parse_json(raw_text)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict) and "questions" in parsed:
            return parsed["questions"]
        elif isinstance(parsed, dict) and "tasks" in parsed:
            return parsed["tasks"]
        return [parsed]

    async def generate_full_exam_pack(
        self, 
        topic: str, 
        context_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Параллельно генерирует полный экзаменационный комплект:
        - 50 тестовых вопросов с вариантами (25 + 25)
        - 10 письменных заданий
        """
        # Запуск параллельной генерации через asyncio.gather
        task1 = self.generate_mcq_chunk(topic=topic, start_num=1, count=25, context_text=context_text)
        task2 = self.generate_mcq_chunk(topic=topic, start_num=26, count=25, context_text=context_text)
        task3 = self.generate_written_chunk(topic=topic, count=10, context_text=context_text)

        mcq_part1, mcq_part2, written = await asyncio.gather(task1, task2, task3)
        
        all_mcq = list(mcq_part1) + list(mcq_part2)
        return {
            "topic": topic,
            "mcq": all_mcq,
            "written": written
        }

    def _clean_and_parse_json(self, raw_text: str) -> Any:
        """Очищает строку от markdown-блоков и парсит JSON."""
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}\nТекст: {text}")
            # Попытка вырезать первый JSON блок {} или []
            start_dict = text.find("{")
            end_dict = text.rfind("}")
            start_arr = text.find("[")
            end_arr = text.rfind("]")
            
            if start_dict != -1 and end_dict != -1 and (start_arr == -1 or start_dict < start_arr):
                return json.loads(text[start_dict:end_dict + 1])
            elif start_arr != -1 and end_arr != -1:
                return json.loads(text[start_arr:end_arr + 1])
            raise e
