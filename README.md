# Cryptobot Database Setup

This repository contains SQL files to create and populate a database that stores cryptocurrencies and their technical indicator values across daily, weekly, and monthly intervals.

## Files
- `db/schema.sql`: Creates the `cryptocurrencies` table and the `crypto_price_metrics` table with fields for price, EMA, Bollinger Bands, and Stoch RSI at daily, weekly, and monthly intervals.
- `db/seed_data.sql`: Inserts sample cryptocurrencies and example metrics covering each interval.

## Usage
These scripts are compatible with SQLite. To create and populate the database:

```bash
sqlite3 cryptobot.db < db/schema.sql
sqlite3 cryptobot.db < db/seed_data.sql
```

You can query the data, for example:

```sql
SELECT c.symbol,
       m.interval,
       m.record_date,
       m.price,
       m.ema,
       m.bollinger_upper,
       m.bollinger_lower,
       m.stoch_rsi
FROM crypto_price_metrics m
JOIN cryptocurrencies c ON c.id = m.cryptocurrency_id
ORDER BY c.symbol, m.interval, m.record_date;
```
