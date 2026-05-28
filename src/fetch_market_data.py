from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import pandas as pd
import pymysql
import requests

from paths import (
    BENCHMARK_METADATA_CSV,
    DATA_FETCH_FAILURES_CSV,
    DAILY_PRICES_CSV,
    ENV_FILE,
    RAW_DATA_DIR,
    ROOT,
    UNIVERSE_HOLDINGS_CSV,
    ensure_project_dirs,
)

XLK_HOLDINGS_URL = (
    "https://www.ssga.com/library-content/products/fund-data/"
    "etfs/us/holdings-daily-us-en-xlk.xlsx"
)

DEFAULT_START = "2020-01-01"
DEFAULT_DB_NAME = "us_stock_mvp"

BENCHMARKS = {
    "SP500": {
        "ticker": "^GSPC",
        "name": "S&P 500 Index",
        "asset_class": "index",
        "proxy_for": "US large-cap equity benchmark",
    },
    "NASDAQ100": {
        "ticker": "^NDX",
        "name": "NASDAQ 100 Index",
        "asset_class": "index",
        "proxy_for": "Nasdaq 100 benchmark",
    },
    "QQQ": {
        "ticker": "QQQ",
        "name": "Invesco QQQ Trust",
        "asset_class": "etf",
        "proxy_for": "tradable Nasdaq 100 ETF proxy",
    },
    "SP500_TECH": {
        "ticker": "XLK",
        "name": "Technology Select Sector SPDR Fund",
        "asset_class": "etf",
        "proxy_for": "tradable S&P 500 technology sector proxy",
    },
    "VIX": {
        "ticker": "^VIX",
        "name": "CBOE Volatility Index",
        "asset_class": "index",
        "proxy_for": "US equity implied volatility / fear gauge",
    },
    "TBILL_13W": {
        "ticker": "^IRX",
        "name": "13 Week Treasury Bill Yield",
        "asset_class": "rate",
        "proxy_for": "short-term USD risk-free rate proxy",
    },
}


@dataclass(frozen=True)
class MysqlConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def mysql_config() -> MysqlConfig:
    load_dotenv(ENV_FILE)
    return MysqlConfig(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", DEFAULT_DB_NAME),
    )


def request_bytes(url: str, *, timeout: int = 45) -> bytes:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0 Safari/537.36"
        ),
        "Accept": "*/*",
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.content


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper().replace(".", "-")


def is_us_equity_symbol(ticker: str) -> bool:
    if not ticker or ticker == "-":
        return False
    if ticker.startswith("^"):
        return False
    if not all(char.isalnum() or char == "-" for char in ticker):
        return False
    if any(char.isdigit() for char in ticker):
        return False
    return 1 <= len(ticker) <= 6


