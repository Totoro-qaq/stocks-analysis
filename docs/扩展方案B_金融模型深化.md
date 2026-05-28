# 扩展方案 B：金融模型深化 — HRP + 协方差收缩 + CVaR + Black-Litterman + Fama-French

> **目标**：在现有 50 股科技股分析管线的基础上，补充更稳健的组合优化方法和因子归因框架，解决当前"马科维茨对高相关科技股不稳定"的核心问题。
> **原则**：每一步都独立可用，做完一步就能在 walk-forward 里和现有方法对比。所有新增指标同步写入前端展示。

---

## 一、现状诊断

### 1.1 数据特征

```
N = 50 支科技股（单一板块，内在相关性极高）
T ≈ 1500 个交易日（2020-01 至今，含 COVID + AI 周期）
行业集中：半导体、软件、硬件、互联网服务
```

### 1.2 当前方法弱点

| 组件 | 当前做法 | 问题 |
|------|----------|------|
| 协方差估计 | 样本协方差 / Ledoit-Wolf → 单位矩阵收缩 | Ledoit-Wolf 的收缩目标假设所有股票独立，对单板块高相关场景不合适 |
| 收益预测 | `returns.mean() * 252` 纯历史均值 | 估计误差大，是马科维茨 max_sharpe 不稳定的根本原因 |
| 优化目标 | `min_variance` / `max_sharpe` | max_sharpe 对收益估计极度敏感；min_variance 只用协方差但忽略了尾部风险 |
| 人工规则 | `return_multiplier` 粗暴乘数 | 没有贝叶斯框架，不确定性的量化缺失 |
| 因子分析 | PCA 主成分 | PC1/PC2 缺乏经济学解释，无法做因子归因 |

### 1.3 优化路线图

```
现状                           第1步                 第2步                   第3步                   第4步               第5步
────                           ────                  ────                    ────                    ────                ────
等权 + 马科维茨          →    + HRP            →    + 单因子收缩协方差    →    + CVaR 优化        →    + Black-Litterman  →  + Fama-French
(min_var / max_sharpe)      (层次风险平价)        (factor shrinkage)         (min_cvar)              (贝叶斯观点融合)       (因子归因)

Walk-forward 对比 →        夏普衰减改善 ✓         协方差更稳定 ✓           尾部风险控制 ✓          人工规则更科学 ✓        超额收益来源清晰 ✓
```

---

## 二、第 1 步：HRP（层次风险平价）

### 2.1 为什么优先做 HRP

马科维茨对高相关资产求逆协方差矩阵时数值不稳定，权重容易极端集中在少数股票。HRP 完全规避矩阵求逆，只用聚类 + 递归分配：

```
1. 计算相关系数矩阵 → 距离矩阵
2. 层次聚类（Ward / single linkage）→ 树状图
3. 自底向上：群内等风险分配 → 群间按风险贡献分配
```

对 50 支科技股（半导体 vs 软件 vs 硬件天然分组），HRP 能自动识别子群结构，在群内群间都分散风险。

### 2.2 新增文件

```
src/portfolio_hrp.py
```

### 2.3 核心实现

```python
# src/portfolio_hrp.py

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform

def correl_dist(corr: pd.DataFrame) -> np.ndarray:
    """相关系数 → 距离矩阵。d = sqrt(0.5 * (1 - ρ))"""
    return ((1 - corr) / 2.0) ** 0.5

def hrp_weights(returns: pd.DataFrame, linkage_method: str = "ward") -> pd.Series:
    """
    层次风险平价权重。
    
    参数:
        returns: (T, N) 日收益 DataFrame
        linkage_method: scipy linkage method
    
    返回:
        weights: (N,) 权重 Series，和为 1
    """
    cov = returns.cov()
    corr = returns.corr()
    dist = correl_dist(corr)
    
    # 层次聚类
    condensed = squareform(dist.values)
    clusters = linkage(condensed, method=linkage_method)
    
    # 递归分配权重
    n = len(returns.columns)
    tickers = returns.columns.tolist()
    w = pd.Series(1.0, index=tickers)
    
    # cluster_items 追踪每次合并后的资产集合
    cluster_items = {i: [tickers[i]] for i in range(n)}
    
    for i, merge in enumerate(clusters):
        left_idx, right_idx = int(merge[0]), int(merge[1])
        left_items = cluster_items[left_idx]
        right_items = cluster_items[right_idx]
        merged_items = left_items + right_items
        
        # 计算群内方差
        left_var = _cluster_variance(cov, w, left_items)
        right_var = _cluster_variance(cov, w, right_items)
        total_var = left_var + right_var
        alpha = left_var / total_var if total_var > 0 else 0.5
        
        # 按方差逆比分配
        for ticker in left_items:
            w[ticker] *= alpha
        for ticker in right_items:
            w[ticker] *= (1 - alpha)
        
        cluster_items[n + i] = merged_items
    
    return w / w.sum()


def _cluster_variance(cov: pd.DataFrame, weights: pd.Series, items: list) -> float:
    """群内方差：w_sub^T * cov_sub * w_sub"""
    w_sub = weights[items]
    cov_sub = cov.loc[items, items]
    return float(w_sub.values @ cov_sub.values @ w_sub.values)
```

