# LLC AI Design Review & Troubleshooting Assistant

## Codex Master Workflow

版本：v0.2
项目阶段：MVP
目标用户：中小型电源研发团队
第一支持拓扑：Half-Bridge LLC
第一支持范围：300–1000 W、300–420 VDC 输入、24/48 V 固定输出

Phase 编号唯一依据：本文第 51–62 节定义的 Phase Prompt 与“Phase 0–10 权威开发顺序”。标记为 Cross-Phase 或 Future Extension 的内容不占用 Phase 编号，必须单独授权后实施。

---

# 0. 项目最终目标

构建一个面向电源研发工程师的 LLC 设计评审与故障排查助手。

系统最终应能够：

1. 建立 LLC 电源项目。
2. 输入设计规格。
3. 输入或导入 LLC 谐振腔参数。
4. 导入 BOM。
5. 解析主要器件数据手册。
6. 使用确定性工程计算引擎计算设计参数。
7. 使用规则引擎执行设计评审。
8. 输出 Pass / Warning / Critical / Insufficient Data。
9. 上传示波器 CSV 波形。
10. 自动提取开关频率、死区、峰值等特征。
11. 实现第一项波形诊断：ZVS Check。
12. 建立结构化故障案例库。
13. 使用大模型调用计算、规则、检索、波形分析等工具。
14. 根据证据生成设计评审与故障分析报告。
15. 所有关键工程结论必须可追溯到：

* 用户输入；
* 确定性计算；
* 数据手册；
* 工程规则；
* 实测波形；
* 已验证故障案例。

AI不得作为最终安全认证主体。

---

# 1. MVP 产品边界

## 1.1 第一版支持

拓扑：

* Half-Bridge LLC

功率：

* 300–1000 W

输入：

* 300–420 VDC

输出：

* 24 V
* 48 V

控制方式：

* Variable Frequency Control

第一版器件：

* Silicon MOSFET
* Diode Rectification

后续再增加：

* Synchronous Rectification
* SiC MOSFET
* GaN
* Full-Bridge LLC
* CLLC
* Bidirectional Converter
* Interleaved LLC

---

# 2. 第一版不做

MVP禁止实现以下功能：

* AI自动生成可以直接量产的完整电源原理图。
* AI自动决定产品符合安规。
* AI直接控制高压实验设备。
* AI自动修改保护阈值并写入硬件。
* AI直接驱动PWM。
* AI绕过OCP、OVP、OTP等保护。
* AI根据不完整信息给出“绝对安全”结论。
* AI自行编造器件参数。
* 使用LLM完成本应由确定性代码完成的工程数学计算。
* 从任意截图完全恢复复杂原理图网络。
* 第一版支持全部LLC变种。

---

# 3. 系统设计原则

系统必须按照以下层次工作：

```text
用户输入
    ↓
结构化数据
    ↓
确定性计算引擎
    ↓
工程规则引擎
    ↓
波形分析引擎
    ↓
技术资料检索
    ↓
故障案例检索
    ↓
LLM编排与解释
    ↓
结构化报告
```

重要原则：

> LLM负责理解、调用工具、解释和生成报告。

而：

> 数值计算、阈值检查、信号处理和硬性工程判断尽可能由确定性程序完成。

---

# 4. 技术栈

## Backend

Python 3.12+

FastAPI

Pydantic

SQLAlchemy

Alembic

PostgreSQL

开发阶段允许：

SQLite

---

## Engineering Calculation

NumPy

SciPy

pandas

Pint

---

## Waveform

NumPy

SciPy

pandas

Matplotlib

---

## Frontend

React

TypeScript

Vite

推荐：

TanStack Query

React Hook Form

Zod

---

## Test

pytest

pytest-cov

---

## Storage

MVP：

本地文件系统

后续：

MinIO / S3

---

# 5. 仓库结构

最终目录目标：

