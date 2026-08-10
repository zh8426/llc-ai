# AGENTS.md

# LLC AI Engineering Assistant — Agent 工作规范

## 1. 项目目标

本仓库用于开发一个面向 **Half-Bridge LLC** 电源设计评审与故障排查的 Engineering Assistant。

本产品用于辅助具备专业能力的电力电子工程师进行研发工作。

它不是安全认证工具，也不得在证据不足的情况下声称某个设计：

- 是安全的；
- 符合相关标准；
- 可以直接量产；
- 已完成充分验证。

在实现任何重要功能之前，必须先阅读：

`docs/MASTER_WORKFLOW.md`

---

## 2. 核心开发原则

所有工程分析必须遵循以下优先级：

```text
确定性工程计算
>
Engineering Rule
>
实测 Waveform Evidence
>
已验证 Engineering Case
>
LLM Interpretation
```

不得颠倒上述优先级。

如果某个工程结果可以通过程序确定性计算得到，则不得让 LLM 替代该计算。

例如：

- 谐振频率；
- RMS；
- Peak Current；
- Dead Time；
- 电压裕量；
- 器件参数比较；

都应优先使用确定性程序计算。

LLM 主要负责：

- 理解自然语言；
- 调用工具；
- 整理分析过程；
- 解释计算结果；
- 检索 Evidence；
- 生成报告。

---

## 3. 当前产品范围

当前支持的拓扑：

`Half-Bridge LLC`

当前 MVP 目标范围：

`300–1000 W`

典型输入范围：

`300–420 VDC`

典型输出：

`24 V / 48 V`

除非当前任务明确要求，否则不得自行扩展到：

- Full-Bridge LLC
- CLLC
- Bidirectional Converter
- Interleaved LLC
- Multi-phase LLC
- 其他 Resonant Converter

不得为了“代码通用性”而提前实现当前产品范围之外的大量功能。

优先保证当前 MVP 正确、可靠、可验证。

---

## 4. Engineering Assumption 管理

不得静默引入任何 Engineering Assumption。

如果实现过程中新增：

- 公式；
- 参数定义；
- 阈值；
- 安全裕量；
- 近似条件；
- 工作区域定义；
- 工程经验规则；

必须：

1. 明确记录；
2. 说明适用范围；
3. 明确单位；
4. 尽可能说明来源或工程依据；
5. 写入：

`docs/DOMAIN_ASSUMPTIONS.md`

如果无法确定正确的工程行为：

**禁止自行猜测。**

应该返回：

`INSUFFICIENT_DATA`

或者建立明确的：

`TODO: Requires domain expert review`

不得为了让程序继续运行而凭经验随意填写数值。

---

## 5. Engineering Calculation

所有工程计算必须满足：

- deterministic；
- 输入类型明确；
- 单位明确；
- 内部尽量统一使用 SI Units；
- 返回 structured output；
- 包含 formula/version identifier；
- 有对应 unit test；
- 可重复计算；
- 不依赖 LLM。

禁止：

```python
return "大约 100 kHz"
```

推荐：

```json
{
  "name": "resonant_frequency",
  "value": 109423.2,
  "unit": "Hz",
  "formula_version": "LLC-FR-V1"
}
```

如果计算依赖多个输入，应保留相关输入信息，以支持：

- Debug；
- Review；
- Evidence Trace；
- Report Generation。

---

## 6. Unit 处理规范

禁止使用隐式单位。

错误：

```python
lr = 45
cr = 47
```

因为无法判断：

- 45 H？
- 45 mH？
- 45 uH？

正确：

```text
Lr = 45 uH
Cr = 47 nF
```

或者在内部归一化为：

```text
Lr = 45e-6 H
Cr = 47e-9 F
```

Unit Conversion 必须发生在明确的数据边界。

推荐使用 Unit Library，而不是在代码中散布：

```python
* 1e-6
* 1e-9
* 1000
```

