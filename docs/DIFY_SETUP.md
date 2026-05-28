# Dify 工作流精确配置说明

本文档用于把 Dify 工作流和当前 Python 代码对齐。

当前建议：

```text
Python 负责量化计算
Dify 负责报告生成和人工规则草稿
DeepSeek V4 Pro 作为 Dify 和 LangChain 共用的大模型
```

MVP 阶段不做 RAG。

## 1. 总体架构

```text
Python:
  fetch_market_data.py
  analysis_engine.py
  portfolio_optimization.py
  walk_forward.py
  stat_tests.py

输出:
  data/output/*.csv
  data/output/*.json

Dify Workflow A:
  输入 data/output/*.csv/json + 人工备注
  输出中文 Markdown 投研报告

Dify Workflow B:
  输入自然语言人工判断
  输出 config/human_overrides.csv 兼容规则草稿
```

Dify 不直接修改 MySQL，也不直接替代 Python 的优化计算。

## 2. DeepSeek 模型供应商配置

在 Dify 中进入：

```text
Workspace -> Settings -> Model Provider
```

如果 Dify 有 DeepSeek provider，直接添加 DeepSeek。

如果没有，使用 OpenAI-compatible provider。

配置：

| 项目 | 值 |
|---|---|
| Provider Type | OpenAI-compatible |
| API Key | 你的 DeepSeek API Key |
| Base URL | `https://api.deepseek.com` |
| Model Name | `deepseek-v4-pro` |

建议默认参数：

| 参数 | 报告生成 | 规则抽取 |
|---|---:|---:|
| Temperature | `0.2` | `0.0` 到 `0.1` |
| Top P | `0.9` | `0.8` |
| Max Tokens | `8000` 到 `12000` | `2000` 到 `4000` |
| Presence Penalty | `0` | `0` |
| Frequency Penalty | `0` | `0` |
| Streaming | 开启 | 可开可关 |
| Memory | 关闭 | 关闭 |

解释：

- 报告生成需要稳定、克制，所以 `temperature=0.2`。
- 规则抽取是结构化任务，随机性越低越好。
- Workflow 不建议开启 Memory，避免历史对话污染本次报告。

## 3. Workflow A：投资报告生成

### 3.1 创建应用

路径：

```text
Studio -> Create App -> Create from Blank -> Workflow
```

应用名称建议：

```text
美股50股策略报告生成器
```

描述建议：

```text
读取 Python 量化分析输出和人工研究备注，生成中文投资策略分析报告。
```

### 3.2 Start 节点变量

在 Start/User Input 节点添加以下变量。

如果你的 Dify 版本字段类型名称不同，按这个对应关系理解：

```text
Paragraph = 长文本 / 多行文本
Text = 短文本 / 单行文本
Select = 下拉选择
```

| 变量名 | 显示名称 | 类型 | 必填 | 默认值 | 建议最大长度 | 对应文件 |
|:--|---|---|---|---|---:|---|
| `analysis_summary_json` | 分析摘要 JSON | Paragraph | 是 | 空 | 20000 | `data/output/analysis_summary.json` |
| `portfolio_metrics_csv` | 等权组合指标 CSV | Paragraph | 是 | 空 | 12000 | `data/output/portfolio_metrics.csv` |
| `opt_portfolio_metrics_csv` | 优化组合指标 CSV | Paragraph | 是 | 空 | 12000 | `data/output/optimized_portfolio_metrics.csv` |
| `walk_forward_summary_csv` | 前向验证汇总 CSV | Paragraph | 是 | 空 | 12000 | `data/output/walk_forward_summary.csv` |
| `significance_tests_csv` | 统计显著性检验 CSV | Paragraph | 是 | 空 | 20000 | `data/output/significance_tests.csv` |
| `bootstrap_intervals_csv` | Bootstrap 区间 CSV | Paragraph | 是 | 空 | 20000 | `data/output/bootstrap_intervals.csv` |
| `human_overrides_csv` | 人工规则 CSV | Paragraph | 否 | 空 | 12000 | `config/human_overrides.csv` |
| `human_research_notes` | 人工研究备注 | Paragraph | 否 | 空 | 20000 | 人工输入 |
| `report_focus` | 报告重点 | Select | 是 | `balanced` | - | 人工选择 |
| `report_language` | 报告语言 | Select | 是 | `zh-CN` | - | 固定中文 |

`report_focus` 下拉选项：

```text
balanced
risk_control
benchmark_outperformance
robustness
```