```text
llc-ai/
│
├── AGENTS.md
├── README.md
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
│
├── docs/
│   ├── MASTER_WORKFLOW.md
│   ├── ARCHITECTURE.md
│   ├── DOMAIN_ASSUMPTIONS.md
│   ├── RULES.md
│   ├── API.md
│   └── SAFETY.md
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── projects.py
│   │   │   ├── reviews.py
│   │   │   ├── waveforms.py
│   │   │   └── reports.py
│   │   │
│   │   ├── models/
│   │   │   ├── project.py
│   │   │   ├── component.py
│   │   │   ├── rule.py
│   │   │   ├── finding.py
│   │   │   ├── waveform.py
│   │   │   └── fault_case.py
│   │   │
│   │   ├── schemas/
│   │   │
│   │   ├── engine/
│   │   │   ├── resonant_tank.py
│   │   │   ├── gain.py
│   │   │   ├── transformer.py
│   │   │   ├── devices.py
│   │   │   ├── losses.py
│   │   │   └── thermal.py
│   │   │
│   │   ├── rules/
│   │   │   ├── engine.py
│   │   │   ├── definitions.py
│   │   │   └── builtin/
│   │   │
│   │   ├── waveform/
│   │   │   ├── loader.py
│   │   │   ├── preprocessing.py
│   │   │   ├── switching.py
│   │   │   ├── zvs.py
│   │   │   └── features.py
│   │   │
│   │   ├── datasheet/
│   │   ├── knowledge/
│   │   ├── reports/
│   │   └── services/
│   │
│   └── tests/
│
├── frontend/
│
├── examples/
│   ├── projects/
│   └── waveforms/
│
├── datasets/
│   ├── rules/
│   ├── fault_cases/
│   └── evaluation/
│
└── scripts/
```

---

# 6. 核心数据模型

## Project

```text
id
name

topology

vin_min
vin_nom
vin_max

vout
iout
pout

target_efficiency

lr
lm
cr

fsw_min
fsw_nom
fsw_max

transformer_ratio

rectification_type

controller_model

created_at
updated_at
```

单位在API层必须明确。

内部推荐统一使用SI单位。

---

# 7. Component

```text
id
project_id

reference_designator
category

manufacturer
part_number

package

datasheet_name
datasheet_version
```

---

# 8. ComponentParameter

必须同时保存参数的测试条件。

```text
id
component_id

parameter_name

value
unit

minimum
typical
maximum

test_condition

temperature
voltage_condition
current_condition

source_document
source_page

extraction_confidence

human_verified
```

例如不得仅保存：

```text
Rds_on = 80mΩ
```

必须允许表达：

```text
Rds_on = 80mΩ
Vgs = 10V
Tj = 25°C
value_type = typical
datasheet_page = 4
```

---

# 9. Review Finding

```text
id
project_id

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

severity只能是：

```text
PASS
INFO
WARNING
CRITICAL
INSUFFICIENT_DATA
```

---

# 10. Phase 1：确定性 LLC 计算引擎

Phase 1必须实现以下函数。

## 10.1 Resonant Frequency

实现：

```text
calculate_fr()
```

公式：

fr = 1 / (2π√(LrCr))

---

## 10.2 Lower Resonant Frequency

```text
calculate_fp()
```

采用项目定义的公式版本：

fp = 1 / (2π√((Lr + Lm)Cr))

必须在：

docs/DOMAIN_ASSUMPTIONS.md

记录定义及适用条件。

---

## 10.3 Characteristic Impedance

```text
calculate_zr()
```

Zr = √(Lr / Cr)

---

## 10.4 Inductance Ratio

```text
calculate_lm_lr_ratio()
```

Lm / Lr

---

## 10.5 Output Current

```text
calculate_output_current()
```

Iout = Pout / Vout

---

## 10.6 Input Power Estimate

```text
calculate_input_power()
```

Pin = Pout / efficiency

---

# 11. 所有计算函数必须满足

禁止：

```python
return "大概100kHz"
```

必须返回结构化结果：

```json
{
  "name": "resonant_frequency",
  "value": 109423.2,
  "unit": "Hz",
  "inputs": {
    "lr": 0.000045,
    "cr": 4.7e-8
  },
  "formula_version": "LLC-FR-V1"
}
```

所有工程计算必须：

* 可测试；
* 可重复；
* 有单位；
* 有输入；
* 有公式版本；
* 不依赖LLM。

---

# 12. Phase 2：第一版规则引擎

Rule必须是独立对象。

推荐接口：

```python
class ReviewRule:
    id: str
    category: str

    def evaluate(self, context):
        ...
