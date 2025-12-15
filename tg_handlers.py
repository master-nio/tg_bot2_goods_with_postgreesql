import logging
import asyncpg
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def start_command(update, context):
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_text = f"""
    🛍️ <b>Добро пожаловать в наш магазин!</b>

    Привет, {user.mention_html()}!

    Я - телеграм бот, здесь вы можете:
    • 🗂️ Просматривать каталог товаров
    • 🛒 Добавлять товары в корзину
    • 📦 Оформлять заказы

    Используйте /catalog чтобы начать покупки или кнопки!
    Или /help для списка всех команд.
    Или /contact для ответа живых людей. 
        Возможно они прочитают ваше сообщение вне рабочее время и ответят.
        В рабочее время они очень заняты и обычно не отвечают (Это дэмка).
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

async def main_menu_command(update, context):
    query = update.callback_query
    await query.answer()
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
    /backet - Моя корзина
    /orders - Мои заказы

    <b>Помощь:</b>
    /contacts - Контакты поддержки магазина
    """

    await update.message.reply_html(help_text)


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


        keyboard_add_card = [
            [InlineKeyboardButton("➕ В корзину", callback_data=f"backet_add_{product['id']}")]
        ]
        reply_markup_add_card = InlineKeyboardMarkup(keyboard_add_card)

        if product['telegram_file_id']:
            await message_obj.reply_photo(
                photo=product['telegram_file_id'],
                caption=caption,
                parse_mode='HTML',
                reply_markup=reply_markup_add_card
            )
        else:
            await message_obj.reply_text(
                caption,
                parse_mode='HTML',
                reply_markup=reply_markup_add_card
            )

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