def read_manual_tickers(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None

    df = pd.read_csv(path)
    lower_map = {col.lower().strip(): col for col in df.columns}
    if "ticker" not in lower_map:
        raise ValueError(f"{path.name} must contain a ticker column")

    ticker_col = lower_map["ticker"]
    name_col = lower_map.get("name") or lower_map.get("company") or ticker_col
    sector_col = lower_map.get("sector")
    industry_col = lower_map.get("industry")

    out = pd.DataFrame(
        {
            "ticker": df[ticker_col].astype(str).map(normalize_ticker),
            "name": df[name_col].astype(str),
            "sector": df[sector_col].astype(str) if sector_col else "Unknown",
            "industry": df[industry_col].astype(str) if industry_col else "Unknown",
            "weight": pd.NA,
            "source": f"manual:{path.name}",
            "as_of_date": date.today().isoformat(),
            "survivorship_note": "Manual current universe; not survivor-bias-free unless delisted names and historical membership are included.",
        }
    )
    out = out[out["ticker"].map(is_us_equity_symbol)]
    return out.drop_duplicates("ticker").sort_values("ticker").reset_index(drop=True)


def fetch_xlk_holdings() -> pd.DataFrame:
    content = request_bytes(XLK_HOLDINGS_URL)
    raw = pd.read_excel(io.BytesIO(content), header=None)

    header_idx = None
    for idx, row in raw.iterrows():
        normalized = {str(value).strip().lower() for value in row.dropna().tolist()}
        if "ticker" in normalized and ("name" in normalized or "company name" in normalized):
            header_idx = idx
            break

    if header_idx is None:
        raise ValueError("Could not locate the holdings table header in the XLK workbook")

    header = raw.iloc[header_idx].astype(str).str.strip().tolist()
    data = raw.iloc[header_idx + 1 :].copy()
    data.columns = header
    data = data.dropna(how="all")

    colmap = {str(col).strip().lower(): col for col in data.columns}
    ticker_col = colmap.get("ticker")
    name_col = colmap.get("name") or colmap.get("company name")
    sector_col = colmap.get("sector")
    industry_col = colmap.get("industry")
    weight_col = colmap.get("weight")

    if not ticker_col or not name_col:
        raise ValueError("XLK workbook missing ticker/name columns")

    holdings = pd.DataFrame(
        {
            "ticker": data[ticker_col].astype(str).map(normalize_ticker),
            "name": data[name_col].astype(str).str.strip(),
            "sector": data[sector_col].astype(str).str.strip() if sector_col else "Information Technology",
            "industry": data[industry_col].astype(str).str.strip() if industry_col else "Unknown",
            "weight": pd.to_numeric(data[weight_col], errors="coerce") if weight_col else pd.NA,
        }
    )
    holdings = holdings[holdings["ticker"].map(is_us_equity_symbol)]
    holdings = holdings[~holdings["ticker"].isin(["NAN", "CASH_USD", "USD"])]
    holdings = holdings.drop_duplicates("ticker").sort_values("ticker").reset_index(drop=True)
    holdings["source"] = "State Street XLK daily holdings"
    holdings["as_of_date"] = date.today().isoformat()
    holdings["survivorship_note"] = (
        "Current XLK holdings used as an investable technology universe proxy. "
        "This is not survivor-bias-free historical index membership."
    )
    return holdings


def unix_ts(value: str, *, end: bool = False) -> int:
    parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if end:
        parsed = parsed + timedelta(days=1)
    return int(parsed.timestamp())


def yahoo_symbol(ticker: str) -> str:
    if ticker.startswith("^"):
        return ticker
    return ticker.replace(".", "-")


def fetch_yahoo_daily(ticker: str, start: str, end: str) -> pd.DataFrame:
    symbol = yahoo_symbol(ticker)
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}"
        f"?period1={unix_ts(start)}&period2={unix_ts(end, end=True)}"
        "&interval=1d&events=history%7Cdiv%7Csplit&includeAdjustedClose=true"
    )
    payload = json.loads(request_bytes(url).decode("utf-8"))
    chart = payload.get("chart", {})
    error = chart.get("error")
    if error:
        raise RuntimeError(f"Yahoo error for {ticker}: {error}")

    result = (chart.get("result") or [None])[0]
    if not result or not result.get("timestamp"):
        return pd.DataFrame()

    quote_data = result["indicators"]["quote"][0]
    adjclose_items = result["indicators"].get("adjclose") or [{}]
    adjclose = adjclose_items[0].get("adjclose")
    timestamps = result["timestamp"]

    df = pd.DataFrame(
        {
            "date": [datetime.fromtimestamp(ts, timezone.utc).date().isoformat() for ts in timestamps],
            "ticker": ticker,
            "open": quote_data.get("open"),
            "high": quote_data.get("high"),
            "low": quote_data.get("low"),
            "close": quote_data.get("close"),
            "adj_close": adjclose,
            "volume": quote_data.get("volume"),
        }
    )
    numeric_cols = ["open", "high", "low", "close", "adj_close", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)