### 2.4 集成到现有管线

在 `portfolio_optimization.py` 的 `main()` 中加一个权重项：

```python
# 在现有 weights dict 中追加
from portfolio_hrp import hrp_weights

weights["hrp"] = pd.Series(
    hrp_weights(stock_returns),
    index=tickers,
    name="hrp"
)
```

在 `walk_forward.py` 的 `build_window_weights()` 中同样追加：

```python
weights["hrp"] = pd.Series(
    hrp_weights(train_returns[tickers]),
    index=tickers,
    name="hrp"
)
```

### 2.5 与现有方法的对比维度

在 walk-forward 汇总中加入 `hrp` 行，对比：

- 平均测试期夏普比率
- 夏普衰减（train → test）
- 最大回撤
- 权重集中度（HHI / 有效持仓数）
- 换手率（窗口间权重变化）

### 2.6 前端展示

| 新增内容 | 位置 | 说明 |
|----------|------|------|
| HRP 权重柱状图 | 组合优化页 | 与 equal_weight / min_variance / max_sharpe 并列 |
| 权重集中度对比卡片 | 组合优化页 | HHI、有效持仓数 `1/Σw²` |
| Walk-forward HRP 行 | 前向验证页 | 训练/测试夏普、衰减、胜率 |
| 聚类树状图 | 组合优化页（新） | `scipy.cluster.hierarchy.dendrogram` 可视化，展示 50 股的层次分组结构 |

---

## 三、第 2 步：单因子收缩协方差

### 3.1 为什么改进协方差

现有 Ledoit-Wolf 向单位矩阵收缩，隐含假设"所有股票独立 + 同方差"——对科技股板块不合理。单因子模型认为：

```
Σ_shrink = (1 - δ) * Σ_sample + δ * Σ_factor
```

其中 `Σ_factor` 来自市场模型（所有股票收益 = α + β × 市场因子 + ε），比向单位矩阵收缩更符合板块集中的数据结构。

### 3.2 新增代码位置

在 `portfolio_optimization.py` 中加一个 `covariance_method` 选项：

```python
# portfolio_optimization.py 中新增

def annualized_covariance_factor_shrinkage(returns: pd.DataFrame) -> pd.DataFrame:
    """
    向单因子模型收缩的协方差估计。
    
    步骤:
    1. 用等权组合收益作为板块因子代理
    2. 每只股票回归: r_i = α_i + β_i * r_factor + ε_i
    3. Σ_factor = ββ^T * σ²_factor + diag(σ²_ε)
    4. 用 Ledoit-Wolf 框架计算最优收缩强度 δ
    5. Σ_shrink = (1 - δ) * Σ_sample + δ * Σ_factor
    """
    clean = returns.dropna(how="any")
    # 板块因子：等权收益
    factor = clean.mean(axis=1)
    factor_var = factor.var()
    
    # 估计每只股票的 β
    betas = {}
    residuals_var = {}
    for ticker in clean.columns:
        stock = clean[ticker]
        beta = stock.cov(factor) / factor_var
        betas[ticker] = beta
        residuals_var[ticker] = (stock - beta * factor).var()
    
    beta_vec = pd.Series(betas)
    sigma_residual = pd.Series(residuals_var)
    
    # 因子模型隐含的协方差
    beta_matrix = np.outer(beta_vec.values, beta_vec.values)
    factor_cov = beta_matrix * factor_var
    np.fill_diagonal(factor_cov, factor_cov.diagonal() + sigma_residual.values)
    cov_factor = pd.DataFrame(factor_cov, index=clean.columns, columns=clean.columns)
    
    # Ledoit-Wolf 风格收缩强度（简化版）
    sample_cov = clean.cov().values
    # 用 OAS 近似最优收缩强度
    shrinkage = _oas_shrinkage_intensity(clean)
    
    shrunk = (1 - shrinkage) * sample_cov + shrinkage * factor_cov.values
    return pd.DataFrame(shrunk, index=clean.columns, columns=clean.columns) * TRADING_DAYS
```