```

统一返回：

```json
{
  "rule_id": "LLC-R001",
  "severity": "PASS",
  "title": "...",
  "evidence": {},
  "missing_information": [],
  "recommended_action": []
}
```

---

# 13. 第一批20条规则

## R001 Critical Parameter Completeness

检查：

* Vin
* Vout
* Pout
* Lr
* Lm
* Cr
* Fsw Min
* Fsw Max

缺失：

INSUFFICIENT_DATA

---

## R002 Positive Values

Lr、Lm、Cr、功率、电压、频率不得：

<= 0

异常：

CRITICAL

---

## R003 Input Voltage Ordering

必须：

Vin Min ≤ Vin Nom ≤ Vin Max

否则：

CRITICAL

---

## R004 Switching Frequency Ordering

必须：

Fsw Min < Fsw Max

否则：

CRITICAL

---

## R005 Resonant Frequency Calculation

计算：

fr

该规则主要用于生成工程数据。

---

## R006 Lower Resonant Frequency Calculation

计算：

fp

---

## R007 Resonant Frequency Operating Range

判断：

Fsw Min < fr < Fsw Max

不满足：

WARNING

不得直接判定设计失败。

---

## R008 Lm/Lr Ratio Observation

计算：

Lm/Lr

第一版本只生成INFO。

除非项目配置了企业内部限值，否则不得使用固定范围直接判定PASS/FAIL。

---

## R009 Characteristic Impedance

计算：

Zr

输出INFO。

---

## R010 Output Power Consistency

如果：

Iout存在

比较：

Vout × Iout

与：

Pout

允许误差由Project Settings配置。

---

## R011 MOSFET Static Voltage Screening

需要：

MOSFET VDS Rating
Vin Max

如果：

Rating <= Vin Max

CRITICAL

如果：

Rating > Vin Max

只能输出：

“Static screening passed.”

禁止输出：

“MOSFET voltage design is safe.”

因为尚未考虑：

* overshoot
* parasitic inductance
* ringing
* transient conditions

---

## R012 MOSFET Measured Peak Voltage

如果存在实测：

VDS Peak

比较：

VDS Peak

与：

Absolute Maximum VDS

超过：

CRITICAL

裕量阈值必须来自项目配置，不得硬编码通用标准。

---

## R013 MOSFET Current Screening

如果有：

Measured Peak Current
Device Current Rating
Temperature Condition

进行比较。

测试条件不足：

INSUFFICIENT_DATA

不得只根据datasheet首页额定电流判定安全。

---

## R014 Resonant Capacitor Voltage Rating

需要：

Capacitor Voltage Rating
Measured or Calculated Stress

缺失stress：

INSUFFICIENT_DATA

---

## R015 Resonant Capacitor RMS Current

需要：

Capacitor RMS Rating
Calculated/Measured RMS Current

比较并输出。

---

## R016 Controller Frequency Capability

如果提供控制器数据：

Controller Fmin
Controller Fmax

必须覆盖项目要求的：

Fsw Min → Fsw Max

---

## R017 Dead-Time Information

如果计划执行ZVS分析而缺少dead-time：

INSUFFICIENT_DATA

---

## R018 Transformer Ratio Required

执行完整增益检查前：

transformer_ratio

必须存在。

否则：

INSUFFICIENT_DATA

---

## R019 Gain Review Prerequisite

检查完整增益计算需要的数据是否齐全。

缺失时：

禁止模型自行补值。

---

## R020 Evidence Completeness

所有：

WARNING
CRITICAL

必须至少有一个：

* calculation
* user input
* datasheet
* waveform
* rule definition

作为evidence。

否则：

该Finding不得进入正式报告。

---

# 14. Phase 3：Project 与 Review API

实现：

## POST /projects

创建项目。

---

## GET /projects/{id}

读取项目。

---

## PATCH /projects/{id}

修改项目。

---

## POST /projects/{id}/calculate

运行LLC基础计算。

---

## POST /projects/{id}/review

执行规则引擎。

---

## GET /projects/{id}/review

返回最近一次Review结果。

---

# 15. Review API返回格式

```json
{
  "project_id": "xxx",

  "summary": {
    "pass": 10,
    "info": 3,
    "warning": 4,
    "critical": 0,
    "insufficient_data": 3
  },

  "findings": []
}
```

---

# 16. Phase 3：前端MVP

第一版只实现：

## Page 1

Project List

---

## Page 2

Project Editor

包括：

### Basic

Vin Min
Vin Nom
Vin Max

Vout
Pout
Efficiency

### Resonant Tank

Lr
Lm
Cr

### Frequency

Fsw Min
Fsw Nom
Fsw Max

### Transformer

Turns Ratio

### Primary Switch

Manufacturer
Part Number
VDS Rating

---

# 17. Phase 3：Design Review Page

页面顶部：

```text
DESIGN REVIEW

