sudo -u postgres psql -d tg_shops
\c tg_shops
create database tg_shops;

CREATE SCHEMA tgbot_vitrina2026 AUTHORIZATION postgres;

drop table tgbot_vitrina2026.order_items;
drop table tgbot_vitrina2026.orders;
drop table tgbot_vitrina2026.user_basket;
drop table tgbot_vitrina2026.product_photos;
drop table tgbot_vitrina2026.products;

select * from tgbot_vitrina2026.products;
select * from tgbot_vitrina2026.product_photos;
select * from tgbot_vitrina2026.user_basket;
select * from tgbot_vitrina2026.order_items;
select * from tgbot_vitrina2026.orders;


CREATE TABLE tgbot_vitrina2026.products (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    price           NUMERIC(10,2) NOT NULL,

    -- Обязательные системные поля
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    -- Флаги и метаданные
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_by      BIGINT,         -- ID пользователя Telegram/системы
    deleted_at      TIMESTAMP,
    sort INT NOT NULL DEFAULT 0
);


CREATE OR REPLACE FUNCTION tgbot_vitrina2026.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_timestamp
BEFORE UPDATE ON tgbot_vitrina2026.products
FOR EACH ROW
EXECUTE FUNCTION tgbot_vitrina2026.update_timestamp();

INSERT INTO tgbot_vitrina2026.products (name, description, price)
VALUES
(
    '<b>Новогодняя ёлка Premium</b>',
    '     Премиальная искусственная ёлка.
     Пышная, высокая и максимально приближенная к настоящей.
     Идеально впишется в интерьер и создаст волшебную праздничную атмосферу.',
    9999.00
),
(
    '<b>Новогодняя ёлка Standart</b>',
    '     Классическая новогодняя ёлка.
     Умеренная плотность веток, аккуратная форма и стильный внешний вид.
     Отличный выбор для квартиры или небольшого офиса.',
    5999.00
),
(
    '<b>Новогодняя ёлка Easy</b>',
    '     Компактная и удобная ёлка.
     Лёгкая, быстро собирается, не занимает много места.
     Подойдёт для стола, тумбы или небольшого пространства.',
    2999.00
);

-- delete from tgbot_vitrina2026.products;

SELECT 
	p.id, 
	p.name, 
	p.description, 
	p.price,
	f.telegram_file_id
FROM tgbot_vitrina2026.products p
LEFT JOIN product_photos f ON p.id = f.product_id
WHERE 
	is_deleted = FALSE
	AND sort = 0
ORDER BY id;

CREATE INDEX idx_products_not_deleted
ON tgbot_vitrina2026.products (is_deleted)
WHERE is_deleted = false;