`report_language` 下拉选项：

```text
zh-CN
```

### 3.3 节点结构

推荐增强版：

```text
Start
  -> LLM：假设与限制审查
  -> LLM：投资报告生成
  -> End
```

简化版：

```text
Start
  -> LLM：投资报告生成
  -> End
```

建议先用增强版。

### 3.4 LLM 节点 1：假设与限制审查

节点名称：

```text
假设与限制审查
```

模型：

```text
deepseek-v4-pro
```

参数：

| 参数 | 值 |
|---|---|
| Temperature | `0.2` |
| Top P | `0.9` |
| Max Tokens | `3000` 到 `5000` |
| Presence Penalty | `0` |
| Frequency Penalty | `0` |
| Streaming | 开启 |
| Memory | 关闭 |

System Prompt：

```text
你是一个严谨的量化投资研究审稿人。你的任务不是推荐买卖股票，而是审查一份美股科技股组合分析的输入材料、假设边界和潜在偏差。

必须遵守：
1. 只基于用户提供的 JSON、CSV 和人工备注进行判断。
2. 不得编造新闻、财报、监管事件或公司基本面。
3. 必须明确区分“量化计算事实”“人工输入判断”“模型限制”。
4. 必须指出生存者偏差：当前股票池来自当前 XLK 持仓向历史回看，不是 point-in-time 历史成分股。
5. 不得使用“保证收益”“一定跑赢”“证明最优”等表述。
6. 输出中文。
```

User Prompt：

```text
请审查以下投资组合分析输入，并输出一段“假设与限制审查”。

【分析摘要 JSON】
{{analysis_summary_json}}

【等权组合指标 CSV】
{{portfolio_metrics_csv}}

【优化组合指标 CSV】
{{opt_portfolio_metrics_csv}}

【Walk-forward 样本外验证 CSV】
{{walk_forward_summary_csv}}

【统计显著性检验 CSV】
{{significance_tests_csv}}

【Bootstrap 区间 CSV】
{{bootstrap_intervals_csv}}

【人工规则 CSV】
{{human_overrides_csv}}

【人工研究备注】
{{human_research_notes}}

请按以下结构输出：
1. 数据来源和可用结论
2. 主要偏差和限制
3. 对结果解释的约束
4. 建议报告中必须保留的风险提示
```

输出变量：

如果 Dify 支持自定义输出变量名，设置为：

```text
assumption_review
```

如果不支持自定义，后续节点用变量选择器选择：

```text
假设与限制审查 / text
```

### 3.5 LLM 节点 2：投资报告生成

节点名称：

```text
投资报告生成
```

模型：

```text
deepseek-v4-pro
```

参数：

| 参数 | 值 |
|---|---|
| Temperature | `0.2` |
| Top P | `0.9` |
| Max Tokens | `8000` 到 `12000` |
| Presence Penalty | `0` |
| Frequency Penalty | `0` |
| Streaming | 开启 |
| Memory | 关闭 |

System Prompt：

```text
你是一个严谨的中文投资研究报告助手。你负责把已经计算好的量化结果和人工研究备注整理成课程作业级别的投资策略分析报告。

重要规则：
1. 只能使用输入中出现的数据、指标、规则和人工备注。
2. 不得编造公司新闻、财报数据、监管事件或宏观数据。
3. 不得直接给出投资建议，不得说“应该买入/卖出”。
4. 必须区分：
   - 机器计算结果
   - 人工规则干预
   - 解释性判断
   - 模型局限
5. 对马科维茨最大夏普组合必须提示过拟合风险。
6. 对 walk-forward 结果必须强调样本外表现。
7. 对统计显著性必须同时说明 p 值和 bootstrap 区间的不确定性。
8. 必须说明当前股票池无法完全排除生存者偏差。
9. 输出 Markdown。
10. 输出语言使用 {{report_language}}。
```

User Prompt：