PASS                 10
INFO                  3
WARNING               4
CRITICAL              0
INSUFFICIENT DATA     3
```

下面按分类：

```text
Resonant Tank

Primary Switch

Transformer

Control

Protection

Thermal

Missing Information
```

每一个Finding必须可以展开。

显示：

```text
Title

Severity

Why

Input Data

Calculated Data

Evidence

Missing Information

Recommended Next Step
```

---

# 18. Phase 4：HTML Design Review Report

实现：

```text
Generate Review Report
```

Phase 4使用：

HTML

随后增加PDF。

报告包含：

1. Project Information
2. Design Specifications
3. Calculated Parameters
4. Review Summary
5. Critical Findings
6. Warnings
7. Missing Information
8. Passed Checks
9. Engineering Disclaimer
10. Calculation Version

---

# 19. 第一个可用 Demo 验收标准（Phase 0–4）

第一个可用 Demo 必须同时满足：

* Backend运行成功。
* Frontend运行成功。
* 可以创建Project。
* 可以保存Project。
* 可以运行六项基础计算。
* 有至少20条规则。
* Rule Engine不存在LLM依赖。
* 可以运行Review。
* 可以在网页查看Review。
* 可以生成HTML报告。
* pytest全部通过。
* 无Critical lint/type errors。
* examples中存在一个500 W示例项目。

否则不得进入 Phase 5。

---

# 20. Phase 5：Waveform Analysis MVP

完成 Phase 0–4 的 Design Review MVP 以后再开始。

Phase 5目标：

> 建立可验证的波形加载、校验、分段与基础特征计算能力。

ZVS Check 属于 Phase 6，不得在 Phase 5 提前实现。

禁止同时开发万能故障诊断。

---

# 21. Waveform输入格式

第一版要求：

CSV

必须支持：

```text
time
VGS_Q1
VDS_Q1
IRES
```

可选：

```text
VGS_Q2
VDS_Q2
VBUS
VOUT
```

用户需要提供：

```text
sample_rate
probe_ratio
channel_unit
channel_polarity
test_condition
```

---

# 22. Phase 5–6 Waveform Pipeline

Phase 5：

```text
CSV
 ↓
schema detection
 ↓
unit normalization
 ↓
NaN / invalid sample handling
 ↓
edge detection
 ↓
switching cycle segmentation
 ↓
frequency measurement
 ↓
peak / RMS calculation
```

Phase 6在上述结果之上扩展：

```text
dead-time estimation
 ↓
channel alignment
 ↓
VDS at turn-on
 ↓
ZVS feature extraction
 ↓
ZVS report
```

---

# 23. Waveform Engine

创建：

```text
backend/app/waveform/
```

Phase 5包含：

```text
loader.py
preprocessing.py
edges.py
cycles.py
features.py
```

Phase 6再增加：

```text
zvs.py
```

---

# 24. 第一批波形功能

实现：

```text
detect_rising_edges()

detect_falling_edges()

calculate_switching_frequency()

segment_cycles()

calculate_peak()

calculate_rms()
```

---

# 25. Phase 6：ZVS Analyzer

Phase 6新增：

```text
calculate_dead_time()

