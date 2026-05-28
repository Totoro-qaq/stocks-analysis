"""Fama-French 因子回归与归因。

对每只股票和每个组合做五因子 + 动量因子回归，
拆解超额收益来源（α vs 因子暴露）。

数据来源: Kenneth French Data Library
  F-F_Research_Data_5_Factors_2x3_daily.CSV
  F-F_Momentum_Factor_daily.CSV
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm

from paths import OUTPUT_DIR, ensure_project_dirs

# Kenneth French 日频因子文件名
FF5_FACTORS_FILE = "F-F_Research_Data_5_Factors_2x3_daily.CSV"
MOMENTUM_FILE = "F-F_Momentum_Factor_daily.CSV"


def load_ff_factors(factors_dir: str | Path | None = None) -> pd.DataFrame:
    """
    加载 Fama-French 五因子 + 动量因子（日频）。

    返回 DataFrame，列为 Mkt-RF, SMB, HML, RMW, CMA, Mom, RF
    值为小数（非百分比），index 为 date。
    """
    if factors_dir is None:
        factors_dir = Path("data/raw")

    factors_dir = Path(factors_dir)

    ff5_path = factors_dir / FF5_FACTORS_FILE
    if not ff5_path.exists():
        raise FileNotFoundError(
            f"Fama-French 5-factor file not found: {ff5_path}. "
            "Download from https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html"
        )

    # 解析 Kenneth French CSV 格式（前 3 行为标题，数据从第 4 行开始）
    ff5 = pd.read_csv(ff5_path, skiprows=3)
    ff5 = ff5.rename(columns={ff5.columns[0]: "date"})
    ff5["date"] = pd.to_datetime(ff5["date"].astype(str).str.strip(), format="%Y%m%d", errors="coerce")
    ff5 = ff5.set_index("date")
    # 转换为小数
    ff5 = ff5.apply(pd.to_numeric, errors="coerce") / 100.0

    # 动量因子
    mom_path = factors_dir / MOMENTUM_FILE
    if mom_path.exists():
        mom = pd.read_csv(mom_path, skiprows=13)
        mom = mom.rename(columns={mom.columns[0]: "date"})
        mom["date"] = pd.to_datetime(mom["date"].astype(str).str.strip(), format="%Y%m%d", errors="coerce")
        mom = mom.set_index("date")
        mom = mom.apply(pd.to_numeric, errors="coerce") / 100.0
        mom_col = [c for c in mom.columns if "Mom" in c or "mom" in c.lower()]
        if mom_col:
            ff5["Mom"] = mom[mom_col[0]]

    return ff5.dropna(how="all")


def single_stock_factor_regression(
    stock_returns: pd.Series,
    factors: pd.DataFrame,
) -> dict[str, Any]:
    """
    对单只股票做 Fama-French 因子回归。

    参数:
        stock_returns: 日收益序列
        factors: FF 因子 DataFrame（Mkt-RF, SMB, HML, RMW, CMA, Mom, RF）

    返回:
        回归结果字典
    """
    trading_days = 252

    # 超额收益
    if "RF" in factors.columns:
        excess_returns = stock_returns - factors["RF"]
        X_factors = factors.drop(columns=["RF"])
    else:
        excess_returns = stock_returns
        X_factors = factors

    aligned = pd.concat([excess_returns, X_factors], axis=1).dropna()
    if len(aligned) < 60:
        return {"error": "insufficient observations", "observations": len(aligned)}

    y = aligned.iloc[:, 0]
    X = sm.add_constant(aligned.iloc[:, 1:])

    try:
        model = sm.OLS(y, X).fit()
    except Exception as exc:
        return {"error": str(exc)}

    betas = {}
    for col in X_factors.columns:
        if col in model.params.index:
            betas[col] = float(model.params[col])

    const_key = "const"
    alpha_daily = float(model.params.get(const_key, 0.0))
    alpha_annualized = alpha_daily * trading_days

    return {
        "alpha_annualized": alpha_annualized,
        "alpha_daily": alpha_daily,
        "alpha_t_stat": float(model.tvalues.get(const_key, np.nan)),
        "alpha_pvalue": float(model.pvalues.get(const_key, np.nan)),
        "alpha_significant_5pct": float(model.pvalues.get(const_key, 1.0)) < 0.05,
        "betas": betas,
        "r_squared": float(model.rsquared),
        "adj_r_squared": float(model.rsquared_adj),
        "f_statistic": float(model.fvalue) if model.fvalue is not None else np.nan,
        "observations": int(len(aligned)),
        "condition_number": float(model.condition_number) if model.condition_number is not None else np.nan,
    }


def run_factor_regression_all_stocks(
    returns: pd.DataFrame,
    factors: pd.DataFrame,
) -> pd.DataFrame:
    """对 50 只股票逐一做因子回归，返回汇总表。"""
    rows = []
    for ticker in returns.columns:
        stock_ret = returns[ticker]
        result = single_stock_factor_regression(stock_ret, factors)
        row = {"ticker": ticker}
        row.update(result)
        rows.append(row)
    return pd.DataFrame(rows)


def portfolio_factor_attribution(
    portfolio_returns: pd.Series,
    factors: pd.DataFrame,
) -> dict[str, Any]:
    """
    对组合收益做因子归因。

    返回:
        因子贡献分解字典
    """
    trading_days = 252

    if "RF" in factors.columns:
        excess_returns = portfolio_returns - factors["RF"]
        X_factors = factors.drop(columns=["RF"])
    else:
        excess_returns = portfolio_returns
        X_factors = factors

    aligned = pd.concat([excess_returns, X_factors], axis=1).dropna()
    y = aligned.iloc[:, 0]
    X = sm.add_constant(aligned.iloc[:, 1:])

    model = sm.OLS(y, X).fit()

    factor_contributions = {}
    for col in X_factors.columns:
        if col in model.params.index:
            factor_mean = aligned[col].mean()
            factor_contributions[col] = float(model.params[col] * factor_mean * trading_days)

    const_key = "const"
    alpha_contribution = float(model.params.get(const_key, 0.0)) * trading_days
    total_return = y.mean() * trading_days

    return {
        "total_annualized_return": total_return,
        "alpha_contribution": alpha_contribution,
        "factor_contributions": factor_contributions,
        "r_squared": float(model.rsquared),
        "adj_r_squared": float(model.rsquared_adj),
        "alpha_t_stat": float(model.tvalues.get(const_key, np.nan)),
        "alpha_pvalue": float(model.pvalues.get(const_key, np.nan)),
    }