async def add_to_basket_callback(update, context):
    query = update.callback_query
    await query.answer()  # подтверждаем нажатие, убираем «крутящийся кружок»

    # Получаем callback_data
    data = query.data  # например "backet_add_5"

    # Извлекаем ID товара
    if data.startswith("backet_add_"):
        product_id = int(data.split("_")[-1])
        telegram_user_id = query.from_user.id  # ID пользователя Telegram

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            # Вставляем товар в корзину
            # Если такой товар уже есть для пользователя, увеличиваем quantity
            await conn.execute("""
                        INSERT INTO tgbot_vitrina2026.user_basket(telegram_user_id, product_id, quantity)
                        VALUES($1, $2, 1)
                        ON CONFLICT(telegram_user_id, product_id)
                        DO UPDATE SET quantity = user_basket.quantity + 1
                    """, telegram_user_id, product_id)

            # 2. Получаем ОБНОВЛЁННУЮ сводку по корзине
            basket_summary = await conn.fetchrow("""
                            SELECT  
                                COUNT(product_id) as cnt_products,
                                COALESCE(SUM(quantity), 0) as qty_products,
                                COALESCE(SUM(p.price * b.quantity),0) as sum_position
                            FROM tgbot_vitrina2026.user_basket b
                            JOIN tgbot_vitrina2026.products p ON p.id = b.product_id
                            WHERE telegram_user_id = $1
                        """, telegram_user_id)

            # 3. Форматируем текст кнопки корзины
            cnt = int(basket_summary['cnt_products'] or 0)
            qty = int(basket_summary['qty_products'] or 0)
            total = int(basket_summary['sum_position'] or 0)

            if cnt == 0:
                basket_button_text = "🛒 Корзина"
                positions_word = "позиций"
            else:
                # Склонение слова "позиция"
                if cnt % 10 == 1 and cnt % 100 != 11:
                    positions_word = "позиция"
                elif cnt % 10 in [2, 3, 4] and cnt % 100 not in [12, 13, 14]:
                    positions_word = "позиции"
                else:
                    positions_word = "позиций"

                #basket_button_text = f"🛒 {cnt} {positions_word}, {qty} шт., {total}₽"

        except Exception as e:
            logger.error(f"Ошибка при добавлении в корзину: {e}")
            await query.message.reply_text("❌ Ошибка при добавлении товара")
            return
        finally:
            await conn.close()

        # Создаем кнопку "Корзина"
        keyboard = [
            [InlineKeyboardButton("🛒 Перейти в корзину", callback_data="show_basket")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение с кнопкой и полезной инфой
        await query.message.reply_text(  # ← query.edit_message_text вместо update.message.reply_html
            f"✅ Товар #{product_id} добавлен в корзину!\n"
            f"В корзине: {cnt} {positions_word}, {qty} шт., {total}₽",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

        logger.info(f"Товар {product_id} добавлен в корзину пользователя {telegram_user_id}")


async def backet_callback(update, context):
    """Обработчик нажатия кнопки 'Каталог'"""
    query = update.callback_query
    await query.answer()  # подтверждаем нажатие, чтобы Telegram не показывал "крутящийся кружок"
    await backet_command(update, context, query)

async def backet_command(update, context, query):
    """Обработчик команды /catalog и кнопки `Каталог` """

    message_obj = update.message or update.callback_query.message

    telegram_user_id = query.from_user.id

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # 1. Получаем сводку по корзине
        basket_summary = await conn.fetchrow("""
                SELECT  
                    COUNT(product_id) as cnt_products,
                    COALESCE(SUM(quantity), 0) as qty_products,
                    COALESCE(SUM(p.price * b.quantity), 0) as sum_position
                FROM tgbot_vitrina2026.user_basket b
                JOIN tgbot_vitrina2026.products p ON p.id = b.product_id
                WHERE telegram_user_id = $1
            """, telegram_user_id)

        cnt = int(basket_summary['cnt_products'])
        qty = int(basket_summary['qty_products'])
        total = int(basket_summary['sum_position'])

        # 2. Получаем детали товаров в корзине
        basket_items = await conn.fetch("""
                SELECT 
                    b.product_id,
                    p.name,
                    p.price,
                    b.quantity,
                    (p.price * b.quantity) as item_total
                FROM tgbot_vitrina2026.user_basket b
                JOIN tgbot_vitrina2026.products p ON p.id = b.product_id
                WHERE telegram_user_id = $1
                ORDER BY 5 DESC
            """, telegram_user_id)

        # 3. Формируем текст корзины
        if cnt == 0:
            # Корзина пуста
            basket_text = "🛒 <b>Ваша корзина</b>\n\n"
            basket_text += "😔 Корзина пуста\n"
            basket_text += "Добавьте товары из каталога!"

            # Кнопки для пустой корзины
            keyboard = [
                [InlineKeyboardButton("🗂️ В каталог", callback_data="show_catalog")]
            ]
        else:
            # Корзина не пуста
            basket_text = "🛒 <b>Ваша корзина</b>\n\n"

            # Добавляем список товаров
            items_list = []
            for item in basket_items:
                items_list.append(
                    f"• <b>{item['name']}</b>\n"
                    f"  {item['price']}₽ × {item['quantity']} шт. = "
                    f"  {item['item_total']}₽\n"
                    #f"  ID: {item['product_id']}"
                )

            basket_text += "\n".join(items_list)
            basket_text += f"\n<b>Итого:</b>\n"
            basket_text += f"Позиций: {cnt}\n"
            basket_text += f"Товаров: {qty} шт.\n"
            basket_text += f"Сумма: {total}₽"

            # Кнопки для корзины с товарами
            keyboard = [
                [
                    InlineKeyboardButton("🗑️ Очистить корзину", callback_data="clear_basket"),
                    InlineKeyboardButton("🗂️ Добавить товары", callback_data="show_catalog")
                ],
                [
                    InlineKeyboardButton("🛍️ Оформить заказ", callback_data="checkout_order")
                ]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # 4. Отправляем или обновляем сообщение
        if query.message.text:  # Если сообщение можно редактировать
            await message_obj.reply_html(
                basket_text,
                reply_markup=reply_markup
            )
        else:
            # Если нельзя редактировать (например, фото), отправляем новое
            await message_obj.reply_html(
                basket_text,
                reply_markup=reply_markup
            )

        logger.info(f"Показана корзина пользователя {telegram_user_id}")

    except Exception as e:
        logger.error(f"Ошибка при показе корзины: {e}")
        await message_obj.reply_html(
            "❌ Произошла ошибка при загрузке корзины. Попробуйте позже."
        )
    finally:
        await conn.close()


async def clear_basket_callback(update, context):
    query = update.callback_query
    await query.answer()

    message_obj = update.message or update.callback_query.message

    telegram_user_id = query.from_user.id  # ID пользователя Telegram

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Очистка корзины в БД
        await conn.fetchrow("""
                    DELETE FROM tgbot_vitrina2026.user_basket WHERE telegram_user_id  = $1
                """, telegram_user_id)

    except Exception as e:
        logger.error(f"Ошибка при очистке корзины: {e}")
        await message_obj.reply_html("❌ Ошибка при очистке корзины")
        return
    finally:
        await conn.close()

    # Создаем кнопку перехода в каталог
    keyboard = [
        [InlineKeyboardButton("🗂 Перейти в каталог", callback_data="show_catalog")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение с кнопкой и полезной инфой
    await message_obj.reply_html(  # ← query.edit_message_text вместо update.message.reply_html
        f"✅ Корзина очищена!\n",
        reply_markup=reply_markup
    )

    logger.info(f"Корзина очищена для пользователя {telegram_user_id}")

async def checkout_order_callback(update, context):
    query = update.callback_query
    await query.answer()

    message_obj = update.message or update.callback_query.message

    telegram_user_id = query.from_user.id  # ID пользователя Telegram

    #проверка корзины
    try:
        # Подключаемся к базе данных
        conn = await asyncpg.connect(DATABASE_URL)

        # Проверяем, есть ли товары в корзине
        basket_query = """
        SELECT 
            COUNT(*) as item_count,
            COALESCE(SUM(p.price * b.quantity), 0) as total_amount
        FROM tgbot_vitrina2026.user_basket b
        JOIN tgbot_vitrina2026.products p ON p.id = b.product_id
        WHERE b.telegram_user_id = $1
        """

        basket_info = await conn.fetchrow(basket_query, int(telegram_user_id))
        await conn.close()

        if not basket_info or basket_info['item_count'] == 0:
            # Корзина пуста
            empty_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Перейти в каталог", callback_data="show_catalog")]
            ])

            await message_obj.edit_text(
                text="🛒 <b>Корзина пуста!</b>\n\n"
                     "Чтобы оформить заказ, сначала добавьте товары из каталога.",
                reply_markup=empty_keyboard,
                parse_mode='HTML'
            )
            return

        # Получаем детальную информацию о товарах в корзине
        conn = await asyncpg.connect(DATABASE_URL)
        basket_details_query = """
        SELECT 
            b.id,
            b.product_id,
            p.name as product_name,
            p.price,
            b.quantity,
            (p.price * b.quantity) as total_price
        FROM tgbot_vitrina2026.user_basket b
        JOIN tgbot_vitrina2026.products p ON p.id = b.product_id
        WHERE b.telegram_user_id = $1
        ORDER BY b.added_at DESC
        """

        basket_items = await conn.fetch(basket_details_query, int(telegram_user_id))
        await conn.close()

        # Преобразуем записи в список словарей
        items_list = []
        for item in basket_items:
            items_list.append({
                'id': item['id'],
                'product_id': item['product_id'],
                'product_name': item['product_name'],
                'price': float(item['price']),
                'quantity': item['quantity'],
                'total_price': float(item['total_price'])
            })

        # Формируем сообщение с содержимым корзины
        basket_text = "📋 <b>Содержимое вашей корзины:</b>\n\n"

        for i, item in enumerate(items_list, 1):
            basket_text += (
                f"{i}. <b>{item['product_name']}</b>\n"
                f"   Количество: {item['quantity']} шт.\n"
                f"   Цена: {item['price']:.2f} ₽ за шт.\n"
                f"   Сумма: {item['total_price']:.2f} ₽\n\n"
            )

        total_amount = float(basket_info['total_amount'])
        items_count = basket_info['item_count']

        basket_text += (
            f"<b>📊 ИТОГО:</b>\n"
            f"Количество товаров: {items_count} шт.\n"
            f"Общая сумма: <b>{total_amount:.2f} ₽</b>\n\n"
            f"<i>Готовы оформить заказ?</i>"
        )

        # Создаем клавиатуру с действиями
        actions_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да, продолжить", callback_data="confirm_checkout")
            ],
            [
                InlineKeyboardButton("🗑️ Очистить корзину", callback_data="clear_basket")
            ],
            [
                InlineKeyboardButton("📋 Вернуться в каталог", callback_data="show_catalog"),
                InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")
            ]
        ])

        await message_obj.edit_text(
            text=basket_text,
            reply_markup=actions_keyboard,
            parse_mode='HTML'
        )

        # Сохраняем информацию о корзине в контексте для следующих шагов
        context.user_data['basket_items'] = items_list
        context.user_data['total_amount'] = total_amount
        context.user_data['items_count'] = items_count

    except Exception as e:
        logger.error(f"Ошибка при проверке корзины для пользователя {telegram_user_id}: {e}")

        # Клавиатура при ошибке
        error_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Перейти в каталог", callback_data="show_catalog")],
            [InlineKeyboardButton("️🏠 В главное меню", callback_data="main_menu")]
        ])

        await message_obj.edit_text(
            text="❌ <b>Произошла ошибка при загрузке корзины</b>\n\n"
                 "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            reply_markup=error_keyboard,
            parse_mode='HTML'
        )


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню"""
    query = update.callback_query

    if query:
        await query.answer()
        message_obj = query.message
        user = query.from_user
    else:
        # Если вызывается из команды /start
        message_obj = update.message
        user = update.effective_user

    telegram_user_id = str(user.id)
    username = user.username or user.first_name

    try:
        # Приветственное сообщение
        welcome_text = (
            f"👋 <b>Привет, {username}!</b>\n\n"
            f"Добро пожаловать в наш магазин!\n\n"
            f"<i>Выберите действие:</i>"
        )

        # Создаем клавиатуру главного меню
        main_menu_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🛍️ Каталог товаров", callback_data="show_catalog"),
                InlineKeyboardButton("🛒 Моя корзина", callback_data="show_basket")
            ],
            [
                InlineKeyboardButton("📋 Мои заказы", callback_data="show_orders"),
                InlineKeyboardButton("📞 Контакты", callback_data="contacts")
            ],
            [
                InlineKeyboardButton("ℹ️ О магазине", callback_data="about"),
                InlineKeyboardButton("🆘 Помощь", callback_data="help")
            ]
        ])

        # Проверяем откуда вызывается меню
        if query:
            await message_obj.edit_text(
                text=welcome_text,
                reply_markup=main_menu_keyboard,
                parse_mode='HTML'
            )
        else:
            await message_obj.reply_html(
                text=welcome_text,
                reply_markup=main_menu_keyboard
            )

        # Очищаем данные FSM при возврате в главное меню
        if context.user_data:
            # Удаляем только данные связанные с оформлением заказа
            checkout_keys = ['basket_items', 'total_amount', 'items_count',
                             'checkout_step', 'customer_name', 'customer_phone',
                             'customer_email', 'order_data']
            for key in checkout_keys:
                if key in context.user_data:
                    del context.user_data[key]

    except Exception as e:
        logger.error(f"Ошибка в главном меню: {e}")

        # Простое меню при ошибке
        fallback_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ Каталог", callback_data="show_catalog")],
            [InlineKeyboardButton("🛒 Корзина", callback_data="show_basket")]
        ])

        if query:
            await message_obj.edit_text(
                text="👋 Добро пожаловать!\n\nЧто вас интересует?",
                reply_markup=fallback_keyboard
            )
        else:
            await message_obj.reply_text(
                text="👋 Добро пожаловать!\n\nЧто вас интересует?",
                reply_markup=fallback_keyboard
            )


async def confirm_checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение оформления - начинаем сбор данных с имени"""
    query = update.callback_query
    await query.answer()

    message_obj = query.message

    # Проверяем, что данные корзины сохранены
    if 'basket_items' not in context.user_data:
        await message_obj.edit_text(
            text="⚠️ <b>Данные корзины не найдены</b>\n\n"
                 "Пожалуйста, начните оформление заказа заново.",
            parse_mode='HTML'
        )
        return

    # Устанавливаем первый шаг FSM - запрос имени
    context.user_data['checkout_step'] = 'ask_name'

    # Клавиатура для отмены
    cancel_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Отменить оформление", callback_data="cancel_checkout")]
    ])

    await message_obj.edit_text(
        text=f"✅ <b>Начинаем оформление заказа!</b>\n"
             f"<b>Шаг 1 из 3:</b> Введите ваше <b>Имя и Фамилию</b>\n"
             f"<i>Пример: Иван Иванов</i>",
        reply_markup=cancel_keyboard,
        parse_mode='HTML'
    )