calculate_vds_at_gate_turn_on()
```

输入：

```text
VGS
VDS
IRES
time
```

输出：

```json
{
  "switching_frequency": {},
  "dead_time": {},
  "vds_at_turn_on": {},
  "zvs_status": "",
  "confidence": 0,
  "evidence_cycles": [],
  "limitations": []
}
```

第一版状态：

```text
LIKELY_ZVS
PARTIAL_ZVS
LIKELY_HARD_SWITCHING
INSUFFICIENT_DATA
```

禁止表述为绝对结论。

---

# 26. Phase 6：ZVS 波形可视化

前端必须展示：

* VGS
* VDS
* IRES

并标注：

* Gate turn-on
* Gate turn-off
* Dead time
* VDS at turn-on
* selected switching cycle

---

# 27. Phase 5–6 验收标准

## 27.1 Phase 5 Waveform Engine

必须：

* 上传CSV；
* 自动解析；
* 自动检测开关周期；
* 计算频率；
* 计算Peak与RMS；
* 使用synthetic waveform编写自动测试；
* 不依赖LLM。

## 27.2 Phase 6 ZVS Check

必须：

* 计算dead time；
* 计算VDS at turn-on；
* 页面显示标注波形；
* 输出ZVS判断；
* 使用synthetic waveform编写自动测试；
* 不依赖LLM。

---

# 28. Phase 7：器件数据手册

随后增加：

PDF Datasheet Parser。

MVP只支持：

MOSFET。

第一批提取：

```text
VDS
ID
Rds(on)
Qg
Coss
Eoss
RthJC
Tj Max
Package
```

但所有参数必须保留：

```text
test condition
value type
source page
confidence
human verified
```

---

# 29. Datasheet Workflow

```text
Upload PDF
 ↓
identify manufacturer
 ↓
identify part number
 ↓
extract candidate parameters
 ↓
normalize units
 ↓
store test conditions
 ↓
show extracted values
 ↓
human verification
 ↓
verified parameter database
```

未经Human Verified的数据不得用于：

CRITICAL安全结论。

---

# 30. Future Extension：BOM（暂不占用 Phase 编号）

BOM 不属于当前 Phase 0–10 的必做开发顺序。只有收到单独明确授权后才实施；不得插入或替代 Phase 7–10。

支持：

CSV / XLSX

字段：

```text
Reference
Manufacturer
Part Number
Description
Quantity
```

系统：

```text
BOM
 ↓
component identification
 ↓
datasheet matching
 ↓
parameter availability
 ↓
review readiness
```

---

# 31. Phase 8：故障案例库

FaultCase：

```text
case_id

topology

power

vin

vout

load

symptom

observed_features

root_cause

verification_steps

fix

waveform_before

waveform_after

engineer_verified
```

只有：

```text
engineer_verified = true
```

的案例能够进入正式诊断证据。

---

# 32. 第一批故障类型

建立：

```text
ZVS lost

MOSFET overheating

VDS overshoot

excessive resonant current

startup failure

output undervoltage

output oscillation

transformer saturation suspected

protection false triggering

light-load instability
```

---

# 33. Phase 9：故障诊断引擎

诊断不能直接：

```text
symptom → LLM answer
```

必须：

```text
symptom
 ↓
available evidence
 ↓
waveform features
 ↓
design parameters
 ↓
rule findings
 ↓
similar verified fault cases
 ↓
candidate causes
 ↓
evidence ranking
 ↓
recommended next measurement
```

---

# 34. Fault Diagnosis输出

```json
{
  "symptom": "",

  "candidate_causes": [
    {
      "cause": "",
      "confidence": 0.0,

      "supporting_evidence": [],

      "contradicting_evidence": [],

      "missing_information": [],

      "next_measurement": [],

      "recommended_action": []
    }
  ]
}
```

必须输出：

Top 3候选根因。

禁止只输出一个确定答案。

---

# 35. Phase 10：LLM接入

只有此前所有核心引擎完成以后，才能加入LLM。

LLM只充当：

```text
Engineering Orchestrator
```

---

# 36. LLM Tools

实现工具接口：

```text
get_project()

calculate_resonant_tank()

run_design_review()

get_component_parameter()

analyze_waveform()

run_zvs_check()

find_similar_fault_cases()

search_engineering_evidence()

