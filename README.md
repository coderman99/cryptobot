# Cryptobot Database Setup

This repository contains SQL files to create and populate a database that stores cryptocurrencies and their technical indicator values across daily, weekly, and monthly intervals, along with a market-wide Fear & Greed index series.

## Files
- `db/schema.sql`: Creates the `cryptocurrencies` table and the `crypto_price_metrics` table with fields for price, EMA, Bollinger Bands, and Stoch RSI at daily, weekly, and monthly intervals. Also defines the `market_sentiment` table for the overall crypto Fear & Greed index.
- `db/seed_data.sql`: Inserts sample cryptocurrencies and example metrics covering each interval, plus a few sample Fear & Greed index values.
- `scripts/fetch_coingecko_data.py`: Fetches six years of price history for supported assets from CoinGecko, computes indicators, and loads them alongside historical Fear & Greed values (retrieved from alternative.me).
- `requirements.txt`: Minimal dependencies (pandas, requests) needed to run the fetch script.

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

### Fetch fresh data from CoinGecko

Install dependencies (ideally in a virtual environment):

```bash
pip install -r requirements.txt
```

Populate or refresh the database with roughly six years of history for Bitcoin, Ethereum, XRP, Cardano, Solana, Avalanche, Chainlink, Litecoin, Monero, Zcash, Algorand, Hedera, and PAXG:

```bash
python scripts/fetch_coingecko_data.py --database cryptobot.db
```

Key flags:

- `--days` controls how many trailing days to request (default: ~6 years).
- `--vs-currency` sets the quote currency for CoinGecko requests (default: usd).
- `--pause` adds a delay between CoinGecko requests to stay under rate limits (default: 1 second).