CREATE TABLE tgbot_vitrina2026.product_photos (
    id              SERIAL PRIMARY KEY,
    product_id      INT NOT NULL REFERENCES tgbot_vitrina2026.products(id) ON DELETE CASCADE,
    telegram_file_id   TEXT NOT NULL, -- Telegram File ID
    sort_order      INT NOT NULL DEFAULT 0,  -- порядок сортировки фото
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

/*
Через функцию загрузки фото в Боте получаем telegram_file_id

premium
AgACAgIAAxkBAAMLaTwLLhh5wLrmJnD2D_pACzjEAn8AApEQaxvUZ-FJGe6O1xyhAjgBAAMCAAN4AAM2BA

standart
AgACAgIAAxkBAAMOaTwMermf2TynzeT8ZZZsZGrpSbkAAqAQaxvUZ-FJGNdoPbRlAAGhAQADAgADeQADNgQ

easy
AgACAgIAAxkBAAMRaTwMi24gwJbabWB3G9jUnYcwgDwAAqIQaxvUZ-FJI1E5dAjyUZYBAAMCAAN5AAM2BA
*/

--линкуем загруженные фото с товарами
insert into product_photos(product_id,telegram_file_id,sort_order) values 
(1,'AgACAgIAAxkBAAMLaTwLLhh5wLrmJnD2D_pACzjEAn8AApEQaxvUZ-FJGe6O1xyhAjgBAAMCAAN4AAM2BA',0),
(2,'AgACAgIAAxkBAAMOaTwMermf2TynzeT8ZZZsZGrpSbkAAqAQaxvUZ-FJGNdoPbRlAAGhAQADAgADeQADNgQ',0),
(3,'AgACAgIAAxkBAAMRaTwMi24gwJbabWB3G9jUnYcwgDwAAqIQaxvUZ-FJI1E5dAjyUZYBAAMCAAN5AAM2BA',0);


select * from product_photos;

--Создаем пользователя
CREATE USER tgbot_reader WITH PASSWORD 'Пароль к пользователю';

-- Продолжаем создавать таблицы. Теперь Корзина
CREATE TABLE tgbot_vitrina2026.user_basket (
    id              SERIAL PRIMARY KEY,       -- Уникальный идентификатор записи
    telegram_user_id BIGINT NOT NULL,         -- ID пользователя Telegram
    product_id      INT NOT NULL REFERENCES tgbot_vitrina2026.products(id) ON DELETE CASCADE,  -- товар
    quantity        INT NOT NULL DEFAULT 1,   -- количество единиц товара
    added_at        TIMESTAMP NOT NULL DEFAULT NOW(),  -- дата и время добавления
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(telegram_user_id, product_id)      -- чтобы один и тот же товар не дублировался для одного пользователя
);

select * from tgbot_vitrina2026.user_basket;


select  
	--count(product_id) cnt_products,
	--sum(quantity) qty_products,
	p.name,
	p.price,
	b.quantity qty,
	p.price * b.quantity as sum_position
from tgbot_vitrina2026.user_basket b
join tgbot_vitrina2026.products p on p.id = b.product_id
where telegram_user_id = 'Ваш телеграм ID'


select  
	count(product_id) cnt_products,
	COALESCE(SUM(quantity), 0) as qty_products,
	COALESCE(SUM(p.price * b.quantity), 0) as sum_position
from tgbot_vitrina2026.user_basket b
join tgbot_vitrina2026.products p on p.id = b.product_id
where telegram_user_id = 'Ваш телеграм ID'

SELECT  
    COUNT(product_id) as cnt_products,
    COALESCE(SUM(quantity), 0) as qty_products,
    COALESCE(SUM(p.price * b.quantity),0) as sum_position
FROM tgbot_vitrina2026.user_basket b
JOIN tgbot_vitrina2026.products p ON p.id = b.product_id
WHERE telegram_user_id  = 'Ваш телеграм ID'
                            
                            
DELETE 
FROM tgbot_vitrina2026.user_basket
WHERE telegram_user_id  = 'Ваш телеграм ID'


select * from user_basket


CREATE TABLE IF NOT EXISTS tgbot_vitrina2026.orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_email VARCHAR(100),
    customer_phone VARCHAR(20) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'new' 
        CHECK (status IN ('new', 'processing', 'completed', 'cancelled')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

select * from orders;

COMMENT ON TABLE tgbot_vitrina2026.orders IS 'Таблица заказов пользователей';
COMMENT ON COLUMN tgbot_vitrina2026.orders.order_number IS 'Уникальный номер заказа';
COMMENT ON COLUMN tgbot_vitrina2026.orders.telegram_user_id IS 'ID пользователя в Telegram';
COMMENT ON COLUMN tgbot_vitrina2026.orders.customer_name IS 'Имя клиента';
COMMENT ON COLUMN tgbot_vitrina2026.orders.customer_email IS 'Email клиента (опционально)';
COMMENT ON COLUMN tgbot_vitrina2026.orders.customer_phone IS 'Телефон клиента';
COMMENT ON COLUMN tgbot_vitrina2026.orders.total_amount IS 'Общая сумма заказа';
COMMENT ON COLUMN tgbot_vitrina2026.orders.status IS 'Статус заказа: new, processing, completed, cancelled';
COMMENT ON COLUMN tgbot_vitrina2026.orders.created_at IS 'Дата создания заказа';
COMMENT ON COLUMN tgbot_vitrina2026.orders.updated_at IS 'Дата последнего обновления';

CREATE INDEX IF NOT EXISTS idx_orders_telegram_user 
    ON tgbot_vitrina2026.orders(telegram_user_id);
    
CREATE INDEX IF NOT EXISTS idx_orders_status 
    ON tgbot_vitrina2026.orders(status);
   
-- Создаем последовательность для номеров заказов
CREATE SEQUENCE IF NOT EXISTS tgbot_vitrina2026.order_number_seq
    START WITH 1000
    INCREMENT BY 1;

-- Посмотреть текущее значение
SELECT currval('tgbot_vitrina2026.order_number_seq');
   
-- Или если последовательность ещё не использовалась:
SELECT last_value FROM tgbot_vitrina2026.order_number_seq;

-- Вся информация о последовательности
SELECT * FROM information_schema.sequences 
WHERE sequence_schema = 'tgbot_vitrina2026' 
AND sequence_name = 'order_number_seq';

-- Сбросить на 1000 (или другое значение)
ALTER SEQUENCE tgbot_vitrina2026.order_number_seq RESTART WITH 1000;


-- Функция для генерации номера заказа
CREATE OR REPLACE FUNCTION tgbot_vitrina2026.generate_order_number()
RETURNS VARCHAR AS $$
DECLARE
    next_val INTEGER;
    order_num VARCHAR;
BEGIN
    SELECT nextval('tgbot_vitrina2026.order_number_seq') INTO next_val;
    order_num := 'ORD-' || to_char(CURRENT_DATE, 'YYYYMMDD') || '-' || LPAD(next_val::TEXT, 4, '0');
    RETURN order_num;
END;
$$ LANGUAGE plpgsql;
 
-- 5. Функция и триггер для updated_at (если ещё нет)
CREATE OR REPLACE FUNCTION tgbot_vitrina2026.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_orders_updated_at ON tgbot_vitrina2026.orders;
CREATE TRIGGER update_orders_updated_at 
    BEFORE UPDATE ON tgbot_vitrina2026.orders
    FOR EACH ROW
    EXECUTE FUNCTION tgbot_vitrina2026.update_updated_at_column();

select generate_order_number()

CREATE TABLE IF NOT EXISTS tgbot_vitrina2026.order_items (
    id SERIAL PRIMARY KEY,
    order_number_id INT NOT NULL REFERENCES tgbot_vitrina2026.orders(id) ON DELETE CASCADE,  -- id заказа
    product_id      INT NOT NULL REFERENCES tgbot_vitrina2026.products(id),
    product_name VARCHAR(200) NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    price_at_order NUMERIC(10,2) CHECK (price_at_order >= 0),
	subtotal DECIMAL(10, 2) GENERATED ALWAYS AS (price_at_order * quantity) STORED,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_order_product UNIQUE (order_number_id, product_id)
);

-- Комментарии
COMMENT ON TABLE tgbot_vitrina2026.order_items IS 'Состав заказа (позиции)';
COMMENT ON COLUMN tgbot_vitrina2026.order_items.order_number_id IS 'Ссылка на заказ';
COMMENT ON COLUMN tgbot_vitrina2026.order_items.product_id IS 'ID товара';
COMMENT ON COLUMN tgbot_vitrina2026.order_items.product_name IS 'Название товара на момент заказа';
COMMENT ON COLUMN tgbot_vitrina2026.order_items.quantity IS 'Количество товара';
COMMENT ON COLUMN tgbot_vitrina2026.order_items.price_at_order IS 'Цена товара на момент оформления заказа';
COMMENT ON COLUMN tgbot_vitrina2026.order_items.subtotal IS 'Сумма по позиции (цена × количество)';
COMMENT ON COLUMN tgbot_vitrina2026.order_items.created_at IS 'Дата создания записи';

-- Создание индексов отдельно
CREATE INDEX IF NOT EXISTS idx_order_items_order 
    ON tgbot_vitrina2026.order_items(order_number_id);
    
CREATE INDEX IF NOT EXISTS idx_order_items_product 
    ON tgbot_vitrina2026.order_items(product_id);

select * from order_items

DROP FUNCTION tgbot_vitrina2026.create_order_from_basket;
CREATE OR REPLACE FUNCTION tgbot_vitrina2026.create_order_from_basket(
    p_telegram_user_id BIGINT,
    p_customer_name VARCHAR,
    p_customer_phone VARCHAR,
    p_customer_email VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    order_number VARCHAR
) AS $$
DECLARE
    v_order_id INTEGER;
    v_order_number VARCHAR;
    v_total_amount DECIMAL(10,2);
    v_items_count INTEGER;
BEGIN
    -- Проверяем что корзина не пуста
    SELECT COUNT(*), COALESCE(SUM(p.price * b.quantity), 0)
    INTO v_items_count, v_total_amount
    FROM tgbot_vitrina2026.user_basket b
    JOIN tgbot_vitrina2026.products p ON p.id = b.product_id
    WHERE b.telegram_user_id = p_telegram_user_id;
    
    IF v_items_count = 0 OR v_total_amount = 0 THEN
        RAISE EXCEPTION 'Корзина пуста или сумма заказа равна 0';
    END IF;
    
    -- Генерируем номер заказа
    v_order_number := tgbot_vitrina2026.generate_order_number();
    
    -- Начинаем транзакцию
    BEGIN
        -- Создаем запись в таблице orders
        INSERT INTO tgbot_vitrina2026.orders (
            order_number,
            telegram_user_id,
            customer_name,
            customer_email,
            customer_phone,
            total_amount,
            status
        ) VALUES (
            v_order_number,
            p_telegram_user_id,
            p_customer_name,
            p_customer_email,
            p_customer_phone,
            v_total_amount,
            'new'
        ) RETURNING id INTO v_order_id;
        
        -- Переносим товары из корзины в order_items
        INSERT INTO tgbot_vitrina2026.order_items (
            order_number_id,
            product_id,
            product_name,
            quantity,
            price_at_order
        )
        SELECT 
            v_order_id,
            b.product_id,
            p.name,
            b.quantity,
            p.price
        FROM tgbot_vitrina2026.user_basket b
        JOIN tgbot_vitrina2026.products p ON p.id = b.product_id
        WHERE b.telegram_user_id = p_telegram_user_id;
        
        -- Очищаем корзину пользователя
        DELETE FROM tgbot_vitrina2026.user_basket 
        WHERE telegram_user_id = p_telegram_user_id;
        
        -- Возвращаем результат (БЕЗ status)
        RETURN QUERY 
        SELECT v_order_number;

            
    EXCEPTION
        WHEN OTHERS THEN
            -- Откатываем транзакцию при ошибке
            RAISE;
    END;
END;
$$ LANGUAGE plpgsql;

select * from orders;

SELECT schemaname, sequencename 
FROM pg_sequences 
WHERE sequencename = 'order_number_seq';


select * from tgbot_vitrina2026.order_items i


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
WHERE o.telegram_user_id = Ваш телеграм ID
ORDER BY o.created_at DESC
LIMIT 50


select *  
FROM tgbot_vitrina2026.orders o

update tgbot_vitrina2026.orders
set status = 'processing'
where id = 2

processing


-----
-- Права для пользователя tgbot_reader

--Убираем права у tgbot_reader на чтение схемы public
REVOKE ALL ON SCHEMA public FROM tgbot_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM tgbot_reader;

GRANT CONNECT ON DATABASE tg_shops TO tgbot_reader;
GRANT USAGE ON SCHEMA tgbot_vitrina2026 TO tgbot_reader;

-- Показать каталог
GRANT SELECT ON tgbot_vitrina2026.products TO tgbot_reader;
GRANT SELECT ON tgbot_vitrina2026.product_photos TO tgbot_reader;

-- Права на корзину
GRANT INSERT, UPDATE, DELETE, SELECT ON tgbot_vitrina2026.user_basket TO tgbot_reader;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE tgbot_vitrina2026.user_basket_id_seq TO tgbot_reader;

-- Права на запуск функций
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA tgbot_vitrina2026 TO tgbot_reader;

-- order_items_id_seq
GRANT USAGE, SELECT, UPDATE ON SEQUENCE tgbot_vitrina2026.order_items_id_seq TO tgbot_reader;
GRANT INSERT, UPDATE, DELETE, SELECT ON tgbot_vitrina2026.order_items TO tgbot_reader;

-- orders
GRANT INSERT, UPDATE, DELETE, SELECT ON tgbot_vitrina2026.orders TO tgbot_reader;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE tgbot_vitrina2026.orders_id_seq TO tgbot_reader;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE tgbot_vitrina2026.order_number_seq TO tgbot_reader;


USAGE → разрешает использовать последовательность
SELECT → читать текущее значение
UPDATE → получать nextval()