generate_review_report()
```

---

# 37. LLM强制规则

LLM必须：

1. 工程计算调用工具。
2. 参数读取调用数据库。
3. 数据不足时明确说明。
4. 不得自行猜测datasheet数值。
5. 不能混用Typical和Maximum。
6. 单位必须显示。
7. 不允许把仿真称为实测。
8. 不允许把估算称为测量。
9. Critical结论必须有Evidence。
10. 安全相关建议要求Engineer Confirmation。

---

# 38. LLM输出原则

禁止：

> “这个650V MOSFET完全可以使用。”

允许：

> “当前静态检查显示650 V额定值高于420 V最大母线电压，但尚缺少实测VDS尖峰、温度和动态工况数据，因此不能完成完整耐压裕量判断。”

---

# 39. Cross-Phase：Evaluation

Evaluation 是贯穿各 Phase 的质量门禁，不占用 Phase 8。每个功能 Phase 都必须增加与其风险相称的测试；本节指标需在单独授权的 Evaluation Task 中统一审计。

建立：

```text
datasets/evaluation/
```

---

# 40. Calculation Tests

每一个公式至少：

* 正常输入；
* 边界输入；
* 无效输入；
* 单位测试。

---

# 41. Rule Tests

至少：

```text
20 normal cases

20 single-fault cases

10 multi-fault cases

10 missing-data cases

10 invalid-input cases
```

---

# 42. Waveform Tests

使用合成波形构造：

```text
clean ZVS

partial ZVS

hard switching

ringing

noise

missing channel

wrong unit

irregular sampling
```

测试算法。

---

# 43. Fault Diagnosis Evaluation

统计：

```text
Top-1 root cause accuracy

Top-3 root cause recall

evidence correctness

unsafe recommendation count

unsupported conclusion count
```

---

# 44. MVP指标

内部目标：

Critical rule recall：

> = 95%

Evidence correctness：

> = 95%

Known fault Top-3 recall：

> = 80%

Unsupported safety conclusion：

0

以上属于项目目标，不代表行业认证指标。

---

# 45. Cross-Phase：安全策略

Safety Policy 从 Phase 0 起持续生效，不占用 Phase 9，也不得推迟到某个后续 Phase 才执行。

增加：

```text
SafetyPolicy
```

禁止系统建议：

* 带电修改电路；
* 取消保护；
* 短接保护；
* 使用不符合额定值的测量设备；
* 普通接地探头直接测量高侧危险节点；
* 自动降低OCP/OVP/OTP；
* 未经验证直接进行高能量测试。

涉及高压测试时统一输出：

```text
Requires qualified engineer review.
```

---

# 46. Future Extension：Deployment（暂不占用 Phase 编号）

Deployment 不属于当前 Phase 0–10 核心能力顺序，必须在 Phase 10 之后或收到单独明确授权时实施。

开发：

Docker Compose。

服务：

```text
frontend
backend
postgres
```

开发环境：

```text
docker compose up
```

必须提供：

```text
.env.example
```

禁止提交：

```text
.env
API keys
customer datasheets
proprietary waveform data
```

---

# 47. Git Workflow

每个Phase单独提交。

命名示例：

```text
feat(engine): implement LLC core calculations

feat(rules): add initial design review rules

feat(api): expose project review endpoints

feat(ui): add design review dashboard

feat(waveform): implement switching edge detection

feat(zvs): add ZVS analysis pipeline

test(engine): add calculation validation cases
```

禁止：

一个commit修改整个项目。

---

# 48. Codex工作模式

Codex每次只处理一个明确阶段。

每阶段必须按照：

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
COMMIT READY
```

---

# 49. Codex每次任务完成后必须报告

```text
1. What changed

2. Files changed

3. Tests added

4. Tests executed

5. Test results

6. Known limitations

7. Engineering assumptions introduced

8. Documentation updated

9. Recommended next task
```

---

# 50. 禁止Codex未经允许推进下一Phase

例如：

Phase 1完成以后停止。

不要自动：

* 接LLM；
* 做RAG；
* 做Datasheet AI；
* 加复杂Agent；
* 加用户系统；
* 加支付；
* 加云部署。

---

# 51. Codex Phase 0 Prompt

首先给Codex：

