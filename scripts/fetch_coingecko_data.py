"""
Fetch cryptocurrency price data from CoinGecko, compute technical indicators, and
store them in the SQLite schema defined in ``db/schema.sql``. The script also
pulls an overall crypto market Fear & Greed index series.

Requires: requests, pandas

Example:
    python scripts/fetch_coingecko_data.py --database cryptobot.db
"""
from __future__ import annotations

import argparse
import datetime as dt
import sqlite3
import time
from dataclasses import dataclass
from typing import Iterable, List

import pandas as pd
import requests

DEFAULT_LOOKBACK_DAYS = 365 * 6  # roughly six years
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=0&date_format=us"


@dataclass(frozen=True)
class Asset:
    symbol: str
    name: str
    coingecko_id: str


ASSETS: List[Asset] = [
    Asset("BTC", "Bitcoin", "bitcoin"),
    Asset("ETH", "Ethereum", "ethereum"),
    Asset("XRP", "XRP", "ripple"),
    Asset("ADA", "Cardano", "cardano"),
    Asset("SOL", "Solana", "solana"),
    Asset("AVAX", "Avalanche", "avalanche-2"),
    Asset("LINK", "Chainlink", "chainlink"),
    Asset("LTC", "Litecoin", "litecoin"),
    Asset("XMR", "Monero", "monero"),
    Asset("ZEC", "Zcash", "zcash"),
    Asset("ALGO", "Algorand", "algorand"),
    Asset("HBAR", "Hedera", "hedera-hashgraph"),
    Asset("PAXG", "PAX Gold", "pax-gold"),
]