### 3.3 验证方式

运行同一组 walk-forward，三个协方差方法对比：

```
COVARIANCE_METHODS = ("sample", "ledoit_wolf", "factor_shrinkage")
```

观测指标：各方法下 max_sharpe 组合的夏普衰减（train_sharpe - test_sharpe）是否递减。

### 3.4 前端展示

| 新增内容 | 位置 | 说明 |
|----------|------|------|
| 协方差方法选择器 | 组合优化页 | 下拉：sample / ledoit_wolf / factor_shrinkage |
| 收缩强度指标 | 组合优化指标表 | `shrinkage_intensity` 列 |
| 协方差矩阵热力图对比 | 相关性页（新 tab） | 三种方法的协方差矩阵并排展示 |

---

## 四、第 3 步：CVaR 优化

### 4.1 为什么加 CVaR

科技股尾部风险高（2022 年 NASDAQ 跌 33%）。方差惩罚对称分布，对左尾不敏感。CVaR 直接最小化最差 α% 情景的平均损失。

你的 `analysis_engine.py` 里已经算好了 `var_95_daily` 和 `cvar_95_daily`，但优化没用它们。

### 4.2 新增代码位置

在 `portfolio_optimization.py` 中加 `objective="min_cvar"`：

```python
def optimize_portfolio_cvar(
    returns: pd.DataFrame,
    alpha: float = 0.05,
    max_weight: float = 0.10,
) -> pd.Series:
    """
    最小 CVaR 组合优化。
    
    Rockafellar & Uryasev (2000) 线性规划形式：
    
    min  γ + 1/(α·T) * Σ max(-w·r_t - γ, 0)
    s.t. Σw = 1, 0 ≤ w_i ≤ max_weight
    """
    from scipy.optimize import minimize
    
    T, N = returns.shape
    ret_matrix = returns.values
    tickers = returns.columns.tolist()
    
    # 决策变量：[w_1, ..., w_N, γ, z_1, ..., z_T]
    # z_t ≥ -w·r_t - γ, z_t ≥ 0
    n_vars = N + 1 + T
    
    def objective(x):
        w = x[:N]
        gamma = x[N]
        z = x[N+1:]
        return gamma + (1.0 / (alpha * T)) * np.sum(z)
    
    def constraint_sum(x):
        return np.sum(x[:N]) - 1.0
    
    # z_t ≥ -w·r_t - γ  →  z_t + w·r_t + γ ≥ 0
    constraints = [{'type': 'eq', 'fun': constraint_sum}]
    
    # 非线性约束在 minimize 中效率低，这里用简化版：
    # 直接在目标中嵌入 z_t = max(-w·r_t - γ, 0)
    def objective_compact(x):
        w = x[:N]
        gamma = x[N]
        portfolio_returns = ret_matrix @ w
        losses = -portfolio_returns - gamma
        z = np.maximum(losses, 0)
        return gamma + (1.0 / (alpha * T)) * np.sum(z)
    
    bounds = [(0.0, max_weight)] * N + [(None, None)]  # γ unbounded
    x0 = np.array([1.0/N] * N + [0.0])
    
    result = minimize(
        objective_compact,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-10},
    )
    
    if not result.success:
        raise RuntimeError(f"CVaR optimization failed: {result.message}")
    return pd.Series(result.x[:N], index=tickers, name="min_cvar")
```

### 4.3 验证指标

在 walk-forward 中加入 `min_cvar` 组合，观测：

- 最大回撤（应该更低）
- 最差窗口收益（应该更好）
- 实际 CVaR vs 方差优化组合的 CVaR

### 4.4 前端展示

| 新增内容 | 位置 | 说明 |
|----------|------|------|
| CVaR 优化组合权重 | 组合优化页 | 与等权/最小方差/最大夏普/HRP 并列 |
| α 参数滑块 | 组合优化页 | 选择 CVaR 置信水平（1%/5%/10%） |
| VaR / CVaR 对比卡片 | 组合指标表 | 各组合的历史 VaR 和 CVaR |
| 收益分布直方图 | 组合优化页（新） | 展示左尾，标注各组合的 VaR/CVaR 阈值 |