“Read AGENTS.md and docs/MASTER_WORKFLOW.md.

We are starting Phase 0 only.

Inspect the repository and create the initial project skeleton required by the master workflow.

Do not implement LLC engineering calculations yet.

Tasks:

1. Create the backend and frontend directory structure.
2. Configure Python backend dependencies.
3. Configure FastAPI.
4. Configure pytest.
5. Configure React + TypeScript + Vite frontend.
6. Add basic health endpoint.
7. Add README development instructions.
8. Add .gitignore.
9. Add environment example.
10. Verify both backend and frontend can run.

Before editing, provide a concise implementation plan.

After implementation, run all available tests and builds.

Do not begin Phase 1.

Finish with:

* files changed
* commands executed
* test/build results
* known issues.”

---

# 52. Phase 1 Prompt

Phase 0通过以后：

“Read AGENTS.md and docs/MASTER_WORKFLOW.md.

Implement Phase 1: LLC Core Engineering Engine.

Do not implement LLM functionality.

Implement:

* project schemas
* unit handling
* calculate_fr
* calculate_fp
* calculate_zr
* calculate_lm_lr_ratio
* calculate_output_current
* calculate_input_power

Requirements:

* use deterministic Python functions
* explicit SI units internally
* typed inputs and outputs
* formula version attached to every calculation
* comprehensive pytest coverage
* invalid input handling
* no hard-coded undocumented engineering assumptions

Update DOMAIN_ASSUMPTIONS.md with every engineering definition introduced.

Stop when Phase 1 core calculations are complete.

Run tests and report results.”

---

# 53. Phase 2 Prompt

“Implement the initial LLC Design Review Rule Engine.

Use the rule definitions in MASTER_WORKFLOW.md.

Implement R001–R020.

Requirements:

* deterministic execution
* no LLM
* standardized Finding schema
* PASS / INFO / WARNING / CRITICAL / INSUFFICIENT_DATA
* evidence support
* configurable engineering margins
* no universal hard-coded safety margin unless explicitly documented

Write unit tests for every rule.

Create at least:

* normal project fixture
* incomplete project fixture
* invalid project fixture

Update RULES.md.

Run all tests.

Do not start waveform analysis.”

---

# 54. Phase 3 Prompt

“Implement project and design review REST APIs and the first frontend workflow.

User workflow:

Create Project
→ Enter LLC parameters
→ Save
→ Run Review
→ View Summary
→ Inspect Findings

Implement only this workflow.

Do not add AI chat.

Do not add authentication.

Do not add waveform analysis.

Create an example 500 W / 48 V LLC project.

Add API and frontend tests where practical.

Run backend tests and frontend build.

Stop after successful verification.”

---

# 55. Phase 4 Prompt

“Implement HTML Design Review Report generation.

Report must use the exact structured review results produced by the rule engine.

The reporting layer must not redo engineering calculations.

Include:

* project specification
* calculation results
* summary
* critical findings
* warnings
* insufficient data
* passed checks
* evidence
* calculation versions
* engineering disclaimer

Add tests.

Do not implement PDF yet.”

---

# 56. Phase 5 Prompt

“Implement Waveform Analysis MVP.

First supported format:
CSV with time, VGS_Q1, VDS_Q1, IRES.

Implement:

* CSV loader
* schema validation
* unit metadata
* rising edge detection
* falling edge detection
* cycle segmentation
* switching frequency measurement
* peak calculation
* RMS calculation

Use synthetic waveform fixtures.

Do not implement machine learning.

Do not implement general fault diagnosis.

Add numerical tests.”

---

# 57. Phase 6 Prompt

“Implement ZVS Check.

Use VGS_Q1, VDS_Q1, IRES and time.

Determine:

* switching frequency
* gate turn-on timestamps
* VDS at gate turn-on
* dead-time information where available
* evidence cycles

Output only:

LIKELY_ZVS
PARTIAL_ZVS
LIKELY_HARD_SWITCHING
INSUFFICIENT_DATA

Avoid absolute safety claims.

Expose analysis through API and frontend waveform visualization.

Add synthetic tests for each classification.”

---

# 58. Phase 7 Prompt

