import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


async def start_command(update, context):
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_text = f"""
    🛍️ <b>Добро пожаловать в наш магазин!</b>

    Привет, {user.mention_html()}!

    Я - бот-витрина, здесь вы можете:
    • 🗂️ Просматривать каталог товаров
    • 🛒 Добавлять товары в корзину
    • 📦 Оформлять заказы

    Используйте /catalog чтобы начать покупки!
    Или /help для списка всех команд.
    """

    # Создаем кнопку "Каталог"
    keyboard = [
        [InlineKeyboardButton("🗂️ Каталог", callback_data="show_catalog")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение с кнопкой
    await update.message.reply_html(
        welcome_text,
        reply_markup=reply_markup
    )

    logger.info(f"Новый пользователь: {user.id} (@{user.username})")


from telegram.ext import CallbackQueryHandler
async def catalog_callback(update, context):
    """Обработчик нажатия кнопки 'Каталог'"""
    query = update.callback_query
    await query.answer()  # подтверждаем нажатие, чтобы Telegram не показывал "крутящийся кружок"
    await catalog_command(update, context)


async def help_command(update, context):
    """Обработчик команды /help"""
    help_text = """
    📋 <b>Команды бота:</b>

    <b>Основные команды:</b>
    /start - Начало работы
    /help - Помощь и команды

    <b>Покупки:</b>
    /catalog - Каталог товаров
    /cart - Моя корзина
    /orders - Мои заказы

    <b>Профиль:</b>
    /profile - Мой профиль
    /contacts - Контакты поддержки
    """

    await update.message.reply_html(help_text)




import asyncpg
from telegram import InputMediaPhoto

# Подключение к БД (можно вынести в отдельную функцию или пул)
DATABASE_URL = "postgresql://tgbot_reader:sdf$&^$oiydfSzQ@localhost:5432/tg_shops"

async def catalog_command(update, context):
    """Обработчик команды /catalog и кнопки `Каталог` """

    message_obj = update.message or update.callback_query.message

    await message_obj.reply_html("🗂️ <b>Каталог товаров</b>\n\n")

    conn = await asyncpg.connect(DATABASE_URL)
    products = await conn.fetch("""
        SELECT 
            p.id, 
            p.name, 
            p.description, 
            p.price,
            f.telegram_file_id
        FROM tgbot_vitrina2026.products p
        LEFT JOIN tgbot_vitrina2026.product_photos f 
               ON p.id = f.product_id AND f.sort_order = 0
        WHERE p.is_deleted = FALSE
        ORDER BY p.id
    """)

    #debug
    #logger.debug("Каталог из базы: %s", products)

    if not products:
        await message_obj.reply_text("Каталог пока пуст.")
        await conn.close()
        return

    # Отправляем товары в тг
    for product in products:
        caption = f"🛒 {product['name']}\n"
        if product['description']:
            caption += f"{product['description']}\n"
        caption += f"💰 Цена: {product['price']} руб.\n"

        if product['telegram_file_id']:
            await message_obj.reply_photo(
                photo=product['telegram_file_id'],
                caption=caption,
                parse_mode='HTML'
            )
        else:
            await message_obj.reply_text(caption, parse_mode='HTML')

    await conn.close()



ADMINS = [219299367]  # замените на реальные Telegram ID админов через запятую, если их несколько
#Telegram ID можно получить через бота  @userinfobot

async def photo_handler(update, context):
    """Принимает фото и возвращает File ID только для администраторов"""
    user_id = update.message.from_user.id

    if user_id not in ADMINS:
        await update.message.reply_text("❌ У вас нет прав для загрузки фото.")
        return

    # Если администратор
    photo = update.message.photo[-1]  # самое большое фото
    file_id = photo.file_id

    await update.message.reply_html(
        "🗂️ <b>Загрузили фото</b>\n\n"
        "Все получится! Ниже указан <b>Telegram File ID</b>."
    )

    await update.message.reply_html(
        f"📎 <b>File ID:</b>\n<code>{file_id}</code>"
    )

    logger.info(f"Получено фото от {update.effective_user.id}, file_id={file_id}")