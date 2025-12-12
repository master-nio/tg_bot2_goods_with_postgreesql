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
    deleted_at      TIMESTAMP
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
    'Новогодняя ёлка Premium',
    '<b>Премиальная искусственная ёлка</b><br>
     Пышная, высокая и максимально приближенная к настоящей.<br>
     Идеально впишется в интерьер и создаст волшебную праздничную атмосферу.',
    9999.99
),
(
    'Новогодняя ёлка Standart',
    '<b>Классическая новогодняя ёлка</b><br>
     Умеренная плотность веток, аккуратная форма и стильный внешний вид.<br>
     Отличный выбор для квартиры или небольшого офиса.',
    5999.99
),
(
    'Новогодняя ёлка Easy',
    '<b>Компактная и удобная ёлка</b><br>
     Лёгкая, быстро собирается, не занимает много места.<br>
     Подойдёт для стола, тумбы или небольшого пространства.',
    2999.99
);

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


select * from  product_photos


--Создаем пользователя
CREATE USER tgbot_reader WITH PASSWORD 'sdf$&^$oiydfSzQ';


-- Эта роль может быть использована для чтения любых таблиц в схеме tgbot_vitrina2026
GRANT CONNECT ON DATABASE tg_shops TO tgbot_reader;
GRANT USAGE ON SCHEMA tgbot_vitrina2026 TO tgbot_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA tgbot_vitrina2026 TO tgbot_reader;

--у меня на локали пользователь postgres админ
ALTER SCHEMA tgbot_vitrina2026 OWNER TO postgres;

-- Добавим новые  таблицы для пользователя tgbot_reader, чтобы он их мог читать, если вдруг что-то новое создадим под postgres
ALTER DEFAULT PRIVILEGES FOR ROLE postgres
IN SCHEMA tgbot_vitrina2026
GRANT SELECT ON TABLES TO tgbot_reader;


--Убираем права у tgbot_reader на чтение схемы public
REVOKE ALL ON SCHEMA public FROM tgbot_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM tgbot_reader;

GRANT USAGE ON SCHEMA tgbot_vitrina2026 TO tgbot_reader;
-- Даем права SELECT на все существующие таблицы
GRANT SELECT ON ALL TABLES IN SCHEMA tgbot_vitrina2026 TO tgbot_reader;

