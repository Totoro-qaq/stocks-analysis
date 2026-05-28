from __future__ import annotations

import pandas as pd

from fetch_market_data import ROOT, connect_db, mysql_config
from paths import ANALYSIS_UNIVERSE_50_CSV, DAILY_PRICES_CSV, UNIVERSE_HOLDINGS_CSV, ensure_project_dirs


OUTPUT = ANALYSIS_UNIVERSE_50_CSV


def scaled_rank(series: pd.Series, ascending: bool = False) -> pd.Series:
    ranks = series.rank(method="average", ascending=ascending)
    if len(ranks) == 1:
        return pd.Series(1.0, index=series.index)
    return 1 - (ranks - 1) / (len(ranks) - 1)


def build_universe() -> pd.DataFrame:
    holdings = pd.read_csv(UNIVERSE_HOLDINGS_CSV)
    prices = pd.read_csv(DAILY_PRICES_CSV, parse_dates=["date"])

    stock_prices = prices[prices["kind"].eq("stock")].copy()
    qqq_calendar = prices[prices["ticker"].eq("QQQ")]["date"].nunique()
    max_date = stock_prices["date"].max()
    last_dates = sorted(stock_prices["date"].drop_duplicates())
    last_252_dates = set(last_dates[-252:])

    grouped = stock_prices.groupby("ticker")
    metrics = grouped.agg(
        first_date=("date", "min"),
        last_date=("date", "max"),
        price_observations=("date", "nunique"),
    )
    metrics["data_coverage"] = metrics["price_observations"] / qqq_calendar

    recent = stock_prices[stock_prices["date"].isin(last_252_dates)].copy()
    recent["dollar_volume"] = recent["adj_close"].fillna(recent["close"]) * recent["volume"]
    liquidity = recent.groupby("ticker")["dollar_volume"].mean().rename("avg_dollar_volume_252")
    metrics = metrics.join(liquidity, how="left").reset_index()

    merged = holdings.merge(metrics, on="ticker", how="inner")
    merged["weight"] = pd.to_numeric(merged["weight"], errors="coerce").fillna(0)
    merged["avg_dollar_volume_252"] = pd.to_numeric(merged["avg_dollar_volume_252"], errors="coerce").fillna(0)

    eligible = merged[
        merged["last_date"].eq(max_date)
        & merged["data_coverage"].ge(0.95)
        & merged["avg_dollar_volume_252"].gt(0)
    ].copy()

    if len(eligible) < 50:
        eligible = merged[
            merged["last_date"].eq(max_date)
            & merged["data_coverage"].ge(0.90)
            & merged["avg_dollar_volume_252"].gt(0)
        ].copy()

    if len(eligible) < 50:
        raise RuntimeError(f"Only {len(eligible)} eligible tickers after relaxed filters; cannot build a 50-stock universe.")

    eligible["weight_score"] = scaled_rank(eligible["weight"], ascending=False)
    eligible["liquidity_score"] = scaled_rank(eligible["avg_dollar_volume_252"], ascending=False)
    eligible["coverage_score"] = scaled_rank(eligible["data_coverage"], ascending=False)
    eligible["selection_score"] = (
        0.45 * eligible["weight_score"]
        + 0.35 * eligible["liquidity_score"]
        + 0.20 * eligible["coverage_score"]
    )

    selected = eligible.sort_values(
        ["selection_score", "weight", "avg_dollar_volume_252"],
        ascending=[False, False, False],
    ).head(50)
    selected = selected.sort_values("selection_score", ascending=False).reset_index(drop=True)
    selected["selection_rank"] = selected.index + 1
    selected["selection_reason"] = (
        "Selected from current official XLK holdings using price coverage >= 95%, current data availability, "
        "XLK weight, and recent dollar-volume liquidity. This is a real current technology universe, "
        "not point-in-time survivor-bias-free historical membership."
    )

    columns = [
        "selection_rank",
        "ticker",
        "name",
        "sector",
        "industry",
        "weight",
        "first_date",
        "last_date",
        "price_observations",
        "data_coverage",
        "avg_dollar_volume_252",
        "selection_score",
        "selection_reason",
    ]
    return selected[columns]


def write_mysql(selected: pd.DataFrame) -> None:
    config = mysql_config()
    ddl = """
        CREATE TABLE IF NOT EXISTS analysis_universe_50 (
            selection_rank INT NOT NULL,
            ticker VARCHAR(32) NOT NULL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            sector VARCHAR(128) NULL,
            industry VARCHAR(255) NULL,
            xlk_weight DECIMAL(18,8) NULL,
            first_date DATE NOT NULL,
            last_date DATE NOT NULL,
            price_observations INT NOT NULL,
            data_coverage DECIMAL(12,8) NOT NULL,
            avg_dollar_volume_252 DECIMAL(24,4) NOT NULL,
            selection_score DECIMAL(12,8) NOT NULL,
            selection_reason TEXT NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """
    insert_sql = """
        INSERT INTO analysis_universe_50
            (selection_rank, ticker, name, sector, industry, xlk_weight, first_date, last_date,
             price_observations, data_coverage, avg_dollar_volume_252, selection_score, selection_reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            selection_rank = VALUES(selection_rank),
            name = VALUES(name),
            sector = VALUES(sector),
            industry = VALUES(industry),
            xlk_weight = VALUES(xlk_weight),
            first_date = VALUES(first_date),
            last_date = VALUES(last_date),
            price_observations = VALUES(price_observations),
            data_coverage = VALUES(data_coverage),
            avg_dollar_volume_252 = VALUES(avg_dollar_volume_252),
            selection_score = VALUES(selection_score),
            selection_reason = VALUES(selection_reason)
    """
    rows = [
        (
            int(row.selection_rank),
            row.ticker,
            row.name,
            row.sector,
            row.industry,
            float(row.weight),
            row.first_date.date().isoformat() if hasattr(row.first_date, "date") else str(row.first_date),
            row.last_date.date().isoformat() if hasattr(row.last_date, "date") else str(row.last_date),
            int(row.price_observations),
            float(row.data_coverage),
            float(row.avg_dollar_volume_252),
            float(row.selection_score),
            row.selection_reason,
        )
        for row in selected.itertuples(index=False)
    ]
    with connect_db(config) as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            cur.executemany(insert_sql, rows)
        conn.commit()


def main() -> int:
    ensure_project_dirs()
    selected = build_universe()
    selected.to_csv(OUTPUT, index=False, encoding="utf-8")
    write_mysql(selected)
    print(f"wrote {OUTPUT}", flush=True)
    print(f"selected_tickers={','.join(selected['ticker'].tolist())}", flush=True)
    print(f"rows={len(selected)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
