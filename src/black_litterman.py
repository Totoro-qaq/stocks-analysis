"""Black-Litterman 模型 — 贝叶斯观点融合。

将人工规则从粗暴乘数升级为贝叶斯框架：
  后验收益 = 加权融合(市场均衡收益, 人工观点)

参考文献:
  Black & Litterman (1992), He & Litterman (1999)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def implied_equilibrium_returns(
    market_weights: pd.Series,
    covariance: pd.DataFrame,
    risk_aversion: float = 2.5,
) -> pd.Series:
    """
    从市值权重反向推出市场隐含均衡收益。

    π = λ × Σ × w_mkt

    参数:
        market_weights: 市值权重（可从 XLK weight 列获取）
        covariance: 年化协方差矩阵
        risk_aversion: 风险厌恶系数 λ（通常 2-4）

    返回:
        隐含均衡收益（年化）
    """
    aligned_cov = covariance.loc[market_weights.index, market_weights.index]
    return risk_aversion * aligned_cov @ market_weights


def black_litterman_posterior(
    prior_returns: pd.Series,
    covariance: pd.DataFrame,
    views_P: np.ndarray,
    views_Q: np.ndarray,
    views_omega: np.ndarray | None = None,
    tau: float = 0.05,
) -> tuple[pd.Series, pd.DataFrame]:
    """
    计算 Black-Litterman 后验收益和协方差。

    参数:
        prior_returns: 先验均衡收益 π (N,)
        covariance: 年化协方差矩阵 Σ (N×N)
        views_P: 观点选择矩阵 (K×N)，每行一个观点
        views_Q: 观点收益向量 (K,)，每个观点的超额收益
        views_omega: 观点不确定性对角矩阵 (K×K)，None 时自动估计
        tau: 先验不确定性缩放参数

    返回:
        posterior_returns: 后验预期收益 (N,)
        posterior_cov: 后验协方差矩阵 (N×N)

    公式:
        μ_post = [(τΣ)⁻¹ + P^T Ω⁻¹ P]⁻¹ × [(τΣ)⁻¹·π + P^T Ω⁻¹·Q]
        Σ_post = Σ + [(τΣ)⁻¹ + P^T Ω⁻¹ P]⁻¹
    """
    tickers = covariance.columns.tolist()
    n = len(tickers)

    if views_omega is None:
        # 自动估计 Ω = diag(P Σ P^T) × tau
        P_cov_Pt = views_P @ covariance.values @ views_P.T
        views_omega = np.diag(np.diag(P_cov_Pt)) * tau

    tau_sigma = tau * covariance.values
    tau_sigma_inv = np.linalg.inv(tau_sigma)
    omega_inv = np.linalg.inv(views_omega)

    # 后验收益
    middle_term = tau_sigma_inv + views_P.T @ omega_inv @ views_P
    M = np.linalg.inv(middle_term)
    posterior_mu = M @ (tau_sigma_inv @ prior_returns.values + views_P.T @ omega_inv @ views_Q)

    # 后验协方差
    posterior_cov_values = covariance.values + M

    posterior_returns = pd.Series(posterior_mu, index=tickers, name="bl_posterior")
    posterior_cov = pd.DataFrame(posterior_cov_values, index=tickers, columns=tickers)

    return posterior_returns, posterior_cov


def rules_to_bl_views(
    rules: pd.DataFrame,
    tickers: list[str],
    default_confidence: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """
    将 human_overrides.csv 中的 boost/penalize 规则转换为 BL 观点矩阵。

    参数:
        rules: 人工规则 DataFrame
        tickers: 完整股票列表
        default_confidence: boost/penalize 规则的默认置信度

    返回:
        (P, Q, Ω) 或 None（如果没有 boost/penalize 规则）
    """
    if rules.empty:
        return None

    # 只处理 boost/penalize
    views = rules[
        rules["action"].isin(["boost", "penalize"])
    ].copy()

    if views.empty:
        return None

    n = len(tickers)
    ticker_to_idx = {t: i for i, t in enumerate(tickers)}

    k = 0
    valid_views = []
    for _, rule in views.iterrows():
        ticker = rule["ticker"]
        if ticker not in ticker_to_idx:
            continue
        valid_views.append(rule)
        k += 1

    if k == 0:
        return None

    P = np.zeros((k, n))
    Q = np.zeros(k)
    omega_diag = np.zeros(k)

    for i, rule in enumerate(valid_views):
        idx = ticker_to_idx[rule["ticker"]]
        direction = 1.0 if rule["action"] == "boost" else -1.0

        # P: 绝对观点（该股票自身的超额收益）
        P[i, idx] = 1.0

        # Q: 观点幅度
        multiplier = float(rule.get("return_multiplier", 1.0))
        if pd.isna(multiplier):
            multiplier = 1.0
        # 将乘数转换为年化超额收益（粗略映射）
        excess = (multiplier - 1.0) * 0.10
        Q[i] = direction * max(abs(excess), 0.01)

        # Ω: 基于置信度的不确定性
        confidence = float(rule.get("bl_confidence", default_confidence))
        if pd.isna(confidence):
            confidence = default_confidence
        confidence = max(0.1, min(0.99, confidence))
        omega_diag[i] = (1.0 - confidence) * 0.01

    omega = np.diag(omega_diag)
    return P, Q, omega
