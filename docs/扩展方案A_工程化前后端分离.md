# 扩展方案 A：工程化 — 前后端分离 + 容器化

> **目标**：把当前 CLI 脚本 + Streamlit 的架构升级为 FastAPI 后端 + React 前端 + Docker 容器化部署的标准化量化服务。
> **核心原则**：现有 `src/` 下所有计算模块不动，只外围包装 API 层。所有现有图表、指标、参数完整保留到前端。

---

## 一、现状资产盘点

### 1.1 现有计算模块（不动）

| 模块 | 文件 | 功能 |
|------|------|------|
| 数据抓取 | `fetch_market_data.py` | Yahoo Finance → CSV + MySQL |
| 股票池构建 | `build_universe_50.py` | XLK 持仓 → 50 股筛选 |
| 基础分析 | `analysis_engine.py` | 单股指标、等权组合、相关性、布林带 |
| 组合优化 | `portfolio_optimization.py` | 马科维茨最小方差/最大夏普、有效前沿、Ledoit-Wolf |
| 前向验证 | `walk_forward.py` | 滚动窗口训练/测试 |
| 统计检验 | `stat_tests.py` | t 检验、block bootstrap |
| 因子分析 | `factor_analysis.py` | PCA 主成分分解 |
| 规则引擎 | `rules_engine.py` | 人工 override 规则 |
| 报告生成 | `llm_report.py` | DeepSeek LangChain 流式报告 |
| Dify 对接 | `dify_client.py` | Dify Workflow A/B |

### 1.2 现有图表和展示（需完整迁移到前端）

| 页面 | 图表 | 数据来源 |
|------|------|----------|
| 数据总览 | 股票池表格、抓取失败记录 | `analysis_universe_50.csv`, `daily_prices.csv`, `data_fetch_failures.csv` |
| 市场基准 | 累计收益曲线（多组合 vs 基准）、VIX 走势 | `cumulative_returns.csv`, `daily_prices.csv` |
| 单股分析 | 指标卡片（年化收益/波动率/夏普/最大回撤）、布林带图、指标表格 | `single_stock_metrics.csv`, `bollinger_bands.csv` |
| 组合优化 | 优化指标表、累计收益曲线、回撤曲线、权重柱状图、有效前沿散点图 | `optimized_portfolio_metrics.csv`, `optimized_portfolio_returns.csv`, `optimized_portfolio_cumulative_returns.csv`, `portfolio_weights.csv`, `efficient_frontier.csv` |
| 相关性 | 50 股相关性热力图 | `correlation_matrix.csv` |
| 前向验证 | 样本外汇总表、训练/测试夏普对比柱状图、各窗口夏普折线图 | `walk_forward_summary.csv`, `walk_forward_window_metrics.csv` |
| 统计检验 | t 检验表、bootstrap 区间表 | `significance_tests.csv`, `bootstrap_intervals.csv` |
| 人工规则 | 规则编辑区、生效规则表、Dify Workflow B 集成 | `human_overrides.csv`, `active_human_overrides.csv` |
| 智能报告 | Markdown 渲染、流式生成 | `investment_report.md` |

### 1.3 现有参数（需保留交互控件）

| 参数 | 当前位置 | 控件类型 |
|------|----------|----------|
| 股票选择 | 单股分析页 | `st.selectbox` |
| 权重组合选择 | 组合优化页 | `st.selectbox` |
| 报告重点 focus | 智能报告页 | `st.selectbox` |
| 报告生成引擎 | 智能报告页 | `st.radio` |
| 人工研究备注 | 智能报告页 | `st.text_area` |
| 规则编辑 | 人工规则页 | `st.text_area` |
| Dify 自然语言输入 | 人工规则页 | `st.text_area` |
| 开始/结束日期 | 人工规则页 | `st.text_input` |
| 一键全流程 | 侧边栏 | `st.button` |
| 分步执行按钮 | 侧边栏 | `st.button` |

---

## 二、目标架构

```
┌─────────────────────────────────────────────────────────┐
│                     Docker Compose                       │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │  React   │  │ FastAPI  │  │  MySQL   │  │  Redis   │ │
│  │  :5173   │→│  :8000   │→│  :3306   │  │  :6379   │ │
│  │  Nginx   │  │  Celery  │  │          │  │ (缓存)   │ │
│  │  静态服务│  │  Worker  │  └──────────┘  └─────────┘ │
│  └──────────┘  └──────────┘                              │
│                                                          │
│  src/ 计算模块（原封不动）────↑                           │
│  portfolio_optimization.py                               │
│  analysis_engine.py                                      │
│  factor_analysis.py                                      │
│  walk_forward.py                                         │
│  stat_tests.py                                           │
│  rules_engine.py                                         │
│  llm_report.py                                           │
│  dify_client.py                                          │
└─────────────────────────────────────────────────────────┘
```

