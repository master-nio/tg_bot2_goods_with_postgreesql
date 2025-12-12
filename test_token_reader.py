import logging

# Настроим логирование чтобы видеть сообщения
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)

from token_reader import get_token

# Тест 1: Файл не существует
token = get_token("non_existent.data")  # Должен выйти с ошибкой

# Тест 2: Создадим тестовый файл
#После теста не забудьте удалить test_token.data
#with open("test_token.data", "w") as f:
#    f.write("1234567890:ABCdefGHIjklMNOp0123456789")

token = get_token("test_token.data")
print(f"Токен получен: {token[:20]}...")