async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода имени"""
    if update.message:
        user_input = update.message.text.strip()
        message_obj = update.message

        # Проверяем, что мы на шаге ввода имени
        if context.user_data.get('checkout_step') != 'ask_name':
            return

        # Проверяем валидность имени (2-50 символов, только буквы и пробелы)
        if len(user_input) < 2 or len(user_input) > 50:
            await message_obj.reply_text(
                "❌ Имя должно содержать от 2 до 50 символов. Попробуйте еще раз:"
            )
            return

        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$', user_input):
            await message_obj.reply_text(
                "❌ Имя может содержать только буквы, пробелы и дефисы. Попробуйте еще раз:"
            )
            return

        # Сохраняем имя
        context.user_data['customer_name'] = user_input
        context.user_data['checkout_step'] = 'ask_phone'

        # Клавиатура для отмены
        cancel_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Отменить оформление", callback_data="cancel_checkout")]
        ])

        # Запрашиваем телефон
        await message_obj.reply_text(
            text=f"✅ Имя сохранено: <b>{user_input}</b>\n\n"
                 f"<b>Шаг 2 из 3:</b> Введите ваш <b>номер телефона</b>\n"
                 f"<i>Пример: +79161234567 или 89161234567</i>",
            reply_markup=cancel_keyboard,
            parse_mode='HTML'
        )

        # Удаляем предыдущее сообщение бота с кнопками (если оно есть)
        try:
            if 'last_bot_message_id' in context.user_data:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message_id']
                )
        except:
            pass


async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода телефона"""
    if update.message:
        user_input = update.message.text.strip()
        message_obj = update.message

        # Проверяем, что мы на шаге ввода телефона
        if context.user_data.get('checkout_step') != 'ask_phone':
            return

        # Нормализуем номер телефона
        phone = user_input.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

        # Проверяем формат телефона
        if not re.match(r'^(\+7|8)\d{10}$', phone):
            await message_obj.reply_text(
                "❌ Неверный формат номера телефона. Используйте российский номер.\n"
                "Пример: +79161234567 или 89161234567\n"
                "Попробуйте еще раз:"
            )
            return

        # Нормализуем к формату +7XXXXXXXXXX
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        elif phone.startswith('7'):
            phone = '+' + phone

        # Сохраняем телефон
        context.user_data['customer_phone'] = phone
        context.user_data['checkout_step'] = 'ask_email'

        # Клавиатура для пропуска email или отмены
        email_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📧 Пропустить email", callback_data="skip_email")],
            [InlineKeyboardButton("🚫 Отменить оформление", callback_data="cancel_checkout")]
        ])

        await message_obj.reply_text(
            text=f"✅ Телефон сохранен: <b>{phone}</b>\n\n"
                 f"<b>Шаг 3 из 3 (необязательный):</b> Введите ваш <b>email</b>\n"
                 f"<i>Пример: ivan@example.com</i>\n\n"
                 f"<i>Если не хотите указывать email, нажмите 'Пропустить email'</i>",
            reply_markup=email_keyboard,
            parse_mode='HTML'
        )

        # Удаляем предыдущее сообщение бота
        try:
            if 'last_bot_message_id' in context.user_data:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message_id']
                )
        except:
            pass