之类的 Magic Conversion。

API、数据库、Calculation Engine 和 Frontend 之间必须明确定义单位。

---

## 7. Datasheet Parameter 规范

当 Datasheet Parameter 与测试条件相关时，禁止仅保存一个数字。

例如禁止只保存：

```text
Rds(on) = 80 mΩ
```

应尽可能同时保存：

- minimum；
- typical；
- maximum；
- unit；
- junction temperature；
- voltage condition；
- current condition；
- gate condition；
- test condition；
- source document；
- source page；
- extraction confidence；
- human verification status。

例如：

```text
Parameter: Rds(on)
Typical: 80 mΩ
VGS: 10 V
ID: 20 A
TJ: 25 °C
Source: datasheet
Page: 4
Human Verified: true
```

严禁：

- 用 Typical 替代 Maximum；
- 用不同 Test Condition 下的数据直接比较；
- 凭空补全 Datasheet 中缺失的参数；
- 将无法确认的 Curve Reading 当作精确数值。

---

## 8. Rule Engine

所有 Review Rule 必须返回统一的 Finding Schema。

Severity 只允许：

```text
PASS
INFO
WARNING
CRITICAL
INSUFFICIENT_DATA
```

不得自行新增：

```text
GOOD
BAD
DANGER
OK
FAILED
```

等未经定义的 Severity。

一个完整 Finding 至少应能够表达：

```text
rule_id
category
severity
title
description
evidence
calculated_values
missing_information
recommended_action
requires_engineer_confirmation
```

任何：

`WARNING`

或：

`CRITICAL`

必须包含 Evidence。

Evidence 可以来自：

- User Input；
- Engineering Calculation；
- Datasheet；
- Waveform；
- Rule Definition；
- Verified Fault Case。

没有 Evidence 的 WARNING / CRITICAL 不得进入正式 Engineering Report。

---

## 9. Engineering Margin

除非存在明确标准、企业规范或经过确认的项目要求，否则 Engineering Margin 必须配置化。

禁止根据模型自身经验硬编码所谓“通用安全裕量”。

例如不得因为 LLM 认为：

> MOSFET 应该留 20% 电压裕量。

就直接把：

```python
VDS_REQUIRED_MARGIN = 20%
```

写入系统。

如果需要 Margin，应：

1. 明确来源；
2. 明确应用场景；
3. 写入配置；
4. 写入 `DOMAIN_ASSUMPTIONS.md`。

---

## 10. LLM 使用边界

LLM 可以：

- 理解自然语言；
- 调度 Tool；
- 整理上下文；
- 总结 Engineering Result；
- 解释 Finding；
- 检索相关 Evidence；
- 查询 Fault Case；
- 生成 Review Report；
- 生成 Troubleshooting Report。

LLM 不得：

- Fabricate Component Specification；
- 静默补充缺失设计参数；
- 直接完成本可由 Python 完成的确定性数学计算；
- 进行权威 Safety Certification；
- 将 Simulation Data 称为 Measured Data；
- 将 Estimated Value 称为 Measured Value；
- 在 Evidence 不足时声明设计安全；
- 绕过 Calculation Engine；
- 绕过 Rule Engine；
- 将模型自身知识当作正式 Datasheet 参数。

---

## 11. Safety

本项目涉及：

- 高压；
- 高电流；
- 高能量储能元件；
- 可能具有致命危险的 Power Converter。

因此必须采用保守的 Safety Policy。

禁止实现以以下行为为目的的功能：

- bypass protection；
- disable OCP；
- disable OVP；
- disable OTP；
- 自动降低 Safety Limit；
- 自动短接保护；
- 未经适当保护直接 Energize Experimental Hardware；
- 让 LLM 直接控制 Converter PWM；
- 让 LLM 直接修改实时保护参数。

涉及 High-Risk Engineering Recommendation 时，必须明确要求：

`Engineer Confirmation`