---

##三、分步施工

### Step 1：FastAPI 后端骨架

**文件**：`backend/` 目录

```
backend/
├── main.py                  # FastAPI app, CORS, lifespan
├── routers/
│   ├── analysis.py          # 基础分析路由
│   ├── portfolio.py         # 组合优化路由
│   ├── validation.py        # Walk-forward + 统计检验路由
│   ├── factor.py            # PCA 因子分析路由
│   ├── rules.py             # 人工规则 CRUD
│   ├── report.py            # DeepSeek + Dify 报告
│   └── data.py              # 数据总览 / 市场行情
├── schemas/                 # Pydantic 请求/响应模型
│   ├── analysis.py
│   ├── portfolio.py
│   └── common.py
├── services/                # 封装 src/ 模块调用
│   ├── analysis_service.py
│   ├── portfolio_service.py
│   └── report_service.py
├── tasks/                   # Celery 异步任务
│   └── pipeline.py          # 一键全流程
└── tests/
```

**核心 API 路由设计**：

```
GET    /api/health                         健康检查

# 数据总览
GET    /api/data/overview                  股票池概况（数量、日期范围）
GET    /api/data/universe                  50 股列表
GET    /api/data/market?ticker=AAPL        单股行情

# 基础分析
POST   /api/analysis/run                   触发基础分析计算
GET    /api/analysis/single-stock-metrics  单股指标表格
GET    /api/analysis/portfolio-metrics     等权组合指标
GET    /api/analysis/correlation           相关性矩阵
GET    /api/analysis/cumulative-returns    累计收益序列
GET    /api/analysis/bollinger?ticker=AAPL 布林带

# 组合优化
POST   /api/portfolio/optimize             触发优化（参数：objective, covariance_method, max_weight, rules）
GET    /api/portfolio/weights              组合权重
GET    /api/portfolio/metrics              优化组合指标
GET    /api/portfolio/efficient-frontier   有效前沿数据
GET    /api/portfolio/returns              优化组合收益序列

# Walk-forward
POST   /api/validation/walk-forward        触发前向验证（参数：train_days, test_days, step_days, max_weight）
GET    /api/validation/wf-summary          样本外汇总
GET    /api/validation/wf-window-metrics   各窗口指标

# 统计检验
POST   /api/validation/stat-tests          触发统计检验（参数：samples, block_size）
GET    /api/validation/significance-tests  t 检验结果
GET    /api/validation/bootstrap           bootstrap 区间

# 因子分析
POST   /api/factor/pca                     触发 PCA（参数：components）
GET    /api/factor/explained-variance      解释方差
GET    /api/factor/loadings                载荷矩阵
GET    /api/factor/pc-returns              PC 收益序列

# 人工规则
GET    /api/rules                          当前规则列表
PUT    /api/rules                          保存规则 CSV
POST   /api/rules/dify-extract             Dify Workflow B 抽取草稿

# 报告
POST   /api/report/generate                触发报告生成（参数：focus, engine, notes）
GET    /api/report/current                 当前报告内容
GET    /api/report/stream                  流式生成（SSE）

# 全流程
POST   /api/pipeline/run                   一键执行全部计算
GET    /api/pipeline/status/{task_id}      查询异步任务进度
```

**关键设计**：

- 每个 `POST` 触发计算 → 返回 `task_id` → 前端轮询 `GET /api/pipeline/status/{task_id}`
- 重计算任务放入 Celery 队列，避免阻塞 API
- 计算结果缓存到 Redis（key = 参数 hash），重复请求直接返回缓存
- `src/` 模块被 `services/` 封装调用，`pd.to_csv()` 改为 `return DataFrame/JSON`

### Step 2：React 前端

**技术选型**：React 18 + TypeScript + Vite + Tailwind CSS + ECharts

**页面结构**（与现有 Streamlit 页面一一对应）：