async def skip_email_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск ввода email"""
    query = update.callback_query
    await query.answer()

    # Устанавливаем email как None
    context.user_data['customer_email'] = None

    # ДОБАВИТЬ ТАКЖЕ ЗДЕСЬ:
    context.user_data['checkout_step'] = 'confirmation'  # ← ДОБАВИТЬ

    # Переходим к подтверждению
    await show_order_confirmation(update, context)

async def handle_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода email"""
    if update.message:
        user_input = update.message.text.strip().lower()
        message_obj = update.message

        # Проверяем, что мы на шаге ввода email
        if context.user_data.get('checkout_step') != 'ask_email':
            return

        # Проверяем валидность email (базовая проверка)
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, user_input):
            await message_obj.reply_text(
                "❌ Неверный формат email. Попробуйте еще раз:\n"
                "Пример: ivan@example.com"
            )
            return

        # Сохраняем email
        context.user_data['customer_email'] = user_input




        # Переходим к подтверждению
        context.user_data['checkout_step'] = 'confirmation'
        await show_order_confirmation(update, context)

        # Удаляем предыдущее сообщение бота
        #try:
        #    if 'last_bot_message_id' in context.user_data:
        #        await context.bot.delete_message(
        #           chat_id=update.effective_chat.id,
        #            message_id=context.user_data['last_bot_message_id']
        #        )
        #except:
        #    pass


