-- Seed data for cryptocurrency technical indicator tracking
-- Run after schema.sql has been applied.

INSERT INTO cryptocurrencies (symbol, name) VALUES
    ('BTC', 'Bitcoin'),
    ('ETH', 'Ethereum'),
    ('ADA', 'Cardano');

-- Example metrics across daily, weekly, and monthly intervals
INSERT INTO crypto_price_metrics (
    cryptocurrency_id, record_date, interval, price, ema, bollinger_upper, bollinger_lower, stoch_rsi
) VALUES
    -- Bitcoin daily sample
    ((SELECT id FROM cryptocurrencies WHERE symbol = 'BTC'), '2024-04-15', 'daily', 66000.25, 65500.10, 67050.00, 64050.00, 0.68),
    ((SELECT id FROM cryptocurrencies WHERE symbol = 'BTC'), '2024-04-22', 'daily', 67250.75, 66020.45, 68500.00, 64800.00, 0.72),
    -- Bitcoin weekly sample
    ((SELECT id FROM cryptocurrencies WHERE symbol = 'BTC'), '2024-04-22', 'weekly', 67250.75, 64500.00, 69000.00, 62000.00, 0.64),
    -- Bitcoin monthly sample
    ((SELECT id FROM cryptocurrencies WHERE symbol = 'BTC'), '2024-04-30', 'monthly', 69010.20, 63000.00, 72000.00, 58000.00, 0.58),

    -- Ethereum daily sample
    ((SELECT id FROM cryptocurrencies WHERE symbol = 'ETH'), '2024-04-15', 'daily', 3200.00, 3150.00, 3330.00, 2970.00, 0.54),
    ((SELECT id FROM cryptocurrencies WHERE symbol = 'ETH'), '2024-04-22', 'daily', 3405.50, 3250.00, 3500.00, 3000.00, 0.61),
    -- Ethereum weekly sample
    ((SELECT id FROM cryptocurrencies WHERE symbol = 'ETH'), '2024-04-22', 'weekly', 3405.50, 3100.00, 3600.00, 2800.00, 0.49),
    -- Ethereum monthly sample
    ((SELECT id FROM cryptocurrencies WHERE symbol = 'ETH'), '2024-04-30', 'monthly', 3500.75, 3000.00, 3800.00, 2600.00, 0.45),

    -- Cardano daily sample
    ((SELECT id FROM cryptocurrencies WHERE symbol = 'ADA'), '2024-04-15', 'daily', 0.58, 0.57, 0.62, 0.52, 0.73),
    ((SELECT id FROM cryptocurrencies WHERE symbol = 'ADA'), '2024-04-22', 'daily', 0.61, 0.58, 0.65, 0.51, 0.77),
    -- Cardano weekly sample
    ((SELECT id FROM cryptocurrencies WHERE symbol = 'ADA'), '2024-04-22', 'weekly', 0.61, 0.55, 0.70, 0.40, 0.63),
    -- Cardano monthly sample
    ((SELECT id FROM cryptocurrencies WHERE symbol = 'ADA'), '2024-04-30', 'monthly', 0.64, 0.53, 0.75, 0.35, 0.59);