```text
请基于以下输入生成一份结构化投资策略分析报告。

报告重点：{{report_focus}}

【分析摘要 JSON】
{{analysis_summary_json}}

【等权组合指标 CSV】
{{portfolio_metrics_csv}}

【优化组合指标 CSV】
{{opt_portfolio_metrics_csv}}

【Walk-forward 样本外验证 CSV】
{{walk_forward_summary_csv}}

【统计显著性检验 CSV】
{{significance_tests_csv}}

【Bootstrap 区间 CSV】
{{bootstrap_intervals_csv}}

【人工规则 CSV】
{{human_overrides_csv}}

【人工研究备注】
{{human_research_notes}}

【假设与限制审查】
{{假设与限制审查.text}}

请生成以下章节：

# 美股科技股 50 股投资组合策略分析报告

## 1. 研究目标与数据范围
说明研究对象、时间范围、股票池来源、基准指数和风险代理。

## 2. 方法论
说明等权组合、马科维茨最小方差组合、马科维茨最大夏普组合、walk-forward 验证、统计显著性检验。

## 3. 单股风险收益特征
总结高夏普股票、高回撤股票、与市场或 VIX 相关性较高的现象。不要编造未提供的数据。

## 4. 组合表现比较
比较等权、最小方差、最大夏普组合的收益、波动、夏普、最大回撤、回撤覆盖率。

## 5. 样本外验证与过拟合风险
重点解释 walk-forward 结果。说明全样本优化结果和样本外结果的区别。

## 6. 人工规则干预
解释 human_overrides_csv 中的规则如何影响组合权重。只能解释输入中已有原因。

## 7. 统计显著性与稳健性
解释 t 检验、bootstrap 区间，以及这些结果支持或不能支持什么结论。

## 8. 主要风险与模型局限
必须包括生存者偏差、数据窗口限制、估计误差、交易成本未纳入、模型不保证未来表现。

## 9. 结论
给出谨慎、非投资建议式结论。使用“回测显示”“样本外结果表明”“仍需人工判断”等表达。
```

注意：

- `{{假设与限制审查.text}}` 需要用 Dify 的变量选择器插入。
- 如果变量实际名称不同，选择该节点的文本输出即可。

输出变量：

如果可自定义，设置为：

```text
investment_report_md
```

否则在 End 节点选择：

```text
投资报告生成 / text
```

### 3.6 End 节点

节点名称：

```text
输出报告
```

输出变量：

| 输出变量名 | 类型 | 来源 |
|---|---|---|
| `investment_report_md` | String | `投资报告生成 / text` |
| `assumption_review` | String | `假设与限制审查 / text` |

如果你使用简化版，只保留：

| 输出变量名 | 类型 | 来源 |
|---|---|---|
| `investment_report_md` | String | `投资报告生成 / text` |

### 3.7 第一次测试输入建议

第一次不要粘太多内容，先跑通。

建议：

```text
analysis_summary_json：完整粘贴
portfolio_metrics_csv：完整粘贴
opt_portfolio_metrics_csv：完整粘贴
walk_forward_summary_csv：完整粘贴
significance_tests_csv：只粘前 20 行
bootstrap_intervals_csv：只粘前 20 行
human_overrides_csv：完整粘贴
human_research_notes：写 3-5 条人工判断
report_focus：balanced
report_language：zh-CN
```

跑通后再粘完整统计检验文件。

## 4. Workflow B：人工规则抽取

### 4.1 创建应用

路径：

```text
Studio -> Create App -> Create from Blank -> Workflow
```

应用名称建议：

```text
美股组合人工规则抽取器
```

描述建议：

```text
把人工基本面、新闻、监管和风险判断转换为 config/human_overrides.csv 兼容规则草稿。
```

### 4.2 Start 节点变量

| 变量名 | 显示名称 | 类型 | 必填 | 默认值 | 建议最大长度 | 用途 |
|---|---|---|---|---|---:|---|
| `human_rule_text` | 人工规则描述 | Paragraph | 是 | 空 | 12000 | 输入自然语言规则 |
| `effective_start_date` | 默认开始日期 | Text | 是 | `2024-01-01` | 20 | 规则默认生效日期 |
| `effective_end_date` | 默认结束日期 | Text | 否 | 空 | 20 | 空值表示持续生效 |

如果没有 Text 类型，用 Paragraph，最大长度设为 `50`。

### 4.3 节点结构

```text
Start
  -> LLM：人工规则抽取
  -> End
```

### 4.4 LLM 节点：人工规则抽取

节点名称：

```text
人工规则抽取
```

模型：

```text
deepseek-v4-pro
```

参数：

| 参数 | 值 |
|---|---|
| Temperature | `0.0` 到 `0.1` |
| Top P | `0.8` |
| Max Tokens | `2000` 到 `4000` |
| Presence Penalty | `0` |
| Frequency Penalty | `0` |
| Streaming | 可开可关 |
| Memory | 关闭 |

System Prompt：

