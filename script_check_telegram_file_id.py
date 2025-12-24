import asyncio
from telegram import Bot


TOKEN = '8509426873:.....' #your bot token

file_id = "AgACAgIAAxkBAAMRaTwMi24gwJbabWB3G9jUnYcwgDwAAqIQaxvUZ-FJI1E5dAjyUZYBAAMCAAN5AAM2BA"

#insert into product_photos(product_id,telegram_file_id,sort_order) values
#(1,'AgACAgIAAxkBAAMLaTwLLhh5wLrmJnD2D_pACzjEAn8AApEQaxvUZ-FJGe6O1xyhAjgBAAMCAAN4AAM2BA',0),
#(2,'AgACAgIAAxkBAAMOaTwMermf2TynzeT8ZZZsZGrpSbkAAqAQaxvUZ-FJGNdoPbRlAAGhAQADAgADeQADNgQ',0),
#(3,'AgACAgIAAxkBAAMRaTwMi24gwJbabWB3G9jUnYcwgDwAAqIQaxvUZ-FJI1E5dAjyUZYBAAMCAAN5AAM2BA',0);

async def check_file():
    bot = Bot(token=TOKEN)
    try:
        file = await bot.get_file(file_id)
        print("Файл существует. Ссылка для скачивания:", file.file_path)
    except Exception as e:
        print("Файл не найден или недоступен:", e)

asyncio.run(check_file())