async def show_order_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать подтверждение заказа со всеми данными"""
    message_obj = None

    is_callback = False

    if update.callback_query:
        message_obj = update.callback_query.message
        await update.callback_query.answer()
        is_callback = True
    elif update.message:
        # Для текстового ввода всегда отправляем новое сообщение
        message_obj = update.message
        is_callback = False

    if not message_obj:
        return

    # Получаем все данные
    customer_name = context.user_data.get('customer_name', 'Не указано')
    customer_phone = context.user_data.get('customer_phone', 'Не указан')
    customer_email = context.user_data.get('customer_email', 'Не указан')

    items = context.user_data.get('basket_items', [])
    total_amount = context.user_data.get('total_amount', 0)

    # Формируем текст подтверждения
    confirmation_text = "📝 <b>Подтвердите данные заказа:</b>\n\n"

    confirmation_text += "<b>Ваши данные:</b>\n"
    confirmation_text += f"👤 Имя: <b>{customer_name}</b>\n"
    confirmation_text += f"📞 Телефон: <b>{customer_phone}</b>\n"
    confirmation_text += f"📧 Email: <b>{customer_email if customer_email else 'Не указан'}</b>\n\n"

    confirmation_text += "<b>Состав заказа:</b>\n"
    for i, item in enumerate(items[:5], 1):  # Показываем первые 5 товаров
        confirmation_text += f"{i}. {item['product_name']} × {item['quantity']}\n"

    if len(items) > 5:
        confirmation_text += f"... и еще {len(items) - 5} товар(ов)\n"

    confirmation_text += f"\n<b>💰 Общая сумма: {total_amount:.2f} ₽</b>\n\n"
    confirmation_text += "<i>Все верно? Нажмите '✅ Подтвердить заказ' для создания заказа.</i>"

    # Создаем клавиатуру
    confirmation_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Подтвердить заказ", callback_data="create_order"),
            InlineKeyboardButton("✏️ Изменить данные", callback_data="edit_order_data")
        ],
        [
            InlineKeyboardButton("🚫 Отменить заказ", callback_data="cancel_checkout"),
            InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")
        ]
    ])

    if is_callback:
        await message_obj.edit_text(
            text=confirmation_text,
            reply_markup=confirmation_keyboard,
            parse_mode='HTML'
        )
    else:
        response = await message_obj.reply_text(
            text=confirmation_text,
            reply_markup=confirmation_keyboard,
            parse_mode='HTML'
        )
        # Сохраняем ID сообщения бота для возможного удаления
        context.user_data['last_bot_message_id'] = response.message_id


async def edit_order_data_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование данных заказа"""
    query = update.callback_query
    await query.answer()

    message_obj = query.message

    edit_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Изменить имя", callback_data="edit_name")],
        [InlineKeyboardButton("✏️ Изменить телефон", callback_data="edit_phone")],
        [InlineKeyboardButton("✏️ Изменить email", callback_data="edit_email")],
        [InlineKeyboardButton("🔙 Назад к подтверждению", callback_data="back_to_confirmation")]
    ])

    await message_obj.edit_text(
        text="📝 <b>Что вы хотите изменить?</b>\n\n"
             "Выберите, какие данные нужно исправить:",
        reply_markup=edit_keyboard,
        parse_mode='HTML'
    )