```
src/
├── pages/
│   ├── Overview.tsx           # 数据总览
│   ├── MarketBenchmark.tsx    # 市场与基准
│   ├── SingleStock.tsx        # 单股分析
│   ├── Portfolio.tsx          # 组合优化
│   ├── Correlation.tsx        # 相关性热力图
│   ├── Validation.tsx         # Walk-forward + 统计检验
│   ├── Rules.tsx              # 人工规则
│   └── Report.tsx             # 智能报告
├── components/
│   ├── charts/
│   │   ├── CumulativeReturnChart.tsx   # 累计收益曲线
│   │   ├── DrawdownChart.tsx           # 回撤曲线
│   │   ├── BollingerChart.tsx          # 布林带
│   │   ├── EfficientFrontierChart.tsx  # 有效前沿
│   │   ├── WeightBarChart.tsx          # 权重柱状图
│   │   ├── CorrelationHeatmap.tsx      # 相关性热力图
│   │   ├── SharpeComparisonChart.tsx   # 训练/测试夏普对比
│   │   └── WindowSharpeLine.tsx        # 各窗口夏普折线图
│   ├── cards/
│   │   ├── MetricCard.tsx              # 通用指标卡片（年化收益/波动率/夏普/回撤）
│   │   └── StatsGrid.tsx              # 指标网格
│   ├── tables/
│   │   ├── DataTable.tsx              # 通用表格（排序/筛选/导出）
│   │   └── RulesEditor.tsx            # 规则编辑表格
│   ├── layout/
│   │   ├── Sidebar.tsx                # 侧边栏导航 + 操作按钮
│   │   └── PipelineProgress.tsx       # 全流程进度条
│   └── common/
│       ├── StockSelector.tsx          # 股票选择器
│       ├── ParamSlider.tsx            # 参数滑块
│       └── MarkdownRenderer.tsx       # 报告 Markdown 渲染
├── hooks/
│   ├── useApi.ts               # API 请求 hook
│   ├── usePolling.ts           # 轮询任务状态
│   └── useSSE.ts              # SSE 流式接收
├── store/
│   └── index.ts               # Zustand 全局状态
└── types/
    └── api.ts                 # API 响应类型定义
```

**图表迁移对照**（Streamlit Plotly → React ECharts）：

| Streamlit 图表 | React ECharts 替代 | 数据接口 |
|----------------|-------------------|----------|
| `plot_cumulative_returns()` → `st.plotly_chart` | `CumulativeReturnChart` (line chart) | `GET /api/analysis/cumulative-returns` |
| `plot_drawdown()` → `st.plotly_chart` | `DrawdownChart` (area chart) | `GET /api/portfolio/returns` |
| Bollinger `go.Scatter * 4` | `BollingerChart` (candlestick + bands) | `GET /api/analysis/bollinger?ticker=` |
| `px.scatter` 有效前沿 | `EfficientFrontierChart` (scatter) | `GET /api/portfolio/efficient-frontier` |
| `px.bar` 权重柱状图 | `WeightBarChart` (horizontal bar) | `GET /api/portfolio/weights` |
| `px.imshow` 相关性热力图 | `CorrelationHeatmap` (heatmap) | `GET /api/analysis/correlation` |
| `px.bar` 夏普对比 | `SharpeComparisonChart` (grouped bar) | `GET /api/validation/wf-summary` |
| `px.line` 各窗口夏普 | `WindowSharpeLine` (line + markers) | `GET /api/validation/wf-window-metrics` |
| VIX `px.line` | 内嵌在 `MarketBenchmark` 页 | `GET /api/data/market?ticker=^VIX` |

### Step 3：Docker 容器化

**文件**：

```
docker-compose.yml
backend/Dockerfile
frontend/Dockerfile
nginx/nginx.conf
```

```yaml
# docker-compose.yml
version: "3.9"
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_DATABASE: us_stock_mvp
    ports: ["3306:3306"]
    volumes: [mysql_data:/var/lib/mysql]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  backend:
    build: ./backend
    depends_on: [mysql, redis]
    environment: ...
    ports: ["8000:8000"]
    volumes: [./src:/app/src, ./data:/app/data, ./config:/app/config]

  celery-worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info
    depends_on: [redis, mysql]

  frontend:
    build: ./frontend
    ports: ["5173:80"]
    depends_on: [backend]

  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes: [./nginx/nginx.conf:/etc/nginx/conf.d/default.conf]
    depends_on: [frontend, backend]
```

### Step 4：异步任务系统

**Celery 任务定义**：