必要时输出：

`Requires qualified engineer review.`

系统永远只能作为 Engineering Assistance Tool，而不是 Safety Authority。

---

## 12. Waveform Data 规范

所有 Waveform Analysis 必须保留必要的 Metadata。

至少包括：

- channel name；
- physical meaning；
- unit；
- probe ratio；
- sample rate；
- polarity；
- offset；
- bandwidth information（如果存在）；
- test condition。

Test Condition 应尽量包含：

- Vin；
- Vout；
- Load；
- Power；
- Switching Mode；
- Temperature；
- Operating State。

不得在必要 Channel 或 Metadata 缺失时强行分类。

如果信息不足，应返回：

`INSUFFICIENT_DATA`

而不是猜测。

---

## 13. Signal Processing

Waveform Analysis Algorithm 必须尽可能使用可验证的 deterministic signal processing。

例如：

- Rising Edge Detection；
- Falling Edge Detection；
- Switching Cycle Segmentation；
- Frequency Measurement；
- Peak Detection；
- RMS Calculation；
- Dead Time Measurement；
- VDS at Turn-On Measurement。

这些功能必须优先使用：

- NumPy；
- SciPy；
- pandas；
- 明确的 Signal Processing Algorithm。

不得优先让 Vision Model 或 LLM 根据示波器截图猜测数值。

---

## 14. Synthetic Waveform Tests

对于 Waveform Algorithm，应尽可能建立 Synthetic Waveform Fixture。

至少应逐步覆盖：

```text
Clean ZVS

Partial ZVS

Hard Switching

Ringing

Noise

Missing Channel

Wrong Unit

Irregular Sampling
```

每一个新 Signal Processing Algorithm 都应考虑：

- Noise；
- Sampling Rate；
- Threshold Sensitivity；
- Missing Data；
- Numerical Stability。

---

## 15. Testing

任何 Engineering Feature 都必须配套 Test。

Backend 默认测试命令：

```bash
pytest
```

每完成一个 Engineering Module，应运行相关测试。

一个 Phase 完成之前，应运行完整 Backend Test Suite。

Frontend 修改后至少运行：

```bash
npm run build
```

如果已经配置 Frontend Tests，也必须执行。

不得在 Test Failed 的情况下声称：

> Task Complete

除非失败项目明确：

- 与当前任务无关；
- 已存在；
- 已记录原因。

---

## 16. Calculation Test 要求

每一个 Engineering Formula 至少需要覆盖：

1. Normal Input；
2. Boundary Input；
3. Invalid Input；
4. Unit Conversion；
5. Missing Required Input（如果适用）。

重要公式需要使用：

- 独立手工计算；
- 已知参考设计；
- 权威 Reference；

进行交叉验证。

---

## 17. Rule Test 要求

每一个 Rule 至少测试：

- Trigger Condition；
- Non-trigger Condition；
- Missing Data；
- Invalid Data（如果适用）。

禁止只测试“正常情况”。

对于 Critical Rule，需要重点验证：

- False Negative；
- Evidence；
- Missing Information；
- Severity。

---

## 18. Code Quality

优先使用：

- Small Function；
- Explicit Type；
- Pure Engineering Calculation Function；
- Clear Domain Model；
- Descriptive Naming；
- Dependency Injection；
- Structured Result。

避免：

- 超大型 Service Class；
- Hidden Global State；
- Magic Number；
- 重复 Engineering Formula；
- API Endpoint 中混入 Business Logic；
- Frontend 中执行 Engineering Calculation；
- LLM Prompt 中隐藏 Engineering Rule。

---

## 19. Architecture Separation

必须保持以下层次分离：

```text
API

Domain Model

Engineering Engine

Rule Engine

Waveform Engine

Datasheet Parser

Persistence

Fault Diagnosis

LLM Orchestration

Reporting

Frontend
```

例如：

FastAPI Route 不应该直接实现：