async def edit_name_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования имени"""
    query = update.callback_query
    await query.answer()

    message_obj = query.message

    context.user_data['checkout_step'] = 'edit_name'

    cancel_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_confirmation")]
    ])

    await message_obj.edit_text(
        text="✏️ <b>Введите новое имя:</b>\n"
             "<i>Пример: Иван Иванов</i>",
        reply_markup=cancel_keyboard,
        parse_mode='HTML'
    )


async def edit_phone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования телефона"""
    query = update.callback_query
    await query.answer()

    message_obj = query.message

    context.user_data['checkout_step'] = 'edit_phone'

    cancel_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_confirmation")]
    ])

    await message_obj.edit_text(
        text="✏️ <b>Введите новый номер телефона:</b>\n"
             "<i>Пример: +79161234567 или 89161234567</i>",
        reply_markup=cancel_keyboard,
        parse_mode='HTML'
    )


async def edit_email_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования email"""
    query = update.callback_query
    await query.answer()

    message_obj = query.message

    context.user_data['checkout_step'] = 'edit_email'

    cancel_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_confirmation")]
    ])

    await message_obj.edit_text(
        text="✏️ <b>Введите новый email:</b>\n"
             "<i>Пример: ivan@example.com</i>\n\n"
             "<i>Или отправьте 'пропустить', чтобы не указывать email</i>",
        reply_markup=cancel_keyboard,
        parse_mode='HTML'
    )


async def back_to_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к подтверждению заказа"""
    await show_order_confirmation(update, context)


async def cancel_checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена оформления заказа"""
    query = update.callback_query
    if query:
        await query.answer()
        message_obj = query.message
    else:
        message_obj = update.message

    # Очищаем данные FSM
    checkout_keys = ['basket_items', 'total_amount', 'items_count',
                     'checkout_step', 'customer_name', 'customer_phone',
                     'customer_email', 'last_bot_message_id']

    for key in checkout_keys:
        if key in context.user_data:
            del context.user_data[key]

    # Возвращаем в главное меню
    await main_menu_callback(update, context)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Определяет тип вводимых данных и перенаправляет в соответствующий обработчик"""
    current_step = context.user_data.get('checkout_step', '')

    if current_step in ['ask_name', 'edit_name']:
        await handle_name_input(update, context)
    elif current_step in ['ask_phone', 'edit_phone']:
        await handle_phone_input(update, context)
    elif current_step in ['ask_email', 'edit_email']:
        # Проверяем, не хочет ли пользователь пропустить email
        user_text = update.message.text.strip().lower()
        if user_text in ['пропустить', 'skip', 'нет', 'не хочу']:
            context.user_data['customer_email'] = None
            await show_order_confirmation(update, context)
        else:
            await handle_email_input(update, context)


