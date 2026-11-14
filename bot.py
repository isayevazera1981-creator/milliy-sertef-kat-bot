import asyncio
import logging
import sys

# Обеспечиваем корректный вывод UTF-8 в консоли Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
from handlers import start, test_runner, doc_exam, ai_chat

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("telegram_gemini_bot")

async def handle_ping(request):
    """Эндпоинт для проверки здоровья и пинга cron-job."""
    return web.Response(text="OK. Bot is running online 24/7!", status=200)

async def start_web_server():
    """Запуск легкого HTTP-сервера для Render и Cron-Job."""
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    try:
        await site.start()
        logger.info(f"🌐 HTTP-сервер для Cron-Job успешно запущен на порту {port}")
    except Exception as e:
        logger.warning(f"Не удалось запустить HTTP-сервер на порту {port}: {e}")

async def main():
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не указан в файле .env!")
        print("\n" + "="*60)
        print("ВНИМАНИЕ: Необходимо настроить токен Telegram-бота в файле .env:")
        print("TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather")
        print("GEMINI_API_KEY=ваш_ключ_от_Google_AI_Studio")
        print("="*60 + "\n")
        return

    if not config.GEMINI_API_KEY:
        logger.warning("⚠️ ПРЕДУПРЕЖДЕНИЕ: GEMINI_API_KEY не указан в .env! ИИ-функции будут недоступны до добавления ключа.")

    bot = Bot(
        token=config.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    
    dp = Dispatcher()
    
    # Регистрация роутеров в строгом порядке
    dp.include_router(start.router)
    dp.include_router(doc_exam.router)
    dp.include_router(test_runner.router)
    dp.include_router(ai_chat.router)  # В конце, так как ловит любой свободный текст

    logger.info("🚀 Бот успешно инициализирован. Запуск long-polling в режиме 24/7...")
    print(f"Используемая модель Gemini: {config.GEMINI_MODEL} (резервная: {config.GEMINI_FALLBACK_MODEL})")
    
    # Запуск фонового HTTP-сервера для Render и Cron-Job
    await start_web_server()

    # 24/7 цикл с защитой от разрывов соединения и автоматическим переподключением
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot, handle_signals=False)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Бот остановлен пользователем.")
            break
        except Exception as e:
            logger.error(f"⚠️ Ошибка соединения с Telegram: {e}. Автоматическое переподключение через 5 секунд...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