```text
你是一个投资组合规则抽取器。你的任务是把人类分析师的自然语言判断转换为结构化规则草稿。

必须遵守：
1. 只输出 CSV，不输出解释。
2. CSV 表头必须严格为：
ticker,start_date,end_date,action,min_weight,max_weight,return_multiplier,risk_multiplier,reason
3. action 只能是 exclude、cap、floor、boost、penalize、note。
4. 如果用户没有给日期，使用输入变量 effective_start_date 和 effective_end_date。
5. 如果没有给 min_weight，填 0。
6. 如果没有给 max_weight，普通规则填 0.10；exclude 填 0。
7. 如果没有给 return_multiplier，填 1.0。
8. 如果没有给 risk_multiplier，填 1.0。
9. 不得发明 ticker。
10. reason 必须简短复述用户原始原因。
```

User Prompt：

```text
请把以下人工判断转换为 config/human_overrides.csv 兼容格式。

默认开始日期：{{effective_start_date}}
默认结束日期：{{effective_end_date}}

人工判断：
{{human_rule_text}}
```

### 4.5 End 节点

节点名称：

```text
输出规则草稿
```

输出变量：

| 输出变量名 | 类型 | 来源 |
|---|---|---|
| `rules_csv` | String | `人工规则抽取 / text` |

把 `rules_csv` 复制到本地：

```text
config/human_overrides.csv
```

人工检查后运行：

```powershell
python portfolio_optimization.py --rules config/human_overrides.csv
python walk_forward.py --rules config/human_overrides.csv
python stat_tests.py
```

## 5. 可选 Workflow C：HTTP 触发 Python 重算

这个不是 MVP 必需。

后续如果要让 Dify 直接触发 Python，需要我再加一个本地 FastAPI 服务。

目标接口：

```text
POST /recalculate
```

Dify HTTP Request 节点设置：

| 项目 | 值 |
|---|---|
| Method | `POST` |
| URL | `http://127.0.0.1:8000/recalculate` |
| Headers | `Content-Type: application/json` |
| Body Type | JSON |

请求体：

```json
{
  "rules_csv": "{{rules_csv}}",
  "run_walk_forward": true,
  "run_stat_tests": true
}
```

预期返回：

```json
{
  "status": "ok",
  "outputs": {
    "portfolio_metrics": "data/output/optimized_portfolio_metrics.csv",
    "walk_forward_summary": "data/output/walk_forward_summary.csv",
    "analysis_summary": "data/output/analysis_summary.json"
  }
}
```

当前阶段先不做这个，先用 Streamlit 的“重新计算组合”按钮更稳。

## 6. 和当前 Python 文件的对应关系

| Python 文件 | 作用 | Dify 是否直接调用 |
|---|---|---|
| `fetch_market_data.py` | 抓数据、写 CSV/MySQL | 否 |
| `build_universe_50.py` | 生成 50 股股票池 | 否 |
| `analysis_engine.py` | 基础指标计算 | 否 |
| `portfolio_optimization.py` | 组合优化 | 后续 HTTP 可调用 |
| `walk_forward.py` | 前向验证 | 后续 HTTP 可调用 |
| `stat_tests.py` | 统计检验 | 后续 HTTP 可调用 |
| `llm_report.py` | 本地 LangChain 报告 | 否，Dify 自己可生成 |
| `dashboard.py` | Streamlit 展示 | 否 |

## 7. 推荐使用顺序

1. 在 Python/Streamlit 中完成数据和指标计算。
2. 在 Dify Workflow A 中粘贴输出结果，生成报告。
3. 如果你有自然语言规则，用 Workflow B 抽取规则草稿。
4. 人工审核规则，写入 `config/human_overrides.csv`。
5. 回到 Streamlit 点击“重新计算组合”。
6. 再用 Dify Workflow A 重新生成报告。

## 8. 常见设置错误

### 变量名不一致

Prompt 中的变量名必须和 Start 节点完全一致：

```text
analysis_summary_json
portfolio_metrics_csv
opt_portfolio_metrics_csv
walk_forward_summary_csv
significance_tests_csv
bootstrap_intervals_csv
human_overrides_csv
human_research_notes
report_focus
report_language
```

### 把 Memory 打开

不建议打开。报告应只基于本次输入。

### Temperature 太高

不要用 `0.7`、`0.8` 这类设置。投研报告容易发散或补充未提供信息。

### 规则抽取输出了说明文字

规则抽取节点必须要求：

```text
只输出 CSV，不输出解释。
```

### 使用 Dify 直接替代 Python

不要这样做。Dify 不负责马科维茨优化、walk-forward、统计检验。