---

## 五、第 4 步：Black-Litterman 观点融合

### 5.1 改造动机

当前 `rules_engine.py` 的 `boost`/`penalize` 是粗暴乘数：

```
当前: adjusted_mean_return = mean_return * 1.2  ← "我觉得 AAPL 要涨 20%"
```

Black-Litterman 把这一提升级为贝叶斯框架：

```
BL 后验收益 = [(τΣ)^-1 + P^T Ω^-1 P]^-1 × [(τΣ)^-1·π + P^T Ω^-1·Q]

其中:
  π = 市场均衡隐含收益（隐含在市值权重中）
  P = 观点选择矩阵（哪些股票有观点）
  Q = 观点收益向量（超额收益多少）
  Ω = 观点不确定性（你对观点有多自信）
  τ = 先验不确定性缩放
```

你的 `human_overrides.csv` 中 `boost`/`penalize` + `reason` 字段天然映射为 (P, Q, Ω)。

### 5.2 新增文件

```
src/black_litterman.py
```

### 5.3 规则文件格式扩展

在 `human_overrides.csv` 中新增列：

```csv
ticker,action,...,bl_confidence
NVDA,boost,...,0.3     ← 对 NVDA 会跑赢市场 10% 的观点只有 30% 确定
INTC,penalize,...,0.7  ← 对 INTC 会跑输 5% 的观点有 70% 确定
```

### 5.4 核心实现框架

```python
# src/black_litterman.py

import numpy as np
import pandas as pd

def implied_equilibrium_returns(
    market_weights: pd.Series,  # 市值权重（可从 XLK 权重获取）
    covariance: pd.DataFrame,
    risk_aversion: float = 2.5,
) -> pd.Series:
    """
    π = λ × Σ × w_mkt
    
    从市值权重反向推出市场隐含均衡收益。
    这是 BL 的先验。
    """
    return risk_aversion * covariance @ market_weights


def black_litterman_posterior(
    prior_returns: pd.Series,      # π: 隐含均衡收益
    covariance: pd.DataFrame,      # Σ: 协方差矩阵
    views_P: np.ndarray,           # P: K×N 观点选择矩阵
    views_Q: np.ndarray,           # Q: K 观点收益向量
    views_omega: np.ndarray,       # Ω: K×K 观点不确定性（对角=置信度倒数）
    tau: float = 0.05,             # 先验缩放参数
) -> tuple[pd.Series, pd.DataFrame]:
    """
    计算 Black-Litterman 后验收益和协方差。
    
    返回:
        posterior_returns: 后验预期收益
        posterior_cov: 后验协方差
    """
    tau_sigma_inv = np.linalg.inv(tau * covariance.values)
    omega_inv = np.linalg.inv(views_omega)
    
    # 后验收益
    M = np.linalg.inv(tau_sigma_inv + views_P.T @ omega_inv @ views_P)
    posterior_mu = M @ (tau_sigma_inv @ prior_returns.values + views_P.T @ omega_inv @ views_Q)
    
    # 后验协方差
    posterior_cov = covariance.values + M
    
    posterior_returns = pd.Series(posterior_mu, index=covariance.index)
    posterior_cov_df = pd.DataFrame(posterior_cov, index=covariance.index, columns=covariance.columns)
    
    return posterior_returns, posterior_cov_df


def rules_to_bl_views(
    rules: pd.DataFrame,
    tickers: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    将 human_overrides.csv 中的 boost/penalize 规则
    转换为 BL 观点矩阵 (P, Q, Ω)。
    
    boost  → 观点: 该股票跑赢等权组合 X%
    penalize → 观点: 该股票跑输等权组合 X%
    
    confidence 列映射到 Ω 对角线（高置信 = 小方差）
    """
    n = len(tickers)
    ticker_to_idx = {t: i for i, t in enumerate(tickers)}
    
    views = rules[
        (rules["action"].isin(["boost", "penalize"]))
    ]
    
    k = len(views)
    P = np.zeros((k, n))
    Q = np.zeros(k)
    omega_diag = np.zeros(k)
    
    for i, (_, rule) in enumerate(views.iterrows()):
        idx = ticker_to_idx[rule["ticker"]]
        direction = 1 if rule["action"] == "boost" else -1
        
        # P: 绝对观点（该股票自身）
        P[i, idx] = 1.0
        
        # Q: 观点幅度（从 return_multiplier 推算）
        excess = (rule.get("return_multiplier", 1.0) - 1.0)
        Q[i] = direction * abs(excess) * 0.10  # 默认超额 10% 映射
        
        # Ω: 从置信度转换
        confidence = rule.get("bl_confidence", 0.5)
        omega_diag[i] = (1.0 - confidence) * 0.01  # 低置信 = 高不确定性
    
    omega = np.diag(omega_diag)
    return P, Q, omega
```