“Implement MOSFET datasheet ingestion infrastructure.

Do not attempt universal perfect PDF extraction.

First scope:
MOSFET only.

Target fields:

VDS
ID
Rds(on)
Qg
Coss
Eoss
RthJC
Tj Max
Package

Every extracted parameter must include:

value
unit
value type
test condition
source page
confidence
human_verified

Unverified extracted parameters must not be used for CRITICAL safety conclusions.

Implement a human verification workflow.

Add tests.”

---

# 59. Phase 8 Prompt

“Implement structured fault case storage and retrieval.

Do not add LLM diagnosis yet.

Implement FaultCase schema.

Allow cases to contain:

symptom
operating condition
observed features
verified root cause
verification procedure
repair action
before waveform
after waveform
engineer_verified

Only engineer_verified cases are eligible for production diagnostic evidence.

Implement CRUD and similarity/filter infrastructure.”

---

# 60. Phase 9 Prompt

“Implement deterministic fault diagnosis orchestration.

Input:

symptom
project design parameters
review findings
waveform features
verified fault cases

Output:

Top 3 candidate causes.

Each candidate must contain:

supporting evidence
contradicting evidence
missing information
recommended next measurement
recommended action

Do not use an LLM yet.

Implement test cases with known root causes.”

---

# 61. Phase 10 Prompt

“Integrate the LLM as an engineering orchestration layer.

The LLM must never replace deterministic engineering calculations.

Expose tools:

get_project
calculate_resonant_tank
run_design_review
get_component_parameter
analyze_waveform
run_zvs_check
find_similar_fault_cases
search_engineering_evidence
generate_review_report

Require structured outputs.

Prevent unsupported safety conclusions.

Add evaluation tests for hallucinated parameters, missing evidence and unit mistakes.”

---

# 62. Phase 0–10 权威开发顺序

本节是本文唯一的 Phase 编号依据。严格按照：

```text
Phase 0
项目骨架

↓

Phase 1
LLC确定性计算

↓

Phase 2
20条Review规则

↓

Phase 3
API + UI

↓

Phase 4
Design Review Report

=================
第一个可用Demo
=================

↓

Phase 5
Waveform Engine

↓

Phase 6
ZVS Check

=================
第二个可用Demo
=================

↓

Phase 7
Datasheet

↓

Phase 8
Fault Cases

↓

Phase 9
Fault Diagnosis

↓

Phase 10
LLM / Agent
```

以下内容不占用 Phase 编号，必须单独授权：

```text
BOM
Unified Evaluation Audit
Deployment
PDF Report
```

Safety Policy 是所有 Phase 的横切约束，不是一个等待后续实现的独立 Phase。

---

# 63. 第一个里程碑（Phase 0–4）

必须首先实现：

> LLC Design Review MVP

用户：

输入：

```text
Vin
Vout
Pout
Lr
Lm
Cr
Fmin
Fmax
MOSFET
```

系统输出：

```text
LLC Design Review

PASS                X

WARNING             X

CRITICAL            X

INSUFFICIENT DATA   X
```

这是第一个可以让真实工程师使用的产品。

---

# 64. 第二个里程碑（Phase 5–6）

增加：

> ZVS Analysis

用户：

```text
上传CSV
```

系统：

```text
识别开关周期
↓
标记VGS
↓
标记VDS
↓
计算dead time
↓
检测VDS at turn-on
↓
输出ZVS分析
```

---

# 65. 第三个里程碑（Phase 7–10 + 经授权扩展）

增加：

在 Phase 7–10 完成后，可按明确授权加入 BOM 等 Future Extension。

```text
BOM
+
Datasheet
+
Design Review
+
Waveform
+
Fault Cases
```

形成：

> LLC Engineering Copilot

---

# 66. 产品最终核心闭环

最终系统应实现：

```text
Design
  ↓
Review
  ↓
Simulation
  ↓
Prototype
  ↓
Measurement
  ↓
Waveform Analysis
  ↓
Fault Diagnosis
  ↓
Modification
  ↓
Verification
  ↓
Case Knowledge
  ↓
Next Project
```

每一个真实项目都会增加系统的工程知识。

这才是本项目长期的核心资产。