def fetch_many_prices(tickers: Iterable[str], start: str, end: str, pause: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    errors: list[dict[str, str]] = []
    unique_tickers = list(dict.fromkeys(tickers))

    for idx, ticker in enumerate(unique_tickers, start=1):
        print(f"[{idx:03d}/{len(unique_tickers):03d}] fetching {ticker}", flush=True)
        try:
            df = fetch_yahoo_daily(ticker, start, end)
            if df.empty:
                errors.append({"ticker": ticker, "error": "empty Yahoo response"})
            else:
                frames.append(df)
        except Exception as exc:  # noqa: BLE001 - log and continue for data coverage report.
            errors.append({"ticker": ticker, "error": str(exc)})
        time.sleep(pause)

    prices = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    failures = pd.DataFrame(errors, columns=["ticker", "error"])
    return prices, failures


def build_benchmark_metadata() -> pd.DataFrame:
    rows = []
    for code, item in BENCHMARKS.items():
        rows.append(
            {
                "code": code,
                "ticker": item["ticker"],
                "name": item["name"],
                "asset_class": item["asset_class"],
                "proxy_for": item["proxy_for"],
                "source": "Yahoo Finance chart API",
            }
        )
    return pd.DataFrame(rows)


def connect_without_db(config: MysqlConfig):
    return pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        charset="utf8mb4",
        autocommit=True,
    )


def connect_db(config: MysqlConfig):
    return pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        charset="utf8mb4",
        autocommit=False,
    )