### 5.5 集成方式

在 `portfolio_optimization.py` 的 `optimize_portfolio()` 中：

```python
if use_black_litterman and rules is not None:
    # 用市值权重（XLK weight）作为先验
    market_weights = _market_weights_from_holdings(tickers)
    prior = implied_equilibrium_returns(market_weights, covariance, risk_aversion=2.5)
    P, Q, omega = rules_to_bl_views(rules, tickers)
    
    posterior_mu, posterior_cov = black_litterman_posterior(
        prior, covariance, P, Q, omega
    )
    mean_returns = posterior_mu
    covariance = posterior_cov
else:
    mean_returns = adjusted_mean_returns(mean_returns, rule_set)
    covariance = adjusted_covariance(covariance, rule_set)
```

### 5.6 前端展示

| 新增内容 | 位置 | 说明 |
|----------|------|------|
| BL 置信度滑块 | 人工规则页 | 每条 boost/penalize 规则加 `bl_confidence` 控件 |
| 先验 vs 后验收益对比 | 组合优化页（新 tab） | 散点图：x=先验收益, y=后验收益, 标注被 boost/penalize 的股票 |
| BL 选项开关 | 组合优化参数区 | `use_black_litterman=true/false` |

---

## 六、第 5 步：Fama-French 因子归因

### 6.1 为什么加因子回归

你的 PCA（`factor_analysis.py`）告诉你 PC1 解释了 38% 方差——但 PC1 是什么？市场因子？科技板块因子？无法解释。

Fama-French 五因子回归给每个 PC 赋予经济学含义：

```
r_i - r_f = α_i + β_mkt·(r_m - r_f) + β_smb·SMB + β_hml·HML + β_rmw·RMW + β_cma·CMA + ε_i
```

对你这种科技大盘股，典型结果会是 α 不显著、β_mkt 接近 1——**这本身就是有价值的结论**：说明超额收益几乎全部来自市场暴露，选股 alpha 空间小。

### 6.2 数据来源

Kenneth French Data Library 提供免费 CSV：
- Fama-French 3 Factors (daily): `F-F_Research_Data_Factors_daily.csv`
- Fama-French 5 Factors (daily): `F-F_Research_Data_5_Factors_2x3_daily.csv`
- Momentum Factor: `F-F_Momentum_Factor_daily.csv`

URL 格式：
```
https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_daily_CSV.zip
```

### 6.3 新增文件

```
src/factor_regression.py
```

### 6.4 核心实现