```python
fr = 1 / (2 * pi * sqrt(lr * cr))
```

而应该调用：

```python
calculate_resonant_frequency(...)
```

Engineering Formula 应只存在于明确的 Engineering Module 中。

---

## 20. Engineering Engine 与 LLM 分离

Engineering Engine 必须能够：

**完全不依赖 LLM 独立运行。**

即使：

- LLM API 不可用；
- 网络不可用；
- AI Provider 不可用；

以下能力仍应正常工作：

- Project Calculation；
- Design Review；
- Rule Engine；
- Waveform Analysis；
- ZVS Check；
- HTML Review Report。

LLM 是 Enhancement Layer，不是核心 Engineering Runtime。

---

## 21. Persistence 原则

数据库应保存结构化 Engineering Data。

例如：

- Project；
- DesignParameter；
- Component；
- ComponentParameter；
- ReviewFinding；
- Waveform；
- FaultCase。

不得把所有工程数据仅以：

- JSON Blob；
- Text Prompt；
- Vector Embedding；

形式保存。

需要精确计算和查询的数据必须结构化。

---

## 22. Fault Case 规范

FaultCase 至少应能够描述：

```text
Topology

Power

Operating Condition

Symptom

Observed Features

Root Cause

Verification Method

Repair Action

Before Waveform

After Waveform

Engineer Verified
```

只有：

```text
engineer_verified = true
```

的案例才可以作为 Production Diagnostic Evidence。

未经确认的案例只能：

- 搜索；
- Research；
- 辅助参考；

不得作为确定性诊断依据。

---

## 23. Fault Diagnosis 原则

Fault Diagnosis 不应采用：

```text
Symptom
↓
LLM
↓
Answer
```

必须尽量采用：

```text
Symptom
↓
Project Parameters
↓
Design Review Findings
↓
Waveform Features
↓
Verified Fault Cases
↓
Candidate Causes
↓
Evidence Ranking
↓
Recommended Next Measurement
```

诊断输出应优先返回：

`Top 3 Candidate Causes`

而不是未经充分证据直接给出唯一 Root Cause。

---

## 24. Fault Diagnosis 必须区分

每个 Candidate Cause 应能够分别记录：

- Supporting Evidence；
- Contradicting Evidence；
- Missing Information；
- Next Measurement；
- Recommended Action。

如果存在明显 Contradicting Evidence，不得隐藏。

---

## 25. Reporting 原则

Report Layer 只能消费：

- Structured Calculation Result；
- Structured Finding；
- Structured Waveform Result；
- Structured Diagnosis Result。

Report Layer 不得重新实现 Engineering Calculation。

也就是说：

```text
Engineering Engine
→ Result
→ Report
```

而不是：

```text
Report
→ 再算一次
```

这样可以避免两个模块得出不同数字。

---

## 26. Documentation

如果新增：

- Formula；
- Rule；
- Architecture Decision；
- Safety Policy；
- Engineering Assumption；
- API；

必须更新对应文档。

主要文档：

```text
docs/MASTER_WORKFLOW.md

docs/ARCHITECTURE.md

docs/DOMAIN_ASSUMPTIONS.md

docs/RULES.md

docs/API.md

docs/SAFETY.md
```

代码和文档不能长期不同步。

---

## 27. Git Discipline

每次只处理一个 Logical Task。

进行较大修改前：

先阅读现有代码和架构。

不要为了完成当前任务而进行无关的大范围 Refactor。

禁止为了“更简单”直接覆盖已经正常工作的功能。

推荐 Commit Style：

```text
feat(engine):
feat(rules):
feat(api):
feat(ui):
feat(waveform):
feat(datasheet):
feat(diagnosis):
feat(llm):
test():
fix():
docs():
refactor():
```

---

## 28. Phase Discipline

必须按照：

`docs/MASTER_WORKFLOW.md`

定义的 Phase 推进。

只完成当前明确要求的 Phase。

