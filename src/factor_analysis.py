"""PCA 因子分析。

把 50 支美股科技股的日收益矩阵做主成分分解，提取潜在因子。
对当前数据规模（50 支 × ≈1500 个交易日），PCA 比 LSTM/Transformer
等深度模型更合适，因为协方差结构的信噪比远高于序列预测。

输出（写入 data/output/）：
- pc_explained_variance.csv：每个 PC 的解释方差比与累计解释比，
  用于在答辩稿里展示 “前 K 个 PC 解释了多少协方差”。
- pc_loadings.csv：每只股票在前 K 个 PC 上的载荷，用于因子解释。
- pc_returns.csv：日频 PC 收益序列（PC1 ≈ 市场因子，PC2/3 通常解释行业/风格）。

使用：
    python src/factor_analysis.py --components 5
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from analysis_engine import return_matrix
from paths import ANALYSIS_UNIVERSE_50_CSV, DAILY_PRICES_CSV, OUTPUT_DIR, ensure_project_dirs


DEFAULT_COMPONENTS = 5


def load_stock_returns() -> pd.DataFrame:
    universe = pd.read_csv(ANALYSIS_UNIVERSE_50_CSV)
    tickers = universe["ticker"].tolist()
    prices = pd.read_csv(DAILY_PRICES_CSV, parse_dates=["date"])
    subset = prices[prices["ticker"].isin(tickers)].copy()
    subset["price"] = subset["adj_close"].fillna(subset["close"])
    wide = subset.pivot(index="date", columns="ticker", values="price").sort_index().ffill()
    return return_matrix(wide).dropna(how="any")


def run_pca(returns: pd.DataFrame, n_components: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """对中心化后的日收益做 PCA，返回 (loadings, pc_returns, explained)。"""
    centered = returns - returns.mean()
    pca = PCA(n_components=n_components)
    scores = pca.fit_transform(centered.values)

    pc_columns = [f"PC{i + 1}" for i in range(n_components)]
    loadings = pd.DataFrame(
        pca.components_.T,
        index=returns.columns,
        columns=pc_columns,
    )
    loadings.index.name = "ticker"

    pc_returns = pd.DataFrame(scores, index=returns.index, columns=pc_columns)
    pc_returns.index.name = "date"

    explained = pd.DataFrame(
        {
            "component": pc_columns,
            "explained_variance_ratio": pca.explained_variance_ratio_,
            "cumulative_ratio": np.cumsum(pca.explained_variance_ratio_),
        }
    )
    return loadings, pc_returns, explained


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="50 股日收益 PCA 因子分析。")
    parser.add_argument(
        "--components",
        type=int,
        default=DEFAULT_COMPONENTS,
        help=f"提取的主成分数量，默认 {DEFAULT_COMPONENTS}。",
    )
    return parser.parse_args()


def main() -> int:
    ensure_project_dirs()
    args = parse_args()
    returns = load_stock_returns()
    if returns.empty:
        raise RuntimeError("收益矩阵为空，请先运行 analysis_engine.py 生成数据。")

    loadings, pc_returns, explained = run_pca(returns, args.components)
    loadings.reset_index().to_csv(OUTPUT_DIR / "pc_loadings.csv", index=False)
    pc_returns.reset_index().to_csv(OUTPUT_DIR / "pc_returns.csv", index=False)
    explained.to_csv(OUTPUT_DIR / "pc_explained_variance.csv", index=False)

    print(f"wrote PCA outputs to {OUTPUT_DIR}", flush=True)
    print(explained.to_string(index=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