```python
# src/factor_regression.py

import numpy as np
import pandas as pd
import statsmodels.api as sm

def load_ff_factors(path: str) -> pd.DataFrame:
    """加载 Fama-French 五因子 + 动量因子（日频，%）"""
    raw = pd.read_csv(path, skiprows=3)
    # Kenneth French CSV 格式: 第一列日期(YYYYMMDD), 其余为因子
    raw = raw.rename(columns={raw.columns[0]: "date"})
    raw["date"] = pd.to_datetime(raw["date"].astype(str), format="%Y%m%d")
    raw = raw.set_index("date")
    # 转换为小数
    return raw / 100.0


def factor_regression(
    stock_returns: pd.Series,
    factors: pd.DataFrame,
    rf: pd.Series | None = None,
) -> dict:
    """
    对单只股票做 Fama-French 因子回归。
    
    返回:
        {
            "alpha_annualized": ...,
            "alpha_pvalue": ...,
            "betas": { "Mkt-RF": ..., "SMB": ..., "HML": ..., "RMW": ..., "CMA": ... },
            "r_squared": ...,
            "adj_r_squared": ...,
        }
    """
    aligned = pd.concat([stock_returns, factors], axis=1).dropna()
    if aligned.empty:
        return {}
    
    y = aligned.iloc[:, 0]
    X = aligned.iloc[:, 1:]
    X = sm.add_constant(X)
    
    model = sm.OLS(y, X).fit()
    
    return {
        "alpha_annualized": model.params["const"] * 252,
        "alpha_t_stat": model.tvalues["const"],
        "alpha_pvalue": model.pvalues["const"],
        "betas": {col: model.params[col] for col in factors.columns},
        "r_squared": model.rsquared,
        "adj_r_squared": model.rsquared_adj,
    }


def portfolio_factor_attribution(
    portfolio_returns: pd.Series,
    factors: pd.DataFrame,
) -> dict:
    """对组合收益做因子归因，拆解超额收益来源。"""
    aligned = pd.concat([portfolio_returns, factors], axis=1).dropna()
    y = aligned.iloc[:, 0]
    X = sm.add_constant(aligned.iloc[:, 1:])
    model = sm.OLS(y, X).fit()
    
    # 归因分解
    total_return = y.mean() * 252
    factor_contributions = {}
    for col in factors.columns:
        factor_contributions[col] = model.params[col] * factors[col].mean() * 252
    
    alpha_contribution = model.params["const"] * 252
    unexplained = total_return - alpha_contribution - sum(factor_contributions.values())
    
    return {
        "total_annualized_return": total_return,
        "alpha_contribution": alpha_contribution,
        "factor_contributions": factor_contributions,
        "unexplained": unexplained,
        "r_squared": model.rsquared,
    }
```

### 6.5 输出文件

```
data/output/
├── factor_regression_single_stock.csv     # 每只股票的 α、β 暴露、R²
├── factor_regression_portfolio.csv        # 各组合的因子归因
└── factor_returns.csv                     # 日频因子收益序列
```

### 6.6 前端展示

| 新增内容 | 位置 | 说明 |
|----------|------|------|
| α 显著性格子图 | 前端验证页（新 tab "因子归因"） | 50 只股票的 α 及 p 值气泡图 |
| 因子暴露条形图 | 因子归因页 | 每只股票在 5 因子上的 β 暴露 |
| 组合收益归因瀑布图 | 因子归因页 | 总收益 → 市场/规模/价值/盈利/投资/α 分解 |
| R² 直方图 | 因子归因页 | 展示因子模型对 50 只科技股的解释力分布 |

---

## 七、与方案 A（前后端）的衔接

方案 A 的 API 和前端天然兼容方案 B 的新模块：

```
方案 B 新增模块                       方案 A 对应路由
──────────────                       ──────────────
portfolio_hrp.py          →          GET /api/portfolio/hrp-weights
                                      POST /api/portfolio/optimize?method=hrp

factor_shrinkage          →          POST /api/portfolio/optimize?covariance=factor_shrinkage

cvar_optimization         →          POST /api/portfolio/optimize?objective=min_cvar

black_litterman.py        →          POST /api/portfolio/black-litterman

factor_regression.py      →          GET /api/factor/ff-regression
                                      GET /api/factor/attribution
```

所有新增指标自动出现在前端的对应页面和数据表中。

---

## 八、工期估算

| 步骤 | 内容 | 工时 | 依赖 |
|------|------|------|------|
| Step 1 | HRP 实现 + 集成 + 前端 | 2 天 | 无 |
| Step 2 | 单因子收缩协方差 | 1 天 | 无 |
| Step 3 | CVaR 优化 | 1.5 天 | 无 |
| Step 4 | Black-Litterman 观点融合 | 2.5 天 | Step 1（HRP 的协方差可用） |
| Step 5 | Fama-French 因子归因 | 1.5 天 | 无（需下载因子数据） |
| **合计** | | **8.5 天** | |

---

## 九、预期对比验证

所有新方法统一在 walk-forward 框架下与基线对比：

| 指标 | 等权（基线） | 马科维茨 max_sharpe | HRP | CVaR | BL |
|------|-------------|-------------------|-----|------|-----|
| avg_test_sharpe | ? | ? | ? | ? | ? |
| avg_sharpe_decay | 0 | 高 | 低 | 中 | 中 |
| worst_max_drawdown | ? | ? | ? | 最低 | ? |
| 权重 HHI（集中度） | 0.02 | 0.15+ | 0.04-0.06 | 0.05 | ? |
| avg_turnover | 低 | 高 | 中 | 中 | 中 |
| win_rate_vs_XLK | ? | ? | ? | ? | ? |

> 每个 `?` 都是待观测的实证结果——这就是练手的核心乐趣。