async def create_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание заказа в БД"""
    query = update.callback_query
    await query.answer()

    message_obj = query.message
    telegram_user_id = int(update.effective_user.id)

    try:
        # Проверяем, что все необходимые данные собраны
        required_data = ['customer_name', 'customer_phone', 'basket_items', 'total_amount']
        missing_data = []

        for key in required_data:
            if key not in context.user_data:
                missing_data.append(key)

        if missing_data:
            logger.error(f"Отсутствуют данные для заказа: {missing_data}")

            # Показываем сообщение об ошибке и предлагаем начать заново
            error_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Начать заново", callback_data="checkout")],
                [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
            ])

            await message_obj.edit_text(
                text="❌ <b>Ошибка оформления заказа</b>\n\n"
                     "Не все данные были сохранены. Пожалуйста, начните оформление заказа заново.",
                reply_markup=error_keyboard,
                parse_mode='HTML'
            )
            return

        # Получаем данные из контекста
        customer_name = context.user_data['customer_name']
        customer_phone = context.user_data['customer_phone']
        customer_email = context.user_data.get('customer_email')  # Может быть None
        basket_items = context.user_data['basket_items']
        total_amount = context.user_data['total_amount']

        # Подключаемся к БД
        conn = await asyncpg.connect(DATABASE_URL)

        # Вызываем функцию создания заказа
        order_query = """
        SELECT * FROM tgbot_vitrina2026.create_order_from_basket(
            $1,  -- telegram_user_id
            $2,  -- customer_name
            $3,  -- customer_phone
            $4   -- customer_email
        )
        """

        result = await conn.fetch(order_query,
                                  telegram_user_id,
                                  customer_name,
                                  customer_phone,
                                  customer_email)

        await conn.close()

        if not result or len(result) == 0:
            raise Exception("Не удалось создать заказ. Функция не вернула номер заказа.")

        # Получаем номер заказа
        order_number = result[0]['order_number']


        # Формируем сообщение об успешном оформлении
        order_details = "📦 <b>Ваш заказ успешно оформлен!</b>\n\n"

        order_details += f"<b>Номер заказа:</b> <code>{order_number}</code>\n"
        order_details += f"<b>Имя:</b> {customer_name}\n"
        order_details += f"<b>Телефон:</b> {customer_phone}\n"

        if customer_email:
            order_details += f"<b>Email:</b> {customer_email}\n"

        order_details += f"<b>Сумма заказа:</b> {total_amount:.2f} ₽\n\n"

        # Состав заказа (кратко)
        order_details += "<b>Состав заказа:</b>\n"
        for i, item in enumerate(basket_items[:3], 1):
            order_details += f"{i}. {item['product_name']} × {item['quantity']}\n"

        if len(basket_items) > 3:
            order_details += f"... и еще {len(basket_items) - 3} товар(ов)\n"

        order_details += "\n"

        # Информация о следующем шаге
        order_details += "✅ <b>Пока это демонстарционный магазин.</b>\n\n"
        order_details += "✅ Если вы желаете подобный свяжитесь по контактам ниже.\n\n"
        order_details += "\n\n"
        order_details += "✅ <b>Информация передана вашему персональному менеджеру.</b>\n\n"
        order_details += "⏳ <i>Ожидайте, с вами свяжутся для уточнения даты доставки заказа.</i>\n\n"
        order_details += "📞 <b>Контакты поддержки:</b>\n"
        order_details += "Телефон: +7 (925) 000-60-75\n"
        order_details += "Email: dashkevich.alexander@gmail.com\n"
        order_details += "Telegram: @alexander_dashkevich\n\n"
        order_details += "<i>Благодарим за покупку! 😊</i>"

        # Клавиатура после создания заказа
        success_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 Мои заказы", callback_data="show_orders"),
                InlineKeyboardButton("🛍️ В каталог", callback_data="catalog")
            ],
            [
                InlineKeyboardButton("📞 Связаться с поддержкой", url="https://t.me/alexander_dashkevich"),
                InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")
            ]
        ])

        await message_obj.edit_text(
            text=order_details,
            reply_markup=success_keyboard,
            parse_mode='HTML'
        )

        # Отправляем уведомление менеджеру (опционально)
        await send_manager_notification(context, order_number, customer_name, customer_phone,
                                        total_amount, basket_items, update.effective_user)

        # Очищаем данные FSM после успешного создания заказа
        checkout_keys = ['basket_items', 'total_amount', 'items_count',
                         'checkout_step', 'customer_name', 'customer_phone',
                         'customer_email', 'last_bot_message_id']

        for key in checkout_keys:
            if key in context.user_data:
                del context.user_data[key]

        logger.info(f"Заказ {order_number} успешно создан для пользователя {telegram_user_id}")

    except asyncpg.exceptions.PostgresError as e:
        logger.error(f"Ошибка базы данных при создании заказа: {e}")

        # Ошибка базы данных
        error_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="checkout")],
            [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
        ])

        await message_obj.edit_text(
            text="❌ <b>Ошибка при создании заказа</b>\n\n"
                 "Произошла ошибка при обработке заказа. Пожалуйста, попробуйте еще раз.\n\n"
                 "<i>Если ошибка повторяется, свяжитесь с поддержкой.</i>",
            reply_markup=error_keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Ошибка при создании заказа: {e}")

        # Общая ошибка
        error_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Начать заново", callback_data="checkout")],
            [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
        ])

        await message_obj.edit_text(
            text="❌ <b>Не удалось создать заказ</b>\n\n"
                 "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже или свяжитесь с поддержкой.",
            reply_markup=error_keyboard,
            parse_mode='HTML'
        )

async def send_manager_notification(context: ContextTypes.DEFAULT_TYPE, order_number: str,
                                    customer_name: str, customer_phone: str,
                                    total_amount: float, basket_items: list, user):
    """Отправка уведомления менеджеру о новом заказе"""
    try:
        # ID чата менеджера (настройте под свои нужды)
        MANAGER_CHAT_ID = -1001234567890  # Или другой ID

        # Формируем сообщение для менеджера
        manager_message = f"🆕 <b>НОВЫЙ ЗАКАЗ #{order_number}</b>\n\n"

        manager_message += f"<b>Клиент:</b> {customer_name}\n"
        manager_message += f"<b>Телефон:</b> {customer_phone}\n"

        if user.username:
            manager_message += f"<b>Telegram:</b> @{user.username}\n"
        else:
            manager_message += f"<b>Telegram ID:</b> {user.id}\n"

        manager_message += f"<b>Сумма:</b> {total_amount:.2f} ₽\n\n"

        manager_message += "<b>Состав заказа:</b>\n"
        for i, item in enumerate(basket_items, 1):
            manager_message += f"{i}. {item['product_name']} × {item['quantity']} = {item['total_price']:.2f} ₽\n"

        manager_message += f"\n<b>Итого:</b> {total_amount:.2f} ₽\n\n"
        manager_message += f"<b>Статус:</b> 🔄 <i>Новый</i>"

        # Клавиатура для менеджера (если нужно быстрое действие)
        manager_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Принять в работу", callback_data=f"order_accept_{order_number}"),
                InlineKeyboardButton("📞 Позвонить", url=f"tel:{customer_phone}")
            ],
            [
                InlineKeyboardButton("💬 Написать клиенту",
                                     url=f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"),
                InlineKeyboardButton("📋 Все заказы", callback_data="all_orders")
            ]
        ])

        # Отправляем сообщение менеджеру
        await context.bot.send_message(
            chat_id=MANAGER_CHAT_ID,
            text=manager_message,
            reply_markup=manager_keyboard,
            parse_mode='HTML'
        )

        logger.info(f"Уведомление менеджеру отправлено для заказа {order_number}")

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления менеджеру: {e}")


async def view_orders_callback(update, context):
    query = update.callback_query
    await query.answer()  # подтверждаем нажатие, чтобы Telegram не показывал "крутящийся кружок"
    await orders_command(update, context)

async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать заказы пользователя"""
    query = update.callback_query
    if query:
        await query.answer()
        message_obj = query.message
        user = query.from_user
    else:
        # Если вызывается из команды /myorders
        message_obj = update.message
        user = update.effective_user

    telegram_user_id = user.id

    username = user.username or user.first_name

    try:
        # Подключаемся к БД
        conn = await asyncpg.connect(DATABASE_URL)

        # Запрос для получения заказов пользователя
        orders_query = """
            SELECT 
                o.id,
                order_number,
                customer_name,
                customer_email,
                customer_phone,
                total_amount,
                status,
                o.created_at,
                (select count(1) from tgbot_vitrina2026.order_items i where o.id = i.order_number_id) cnt_items 
            FROM tgbot_vitrina2026.orders o
            WHERE o.telegram_user_id = $1
            ORDER BY o.created_at DESC
            LIMIT 50
        """

        orders = await conn.fetch(orders_query, telegram_user_id)
        await conn.close()

        if not orders:
            # Нет заказов
            no_orders_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ В каталог", callback_data="show_catalog")],
                [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
            ])

            text = f"📋 <b>Ваши заказы</b>\n\n"
            text += f"У вас еще нет заказов.\n\n"
            text += f"<i>Посмотрите наш каталог товаров!</i>"

            if query:
                await message_obj.edit_text(
                    text=text,
                    reply_markup=no_orders_keyboard,
                    parse_mode='HTML'
                )
            else:
                await message_obj.reply_text(
                    text=text,
                    reply_markup=no_orders_keyboard,
                    parse_mode='HTML'
                )
            return

        # Форматируем список заказов
        orders_text = f"📋 <b>Ваши заказы</b>\n\n"
        orders_text += f"Найдено заказов: {len(orders)}\n\n"

        for i, order in enumerate(orders, 1):
            # Форматируем дату
            created_date = order['created_at'].strftime('%d.%m.%Y %H:%M')

            # Определяем эмодзи статуса
            status_emoji = {
                'new': '🆕',
                'processing': '🔄',
                'completed': '✅',
                'cancelled': '❌'
            }.get(order['status'], '❓')

            orders_text += f"<b>{i}. Заказ #{order['order_number']}</b>\n"
            orders_text += f"   📅 Дата: {created_date}\n"
            orders_text += f"   💰 Сумма: {order['total_amount']:.2f} ₽\n"
            orders_text += f"   📦 Товаров: {order['cnt_items']} шт.\n"
            orders_text += f"   📊 Статус: {status_emoji} {order['status']}\n\n"

        # Создаем инлайн клавиатуру
        keyboard_buttons = []

        # Добавляем стандартные кнопки
        keyboard_buttons.append([
            InlineKeyboardButton("📞 Поддержка", url="https://t.me/alexander_dashkevich")
        ])

        keyboard_buttons.append([
            InlineKeyboardButton("🛍️ В каталог", callback_data="show_catalog"),
            InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")
        ])

        orders_keyboard = InlineKeyboardMarkup(keyboard_buttons)

        # Отправляем сообщение
        if query:
            await message_obj.edit_text(
                text=orders_text,
                reply_markup=orders_keyboard,
                parse_mode='HTML'
            )
        else:
            await message_obj.reply_text(
                text=orders_text,
                reply_markup=orders_keyboard,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Ошибка при получении заказов: {e}")

        error_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="my_orders")],
            [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
        ])

        error_text = "❌ <b>Ошибка при загрузке заказов</b>\n\n"
        error_text += "Пожалуйста, попробуйте позже."

        if query:
            await message_obj.edit_text(
                text=error_text,
                reply_markup=error_keyboard,
                parse_mode='HTML'
            )
        else:
            await message_obj.reply_text(
                text=error_text,
                reply_markup=error_keyboard,
                parse_mode='HTML'
            )