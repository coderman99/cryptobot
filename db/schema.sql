-- Schema for cryptocurrency technical indicator tracking
-- This script creates the tables needed to store cryptocurrencies and
-- their technical indicator values for daily, weekly, and monthly intervals.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cryptocurrencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crypto_price_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cryptocurrency_id INTEGER NOT NULL,
    record_date DATE NOT NULL,
    interval TEXT NOT NULL CHECK (interval IN ('daily', 'weekly', 'monthly')),
    price NUMERIC NOT NULL,
    ema NUMERIC NOT NULL,
    bollinger_upper NUMERIC NOT NULL,
    bollinger_lower NUMERIC NOT NULL,
    stoch_rsi NUMERIC NOT NULL,
    UNIQUE (cryptocurrency_id, interval, record_date),
    FOREIGN KEY (cryptocurrency_id) REFERENCES cryptocurrencies(id) ON DELETE CASCADE
);
