"""
Copyright (c) 2025 master-nio(Dashkevich Alexander)

Лицензировано под MIT License.
См. файл LICENSE в корне проекта.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

#файл с токеном должен находится в той же папке, что и скрипт.py чтения токена
token_file = "tg_bot_token.data"

# Настраиваем логгер для этого модуля
logger = logging.getLogger(__name__)

def get_token(token_file_name: str = token_file) -> str:
    try:
        token_path = Path(token_file_name)
        if not token_path.exists():
            logger.critical(f"   ОШИБКА: Файл с токеном не найден: {token_path}")
            logger.critical(f"   Создайте файл '{token_file_name}' и поместите в него токен бота созданный при помощи botFather")
            sys.exit(1)

        with open(token_path, 'r', encoding='utf-8') as file:
            token = file.read().strip()

        if not token:
            logger.critical(f"   ОШИБКА: Файл с токеном пуст: {token_path}")
            logger.critical(f"   Добавьте токен бота в файл '{token_file_name}'")
            sys.exit(1)

        masked_token = f"{token[:10]}..." if len(token) > 10 else token
        logger.info(f"   Токен успешно загружен: {masked_token}")

        return token

    except PermissionError as e:
        logger.critical(f"Нет прав для чтения файла: {token_path}")
        logger.critical(f"Ошибка: {e}")
        sys.exit(1)

    except Exception as e:
        logger.exception(f"Непредвиденная ошибка при чтении токена")
        sys.exit(1)