```python
# backend/tasks/pipeline.py

@celery_app.task(bind=True)
def run_full_pipeline(self, params: PipelineParams):
    """一键全流程，逐步更新进度"""
    steps = [
        ("基础分析", run_analysis_engine),
        ("组合优化", run_portfolio_optimization),
        ("前向验证", run_walk_forward),
        ("统计检验", run_stat_tests),
    ]
    total = len(steps)
    for i, (name, fn) in enumerate(steps):
        self.update_state(state="PROGRESS", meta={"step": name, "progress": i / total})
        fn(params)
    return {"status": "complete"}
```

前端通过轮询 `GET /api/pipeline/status/{task_id}` 拿到 `{ step, progress }` 渲染进度条。

---

## 四、现有资产在前端的落位

| 现有 Streamlit 元素 | 前端落位 | 数据来源 API |
|---------------------|----------|-------------|
| `st.dataframe(universe)` | `DataTable` 组件 | `GET /api/data/universe` |
| `metric_card(研究股票数)` | `MetricCard` 组件 | `GET /api/data/overview` |
| `plot_cumulative_returns(cumulative)` | `CumulativeReturnChart` | `GET /api/analysis/cumulative-returns` |
| VIX `px.line` | `MarketBenchmark` 页内嵌 | `GET /api/data/market?ticker=^VIX` |
| `st.selectbox(选择股票)` | `StockSelector` 组件 | `GET /api/data/universe` |
| 单股 metric_card * 4 | `StatsGrid` 组件 | `GET /api/analysis/single-stock-metrics` |
| 布林带 4 条线图 | `BollingerChart` | `GET /api/analysis/bollinger?ticker=` |
| `st.dataframe(opt_metrics)` | `DataTable` | `GET /api/portfolio/metrics` |
| 优化组合净值曲线 | `CumulativeReturnChart` | `GET /api/portfolio/returns` |
| 回撤曲线 | `DrawdownChart` | `GET /api/portfolio/returns` |
| `st.selectbox(选择权重组合)` | 下拉选择器 | `GET /api/portfolio/weights` |
| `px.bar(前20权重)` | `WeightBarChart` | `GET /api/portfolio/weights` |
| `px.scatter(有效前沿)` | `EfficientFrontierChart` | `GET /api/portfolio/efficient-frontier` |
| `px.imshow(相关性热力图)` | `CorrelationHeatmap` | `GET /api/analysis/correlation` |
| WF 样本外表格 | `DataTable` | `GET /api/validation/wf-summary` |
| `px.bar(训练/测试夏普)` | `SharpeComparisonChart` | `GET /api/validation/wf-summary` |
| `px.line(各窗口夏普)` | `WindowSharpeLine` | `GET /api/validation/wf-window-metrics` |
| t 检验表 | `DataTable` | `GET /api/validation/significance-tests` |
| bootstrap 表 | `DataTable` | `GET /api/validation/bootstrap` |
| `st.text_area(规则编辑)` | `RulesEditor` | `GET /api/rules` + `PUT /api/rules` |
| `st.button(保存/重算)` | 按钮 + `PipelineProgress` | `POST /api/rules/dify-extract` |
| `st.radio(生成引擎)` | RadioGroup | `POST /api/report/generate` |
| `st.selectbox(report_focus)` | 下拉选择器 | `POST /api/report/generate` |
| `st.text_area(备注)` | 文本框 | 随请求发送 |
| 报告 Markdown 渲染 | `MarkdownRenderer` | `GET /api/report/current` |
| `st.spinner` | 骨架屏 + `PipelineProgress` | 轮询 task status |
| 侧边栏按钮 | `Sidebar` 操作区 | 各自 POST API |

---

## 五、工期估算

| 步骤 | 内容 | 工时 |
|------|------|------|
| Step 1 | FastAPI 骨架 + 全部路由 + services 封装 | 2-3 天 |
| Step 2 | React 前端（8 个页面 + 全部图表组件） | 3-5 天 |
| Step 3 | Docker 容器化 | 0.5 天 |
| Step 4 | Celery 异步任务 + Redis 缓存 | 1 天 |
| - | 联调、Debug、样式打磨 | 1-2 天 |
| **合计** | | **8-12 天** |

---

## 六、与原方案的关系

- `src/` 下所有 `.py` **不修改**，只通过 `backend/services/` 封装调用
- 当前 Streamlit `dashboard.py` **保留不动**——可以作为轻量备选方案继续使用
- 前端优先调用 API，API 的 JSON 响应同时兼容新前端和旧 Streamlit（只需在 Streamlit 侧加一个 `requests.get()` 包装）
- 两份系统可同时运行，渐进迁移