不得在任务完成后自动继续下一个 Phase。

例如：

当任务要求实现：

`LLC Core Calculation Engine`

不得顺便继续：

- LLM；
- RAG；
- Agent；
- Datasheet Parser；
- User Authentication；
- Payment；
- Cloud Deployment。

避免 Scope Creep。

---

## 29. Codex 工作流程

处理每个任务时，应遵循：

```text
READ
↓
PLAN
↓
IMPLEMENT
↓
TEST
↓
REVIEW
↓
DOCUMENT
↓
STOP
```

### READ

阅读：

- AGENTS.md；
- 当前 Phase；
- 相关代码；
- 相关 Test；
- 相关 Documentation。

### PLAN

在修改代码之前形成简洁 Implementation Plan。

### IMPLEMENT

只实现当前 Scope。

### TEST

运行相关 Test。

### REVIEW

检查：

- Logic；
- Unit；
- Error Handling；
- Evidence；
- Safety；
- Regression Risk。

### DOCUMENT

更新必要 Documentation。

### STOP

完成当前任务后停止。

不得自行进入下一 Phase。

---

## 30. Definition of Done

代码写完不代表任务完成。

一个 Task 只有同时满足以下条件才算 Done：

- Feature 已实现；
- Architecture Boundary 未被破坏；
- Test 已增加；
- Test 已通过；
- Error Handling 已实现；
- Units 已明确；
- Structured Output 已实现；
- 新 Engineering Assumption 已记录；
- Documentation 已同步；
- 未引入 Unsupported Safety Claim；
- 未引入明显 Regression。

---

## 31. 完成任务后的固定报告格式

每次 Codex 完成任务后，必须返回以下内容。

### Changes

说明本次实现了什么。

### Files

列出：

- 新增文件；
- 修改文件；
- 删除文件。

### Tests

说明新增或修改了哪些 Test。

### Verification

列出实际执行的 Command，例如：

```bash
pytest
npm run build
```

以及结果。

### Engineering Assumptions

列出本次是否增加：

- Formula；
- Threshold；
- Approximation；
- Engineering Assumption。

如果没有：

明确写：

`None`

### Limitations

说明：

- 当前不支持什么；
- 哪些部分仍需要 Domain Review；
- 已知限制。

### Next Step

只推荐一个下一步任务。

**不得自动执行 Next Step。**

---

## 32. 遇到 Engineering Uncertainty 时

当 Codex 不确定某个 LLC Engineering Question 时：

不得根据语言模型知识自行做出重大设计决定。

应优先：

1. 检查已有 Documentation；
2. 检查代码中的 Domain Definition；
3. 检查现有 Test；
4. 查找项目中已有 Reference；
5. 如果仍无法确定，将其标记为需要 Domain Expert Review。

允许：

```text
INSUFFICIENT_DATA
```

允许：

```text
TODO: Domain expert validation required.
```

不允许：

> “通常应该是这个数，所以直接这样实现。”

---

## 33. 当前开发优先级

当前项目优先级：

```text
Correctness
>
Traceability
>
Testability
>
Safety
>
Engineering Value
>
Performance
>
UI Polish
>
AI Capability
```

不得为了：

- UI 更漂亮；
- AI 回答更自然；
- Demo 更炫；

牺牲 Engineering Correctness 和 Traceability。

---

## 34. 项目最终原则

本项目不是：

> ChatGPT + LLC PDF

而应该逐步成为：

```text
Structured Engineering Data
+
Deterministic Calculation Engine
+
Engineering Rule Engine
+
Waveform Analysis
+
Verified Fault Knowledge
+
LLM Orchestration
```

最终核心目标不是让 AI：

> “看起来像一个电源工程师。”

而是让系统能够：

> **基于可计算的数据、可验证的规则、真实测量 Evidence 和经过确认的 Engineering Case，辅助工程师完成 LLC Design Review 与 Troubleshooting。**