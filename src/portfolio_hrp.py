"""层次风险平价 (Hierarchical Risk Parity)。

Lopez de Prado (2016) 方法：通过层次聚类识别资产子群结构，
在群内和群间递归分配风险，完全规避马科维茨协方差矩阵求逆的数值不稳定性。

适用于高相关性资产池（如纯科技股板块）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform


def correl_dist(corr: pd.DataFrame) -> np.ndarray:
    """相关系数矩阵 → 距离矩阵。d = sqrt(0.5 * (1 - ρ))"""
    return np.sqrt(0.5 * (1.0 - corr.values))


def _cluster_variance(cov: pd.DataFrame, weights: pd.Series, items: list[str]) -> float:
    """计算某个资产集合在给定权重下的组合方差。"""
    w_sub = weights[items].values
    cov_sub = cov.loc[items, items].values
    return float(w_sub @ cov_sub @ w_sub)


def hrp_weights(returns: pd.DataFrame, linkage_method: str = "ward") -> pd.Series:
    """
    层次风险平价权重。

    参数:
        returns: (T, N) 日收益 DataFrame，列为 ticker
        linkage_method: scipy linkage method，默认 ward

    返回:
        weights: (N,) 权重 Series，和为 1
    """
    cov = returns.cov()
    corr = returns.corr()
    dist = correl_dist(corr)

    # 层次聚类
    condensed = squareform(dist)
    clusters = linkage(condensed, method=linkage_method)

    n = len(returns.columns)
    tickers = list(returns.columns)
    w = pd.Series(1.0, index=tickers)

    # cluster_items 追踪每次合并后的资产集合
    cluster_items: dict[int, list[str]] = {i: [tickers[i]] for i in range(n)}

    for i, merge in enumerate(clusters):
        left_idx, right_idx = int(merge[0]), int(merge[1])
        left_items = cluster_items[left_idx]
        right_items = cluster_items[right_idx]
        merged_items = left_items + right_items

        # 计算两群方差 → 按逆方差比分配风险
        left_var = _cluster_variance(cov, w, left_items)
        right_var = _cluster_variance(cov, w, right_items)
        total_var = left_var + right_var

        if total_var > 0:
            alpha = left_var / total_var
        else:
            alpha = 0.5

        # 群内标度
        for ticker in left_items:
            w[ticker] *= alpha
        for ticker in right_items:
            w[ticker] *= (1.0 - alpha)

        cluster_items[n + i] = merged_items

    result = w / w.sum()
    result.name = "hrp"
    return result


def hrp_cluster_labels(returns: pd.DataFrame, n_clusters: int = 5, linkage_method: str = "ward") -> pd.Series:
    """
    返回每只股票所属的聚类标签（用于前端展示树状图分组）。

    返回:
        labels: (N,) Series，index=ticker，值为 0..n_clusters-1
    """
    from scipy.cluster.hierarchy import fcluster

    corr = returns.corr()
    dist = correl_dist(corr)
    condensed = squareform(dist)
    clusters = linkage(condensed, method=linkage_method)
    labels = fcluster(clusters, n_clusters, criterion="maxclust")
    return pd.Series(labels, index=returns.columns, name="cluster")


def effective_n(weights: pd.Series) -> float:
    """有效持仓数 = 1 / Σw² (HHI 倒数)。越大表示权重越分散。"""
    return float(1.0 / (weights ** 2).sum())


def weight_concentration(weights: pd.Series, top_n: int = 5) -> dict[str, float]:
    """权重集中度指标。"""
    sorted_w = weights.sort_values(ascending=False)
    return {
        "top5_share": float(sorted_w.head(5).sum()),
        "top10_share": float(sorted_w.head(10).sum()),
        "effective_n": effective_n(weights),
        "hhi": float((weights ** 2).sum()),
    }
