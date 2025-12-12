import asyncio
import logging
import sys
import platform

from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler

#импорты функций из скриптов проекта
from token_reader import get_token
from tg_handlers import start_command, help_command, catalog_command





def setup_logging():
    """Настройка записи ВСЕХ логов в файл"""

    # Создаем папку для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Файлы для логов
    all_logs_file = log_dir / "all.log"  # ВСЕ логи (включая DEBUG)
    info_logs_file = log_dir / "info.log"  # Только INFO и выше
    errors_logs_file = log_dir / "errors.log"  # Только ERROR и выше

    # Корневой логгер
    root_logger = logging.getLogger()

    # Очищаем старые обработчики (чтобы не дублировались при повторном вызове)
    root_logger.handlers.clear()

    root_logger.setLevel(logging.DEBUG) #для отладки
    # === ВАЖНО ===
    # Устанавливаем INFO уровень на корневом логгере
    # Это позволит записывать ВСЕ сообщения кроме DEBUG

    # DEBUG(10)     ← НЕ пишутся при level INFO
    # INFO(20)      ← ПИШУТСЯ
    # WARNING(30)   ← ПИШУТСЯ
    # ERROR(40)     ← ПИШУТСЯ
    # CRITICAL(50)  ← ПИШУТСЯ

    # Формат сообщений
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',  # ← Добавлен номер строки
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Файл для ВСЕХ логов (включая DEBUG)
    debug_handler = logging.FileHandler(all_logs_file, encoding='utf-8')
    debug_handler.setLevel(logging.DEBUG)  # Принимаем ВСЕ уровни
    debug_handler.setFormatter(formatter)
    root_logger.addHandler(debug_handler)

    # 2. Файл для INFO и выше
    info_handler = logging.FileHandler(info_logs_file, encoding='utf-8')
    info_handler.setLevel(logging.INFO)  # Только INFO и выше
    info_handler.setFormatter(formatter)
    root_logger.addHandler(info_handler)

    # 3. Файл только для ошибок
    error_handler = logging.FileHandler(errors_logs_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)  # Только ERROR и CRITICAL
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # 4. Консоль (только WARNING и выше, чтобы не засорять)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Режим отладки, потом можно поменять на WARNING
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.info(f"Логирование настроено")
    logging.info(f"Все логи: {all_logs_file}")
    logging.info(f"Инфо-логи: {info_logs_file}")
    logging.info(f"Логи ошибок: {errors_logs_file}")

    # Уменьшаем уровень логирования для библиотеки httpx
    logging.getLogger("httpx").setLevel(logging.WARNING)
    # ===========================

    # Дополнительно: убираем логи от других шумных библиотек (опционально)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def main():
    """Основная асинхронная функция бота."""
    # 1. Настраиваем логирование
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 50)
    logger.info("Запуск Telegram бота-витрины")
    logger.info("=" * 50)

    # 2. Получаем токен из файла
    try:
        # Если файл не найден или пуст, программа завершится в token_reader.read_bot_token()
        BOT_TOKEN = get_token()
    except SystemExit:
        logger.error("Не удалось получить токен. Завершение работы.")
        return
    logger.info("Токен успешно получен, инициализируем бота...")

    # 3. Инициализация бота
    try:
        # Создаем Application
        application = Application.builder().token(BOT_TOKEN).build()

        #loop = asyncio.new_event_loop()
        #asyncio.set_event_loop(loop)

        # Получаем информацию о боте
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        bot_info = loop.run_until_complete(application.bot.get_me())

        logger.info(f"Бот: @{bot_info.username} (ID: {bot_info.id})")

        # Регистрируем команды
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("catalog", catalog_command))

        logger.info(f"Зарегистрировано команд: {len(application.handlers[0])}")

        # 4. Запуск бота
        logger.info("Запуск телеграм бота...")
        application.run_polling(drop_pending_updates=True)

    except ImportError as e:
        logger.error(f"Ошибка импорта: {e}")
        logger.info("Установите: pip install python-telegram-bot")
    except Exception as e:
        logger.exception(f"Ошибка: {e}")
    finally:
        logger.info("Бот остановлен")
        logger.info("=" * 50)

if __name__ == "__main__":
    #for linux
    #asyncio.run(main())

    #Windows спотыкается, поэтому запускаем так

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    main()