def fetch_market_chart(coin_id: str, vs_currency: str, days: int) -> pd.DataFrame:
    """Pull price history from CoinGecko and return a DataFrame indexed by date."""
    url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
    response = requests.get(
        url,
        params={"vs_currency": vs_currency, "days": days, "interval": "hourly"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    prices = payload.get("prices", [])
    if not prices:
        raise ValueError(f"No pricing data returned for {coin_id}")

    df = pd.DataFrame(prices, columns=["timestamp", "price"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("timestamp").sort_index()

    # Use daily closing price for indicator calculations.
    daily_prices = df["price"].resample("1D").last().dropna()
    return pd.DataFrame({"price": daily_prices})


def compute_indicators(price_series: pd.Series) -> pd.DataFrame:
    """Compute EMA, Bollinger Bands, and Stochastic RSI for a price series."""
    price_series = price_series.sort_index()
    ema = price_series.ewm(span=14, adjust=False).mean()

    rolling_mean = price_series.rolling(window=20).mean()
    rolling_std = price_series.rolling(window=20).std()
    bollinger_upper = rolling_mean + 2 * rolling_std
    bollinger_lower = rolling_mean - 2 * rolling_std

    delta = price_series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14, min_periods=14).mean()
    avg_loss = loss.rolling(window=14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    rsi_min = rsi.rolling(window=14, min_periods=14).min()
    rsi_max = rsi.rolling(window=14, min_periods=14).max()
    stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min)
    stoch_rsi = stoch_rsi.clip(lower=0, upper=1)

    return pd.DataFrame(
        {
            "price": price_series,
            "ema": ema,
            "bollinger_upper": bollinger_upper,
            "bollinger_lower": bollinger_lower,
            "stoch_rsi": stoch_rsi,
        }
    )


def build_interval_frames(price_df: pd.DataFrame) -> Iterable[tuple[str, pd.DataFrame]]:
    frequencies = {
        "daily": "1D",
        "weekly": "1W",
        "monthly": "1M",
    }
    for interval, freq in frequencies.items():
        sampled = price_df["price"].resample(freq).last().dropna()
        indicators = compute_indicators(sampled)
        indicators = indicators.dropna(subset=["price", "ema", "bollinger_upper", "bollinger_lower", "stoch_rsi"])
        interval_df = indicators.copy()
        interval_df["record_date"] = interval_df.index.date
        interval_df["interval"] = interval
        yield interval, interval_df


def ensure_cryptocurrency(conn: sqlite3.Connection, asset: Asset) -> int:
    cursor = conn.execute(
        "INSERT INTO cryptocurrencies (symbol, name) VALUES (?, ?)"
        " ON CONFLICT(symbol) DO UPDATE SET name=excluded.name",
        (asset.symbol, asset.name),
    )
    return cursor.lastrowid or conn.execute(
        "SELECT id FROM cryptocurrencies WHERE symbol = ?", (asset.symbol,)
    ).fetchone()[0]


def upsert_metrics(conn: sqlite3.Connection, crypto_id: int, interval_df: pd.DataFrame) -> None:
    rows = [
        (
            crypto_id,
            row.record_date,
            row.interval,
            float(row.price),
            float(row.ema),
            float(row.bollinger_upper),
            float(row.bollinger_lower),
            float(row.stoch_rsi),
        )
        for row in interval_df.itertuples()
    ]
    conn.executemany(
        """
        INSERT INTO crypto_price_metrics (
            cryptocurrency_id, record_date, interval, price, ema, bollinger_upper, bollinger_lower, stoch_rsi
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(cryptocurrency_id, interval, record_date) DO UPDATE SET
            price=excluded.price,
            ema=excluded.ema,
            bollinger_upper=excluded.bollinger_upper,
            bollinger_lower=excluded.bollinger_lower,
            stoch_rsi=excluded.stoch_rsi
        """,
        rows,
    )


def fetch_fear_greed_history() -> pd.DataFrame:
    response = requests.get(FEAR_GREED_URL, timeout=30)
    response.raise_for_status()
    data = response.json().get("data", [])
    if not data:
        raise ValueError("No fear & greed index data returned")

    records = []
    for entry in data:
        timestamp = entry["timestamp"]
        try:
            date = dt.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z").date()
        except (ValueError, TypeError):
            # Alternative.me sometimes returns unix timestamps as seconds.
            date = dt.datetime.utcfromtimestamp(int(timestamp)).date()
        records.append((date, int(entry["value"])))

    df = pd.DataFrame(records, columns=["record_date", "fear_greed_index"])
    df = df.drop_duplicates(subset=["record_date"]).sort_values("record_date")
    return df


def upsert_market_sentiment(conn: sqlite3.Connection, sentiment_df: pd.DataFrame) -> None:
    rows = [
        (row.record_date, int(row.fear_greed_index)) for row in sentiment_df.itertuples()
    ]
    conn.executemany(
        """
        INSERT INTO market_sentiment (record_date, fear_greed_index)
        VALUES (?, ?)
        ON CONFLICT(record_date) DO UPDATE SET fear_greed_index=excluded.fear_greed_index
        """,
        rows,
    )


def sync_asset(conn: sqlite3.Connection, asset: Asset, days: int, vs_currency: str, pause: float) -> None:
    price_df = fetch_market_chart(asset.coingecko_id, vs_currency, days)
    crypto_id = ensure_cryptocurrency(conn, asset)
    for _, interval_df in build_interval_frames(price_df):
        upsert_metrics(conn, crypto_id, interval_df)
    conn.commit()
    if pause:
        time.sleep(pause)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load CoinGecko data into the cryptobot database")
    parser.add_argument(
        "--database",
        default="cryptobot.db",
        help="Path to the SQLite database file to populate",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
        help="Number of trailing days to request from CoinGecko (default: 6 years)",
    )
    parser.add_argument(
        "--vs-currency",
        default="usd",
        help="Quote currency for CoinGecko requests (default: usd)",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=1.0,
        help="Seconds to wait between CoinGecko requests to avoid rate limits",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(args.database)
    conn.execute("PRAGMA foreign_keys = ON;")

    for asset in ASSETS:
        print(f"Syncing {asset.symbol}...")
        sync_asset(conn, asset, args.days, args.vs_currency, args.pause)

    print("Fetching market sentiment (Fear & Greed index)...")
    sentiment_df = fetch_fear_greed_history()
    upsert_market_sentiment(conn, sentiment_df)
    conn.commit()
    print("Done.")


if __name__ == "__main__":
    main()