def create_database_and_tables(config: MysqlConfig) -> None:
    with connect_without_db(config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )

    ddl = [
        """
        CREATE TABLE IF NOT EXISTS universe_holdings (
            ticker VARCHAR(32) NOT NULL,
            name VARCHAR(255) NOT NULL,
            sector VARCHAR(128) NULL,
            industry VARCHAR(255) NULL,
            weight DECIMAL(18,8) NULL,
            source VARCHAR(255) NOT NULL,
            as_of_date DATE NOT NULL,
            survivorship_note TEXT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, source, as_of_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS daily_prices (
            ticker VARCHAR(32) NOT NULL,
            trade_date DATE NOT NULL,
            open DECIMAL(20,8) NULL,
            high DECIMAL(20,8) NULL,
            low DECIMAL(20,8) NULL,
            close DECIMAL(20,8) NULL,
            adj_close DECIMAL(20,8) NULL,
            volume BIGINT NULL,
            source VARCHAR(64) NOT NULL DEFAULT 'Yahoo Finance chart API',
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, trade_date),
            INDEX idx_trade_date (trade_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS benchmark_metadata (
            code VARCHAR(64) NOT NULL PRIMARY KEY,
            ticker VARCHAR(32) NOT NULL,
            name VARCHAR(255) NOT NULL,
            asset_class VARCHAR(64) NOT NULL,
            proxy_for VARCHAR(255) NOT NULL,
            source VARCHAR(255) NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS data_fetch_log (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            run_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            universe_source VARCHAR(255) NOT NULL,
            ticker_count INT NOT NULL,
            price_rows INT NOT NULL,
            failure_count INT NOT NULL,
            note TEXT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ]

    with connect_db(config) as conn:
        with conn.cursor() as cur:
            for statement in ddl:
                cur.execute(statement)
        conn.commit()


def none_if_na(value):
    if pd.isna(value):
        return None
    return value


def upsert_holdings(conn, holdings: pd.DataFrame) -> None:
    sql = """
        INSERT INTO universe_holdings
            (ticker, name, sector, industry, weight, source, as_of_date, survivorship_note)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            sector = VALUES(sector),
            industry = VALUES(industry),
            weight = VALUES(weight),
            survivorship_note = VALUES(survivorship_note)
    """
    rows = [
        (
            row.ticker,
            row.name,
            none_if_na(row.sector),
            none_if_na(row.industry),
            none_if_na(row.weight),
            row.source,
            row.as_of_date,
            row.survivorship_note,
        )
        for row in holdings.itertuples(index=False)
    ]
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def upsert_prices(conn, prices: pd.DataFrame) -> None:
    sql = """
        INSERT INTO daily_prices
            (ticker, trade_date, open, high, low, close, adj_close, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            open = VALUES(open),
            high = VALUES(high),
            low = VALUES(low),
            close = VALUES(close),
            adj_close = VALUES(adj_close),
            volume = VALUES(volume)
    """
    rows = [
        (
            row.ticker,
            row.date,
            none_if_na(row.open),
            none_if_na(row.high),
            none_if_na(row.low),
            none_if_na(row.close),
            none_if_na(row.adj_close),
            int(row.volume) if not pd.isna(row.volume) else None,
        )
        for row in prices.itertuples(index=False)
    ]
    with conn.cursor() as cur:
        batch_size = 5000
        for idx in range(0, len(rows), batch_size):
            cur.executemany(sql, rows[idx : idx + batch_size])


def upsert_benchmarks(conn, benchmarks: pd.DataFrame) -> None:
    sql = """
        INSERT INTO benchmark_metadata
            (code, ticker, name, asset_class, proxy_for, source)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            ticker = VALUES(ticker),
            name = VALUES(name),
            asset_class = VALUES(asset_class),
            proxy_for = VALUES(proxy_for),
            source = VALUES(source)
    """
    rows = [tuple(row) for row in benchmarks.to_numpy()]
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def insert_fetch_log(
    conn,
    *,
    start: str,
    end: str,
    holdings: pd.DataFrame,
    prices: pd.DataFrame,
    failures: pd.DataFrame,
) -> None:
    sql = """
        INSERT INTO data_fetch_log
            (start_date, end_date, universe_source, ticker_count, price_rows, failure_count, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    source = holdings["source"].iloc[0] if not holdings.empty else "unknown"
    note = "Benchmarks included: " + ", ".join(item["ticker"] for item in BENCHMARKS.values())
    with conn.cursor() as cur:
        cur.execute(sql, (start, end, source, holdings["ticker"].nunique(), len(prices), len(failures), note))


def write_mysql(config: MysqlConfig, holdings: pd.DataFrame, benchmarks: pd.DataFrame, prices: pd.DataFrame, failures: pd.DataFrame, start: str, end: str) -> None:
    create_database_and_tables(config)
    with connect_db(config) as conn:
        upsert_holdings(conn, holdings)
        upsert_benchmarks(conn, benchmarks)
        upsert_prices(conn, prices)
        insert_fetch_log(conn, start=start, end=end, holdings=holdings, prices=prices, failures=failures)
        conn.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch US equity universe, benchmark prices, CSV files, and MySQL tables.")
    parser.add_argument("--start", default=DEFAULT_START, help="Start date, YYYY-MM-DD. Default: 2020-01-01.")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date, YYYY-MM-DD. Default: today.")
    parser.add_argument("--tickers-file", default="tickers.csv", help="Optional manual universe CSV with a ticker column.")
    parser.add_argument("--skip-mysql", action="store_true", help="Only write CSV files; do not connect to MySQL.")
    parser.add_argument("--summary-only", action="store_true", help="Print row counts for existing CSV files and exit.")
    parser.add_argument("--mysql-from-csv", action="store_true", help="Load existing root CSV files into MySQL without fetching data.")
    parser.add_argument("--mysql-summary", action="store_true", help="Print row counts from MySQL and exit.")
    parser.add_argument("--pause", type=float, default=0.10, help="Pause in seconds between Yahoo requests.")
    return parser.parse_args()


def read_existing_csvs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    holdings = pd.read_csv(UNIVERSE_HOLDINGS_CSV)
    benchmarks = pd.read_csv(BENCHMARK_METADATA_CSV)
    prices = pd.read_csv(DAILY_PRICES_CSV)
    failures = pd.read_csv(DATA_FETCH_FAILURES_CSV)
    return holdings, benchmarks, prices, failures


def print_csv_summary() -> None:
    holdings, _, prices, failures = read_existing_csvs()

    print(f"holdings={len(holdings)}", flush=True)
    print(f"price_rows={len(prices)}", flush=True)
    print(f"priced_tickers={prices['ticker'].nunique()}", flush=True)
    print(f"date_min={prices['date'].min()} date_max={prices['date'].max()}", flush=True)
    print(f"kind_tickers={prices.groupby('kind')['ticker'].nunique().to_dict()}", flush=True)
    print(f"kind_rows={prices.groupby('kind').size().to_dict()}", flush=True)
    print(f"failures={len(failures)}", flush=True)


def print_mysql_summary() -> None:
    config = mysql_config()
    with connect_db(config) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), COUNT(DISTINCT ticker), MIN(trade_date), MAX(trade_date) FROM daily_prices")
            price_count, ticker_count, min_date, max_date = cur.fetchone()
            cur.execute("SELECT COUNT(*), COUNT(DISTINCT ticker) FROM universe_holdings")
            holding_count, holding_ticker_count = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM benchmark_metadata")
            benchmark_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM data_fetch_log")
            log_count = cur.fetchone()[0]

    print(f"mysql_database={config.database}", flush=True)
    print(f"daily_prices_rows={price_count}", flush=True)
    print(f"daily_prices_tickers={ticker_count}", flush=True)
    print(f"daily_prices_date_min={min_date} date_max={max_date}", flush=True)
    print(f"universe_holdings_rows={holding_count}", flush=True)
    print(f"universe_holdings_tickers={holding_ticker_count}", flush=True)
    print(f"benchmark_metadata_rows={benchmark_count}", flush=True)
    print(f"data_fetch_log_rows={log_count}", flush=True)


def main() -> int:
    ensure_project_dirs()
    args = parse_args()
    if args.summary_only:
        print_csv_summary()
        return 0

    if args.mysql_summary:
        print_mysql_summary()
        return 0

    if args.mysql_from_csv:
        holdings, benchmarks, prices, failures = read_existing_csvs()
        config = mysql_config()
        print(f"Writing existing CSV files to MySQL database {config.database} at {config.host}:{config.port}...", flush=True)
        mysql_prices = prices.drop(columns=["kind"]) if "kind" in prices.columns else prices
        write_mysql(config, holdings, benchmarks, mysql_prices, failures, args.start, args.end)
        print("Done.", flush=True)
        return 0

    tickers_path = ROOT / args.tickers_file

    print("Loading stock universe...", flush=True)
    holdings = read_manual_tickers(tickers_path)
    if holdings is None:
        holdings = fetch_xlk_holdings()

    benchmarks = build_benchmark_metadata()
    stock_tickers = holdings["ticker"].dropna().astype(str).tolist()
    benchmark_tickers = benchmarks["ticker"].dropna().astype(str).tolist()
    all_tickers = stock_tickers + benchmark_tickers

    print(f"Universe tickers: {len(stock_tickers)}", flush=True)
    print(f"Benchmark tickers: {', '.join(benchmark_tickers)}", flush=True)
    prices, failures = fetch_many_prices(all_tickers, args.start, args.end, args.pause)

    if prices.empty:
        raise RuntimeError("No price data was fetched; check network access and ticker symbols.")

    prices["kind"] = prices["ticker"].where(prices["ticker"].isin(stock_tickers), "benchmark")
    prices.loc[prices["ticker"].isin(stock_tickers), "kind"] = "stock"

    holdings.to_csv(UNIVERSE_HOLDINGS_CSV, index=False, encoding="utf-8")
    benchmarks.to_csv(BENCHMARK_METADATA_CSV, index=False, encoding="utf-8")
    prices.to_csv(DAILY_PRICES_CSV, index=False, encoding="utf-8")
    failures.to_csv(DATA_FETCH_FAILURES_CSV, index=False, encoding="utf-8")

    if not args.skip_mysql:
        config = mysql_config()
        print(f"Writing MySQL database {config.database} at {config.host}:{config.port}...", flush=True)
        write_mysql(config, holdings, benchmarks, prices.drop(columns=["kind"]), failures, args.start, args.end)

    print("Done.", flush=True)
    print(f"CSV: {UNIVERSE_HOLDINGS_CSV}", flush=True)
    print(f"CSV: {BENCHMARK_METADATA_CSV}", flush=True)
    print(f"CSV: {DAILY_PRICES_CSV}", flush=True)
    print(f"CSV: {DATA_FETCH_FAILURES_CSV}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
