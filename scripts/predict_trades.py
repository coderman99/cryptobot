"""
Simulate a simple rule-based trading model using stored indicators.

The model:
- Uses daily indicator data from the SQLite database.
- Buys when Stoch RSI is oversold (<0.2) and price trades below the lower Bollinger band.
- Sells when Stoch RSI is overbought (>0.8) and price trades above the upper Bollinger band.
- Starts with a single cash allocation (default: $1000) and holds one position at a time.
- Reports profit and the holding duration for each completed trade over a one-year period
  (configurable via --lookback-days).

Example:
    python scripts/predict_trades.py --database cryptobot.db --symbol BTC
"""
from __future__ import annotations

import argparse
import datetime as dt
import sqlite3
from dataclasses import dataclass
from typing import Iterable, List, Optional

import pandas as pd


@dataclass
class Trade:
    buy_date: dt.date
    sell_date: dt.date
    buy_price: float
    sell_price: float
    shares: float

    @property
    def profit(self) -> float:
        return (self.sell_price - self.buy_price) * self.shares

    @property
    def hold_days(self) -> int:
        return (self.sell_date - self.buy_date).days


def load_price_metrics(
    conn: sqlite3.Connection,
    symbol: str,
    lookback_days: int,
    interval: str = "daily",
) -> pd.DataFrame:
    cutoff = dt.date.today() - dt.timedelta(days=lookback_days)
    query = """
        SELECT m.record_date, m.price, m.bollinger_upper, m.bollinger_lower, m.stoch_rsi
        FROM crypto_price_metrics m
        JOIN cryptocurrencies c ON c.id = m.cryptocurrency_id
        WHERE c.symbol = ? AND m.interval = ? AND m.record_date >= ?
        ORDER BY m.record_date ASC
    """
    df = pd.read_sql_query(
        query,
        conn,
        params=(symbol, interval, cutoff.isoformat()),
        parse_dates=["record_date"],
    )
    if df.empty:
        raise ValueError(
            f"No metrics found for {symbol} at interval '{interval}' within the last {lookback_days} days"
        )
    return df.set_index("record_date")


def generate_signals(metrics: pd.DataFrame) -> pd.Series:
    """Return a signal series: 1 for buy, -1 for sell, 0 for hold."""
    buy_signal = (metrics["stoch_rsi"] < 0.2) & (metrics["price"] < metrics["bollinger_lower"])
    sell_signal = (metrics["stoch_rsi"] > 0.8) & (metrics["price"] > metrics["bollinger_upper"])
    signals = pd.Series(0, index=metrics.index)
    signals.loc[buy_signal] = 1
    signals.loc[sell_signal] = -1
    return signals


def simulate_trades(
    metrics: pd.DataFrame,
    starting_capital: float,
) -> List[Trade]:
    signals = generate_signals(metrics)
    trades: List[Trade] = []
    position_open: Optional[Trade] = None
    cash = starting_capital

    for date, row in metrics.iterrows():
        signal = signals.loc[date]
        price = float(row["price"])

        if signal == 1 and position_open is None:
            shares = cash / price
            position_open = Trade(
                buy_date=date.date(),
                sell_date=date.date(),
                buy_price=price,
                sell_price=price,
                shares=shares,
            )
            cash = 0.0
        elif signal == -1 and position_open is not None:
            position_open.sell_date = date.date()  # type: ignore[assignment]
            position_open.sell_price = price  # type: ignore[assignment]
            trades.append(position_open)
            cash = position_open.shares * price
            position_open = None

    # If a position remains open at the end of the window, close it at the final price.
    if position_open is not None:
        final_price = float(metrics.iloc[-1]["price"])
        position_open.sell_date = metrics.index[-1].date()  # type: ignore[assignment]
        position_open.sell_price = final_price  # type: ignore[assignment]
        trades.append(position_open)

    return trades


def summarize_trades(trades: Iterable[Trade]) -> dict:
    trade_list = list(trades)
    total_profit = sum(t.profit for t in trade_list)
    total_hold_days = sum(t.hold_days for t in trade_list)
    average_hold = total_hold_days / len(trade_list) if trade_list else 0.0
    return {
        "trades": trade_list,
        "total_profit": total_profit,
        "average_hold_days": average_hold,
    }


def format_report(summary: dict, symbol: str, starting_capital: float, lookback_days: int) -> str:
    lines = [
        f"Symbol: {symbol}",
        f"Lookback: {lookback_days} days", 
        f"Starting capital: ${starting_capital:,.2f}",
        f"Total profit: ${summary['total_profit']:,.2f}",
        f"Average hold (days): {summary['average_hold_days']:.1f}",
        "",
        "Trades:",
    ]
    if not summary["trades"]:
        lines.append("  No trades generated for the chosen signals.")
    else:
        for idx, trade in enumerate(summary["trades"], start=1):
            lines.append(
                f"  {idx}. Buy {trade.buy_date} @ ${trade.buy_price:,.2f} | "
                f"Sell {trade.sell_date} @ ${trade.sell_price:,.2f} | "
                f"Hold: {trade.hold_days} days | Profit: ${trade.profit:,.2f}"
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict buy/sell trades from stored indicators")
    parser.add_argument("--database", default="cryptobot.db", help="SQLite database file")
    parser.add_argument("--symbol", required=True, help="Ticker symbol (e.g., BTC, ETH)")
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=365,
        help="How many trailing days to consider (default: 365)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1000.0,
        help="Starting capital for the simulation (default: 1000)",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(args.database)
    conn.execute("PRAGMA foreign_keys = ON;")

    metrics = load_price_metrics(conn, args.symbol, args.lookback_days)
    trades = simulate_trades(metrics, args.capital)
    summary = summarize_trades(trades)

    report = format_report(summary, args.symbol, args.capital, args.lookback_days)
    print(report)


if __name__ == "__main__":
    main()
