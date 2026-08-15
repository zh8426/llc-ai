# LLC-AI Phase 0–4 代码审计整改清单

> 项目：`zh8426/llc-ai`  
> 审计基线：上次代码审计时 `main` 分支，最新提交约为 `46b8983fa7fbbba9a4237ae8df90f3934edef162`  
> 当前目标：**在进入 Phase 5（Waveform MVP）之前，完成 Phase 0–4 Hardening & Acceptance。**
>
> 本文档用于指导代码整改。建议一次只处理一个整改项，每个整改项完成后运行对应测试，再进入下一项。

---

## 0. 审计结论摘要

当前 Phase 0–4 的整体架构是合理的，核心设计质量较好：

- Backend：FastAPI + Pydantic + SQLAlchemy + Pint
- Frontend：React + TypeScript + Vite
- Phase 1：确定性 LLC 核心计算
- Phase 2：R001–R020 Rule Engine
- Phase 3：Project Design Review Web Workflow
- Phase 4：HTML Design Review Report
- Engineering Engine / Rule Engine 与 FastAPI、SQLAlchemy、Frontend、网络和 LLM 基本解耦
- 单位边界、规则证据约束、Review Snapshot、Report 不重新计算等设计值得保留

但目前仍然**不建议直接进入 Phase 5**。

主要原因不是现有 Phase 0–4 功能明显错误，而是：

1. 缺少可重复执行的质量门禁；
2. 数据库没有 migration 机制；
3. Calculation / Review / Report 尚未形成统一的 Calculation Snapshot；
4. `excluded_findings` 没有持久化；
5. 测量证据的数据模型不足以支撑后续 Waveform / ZVS；
6. Review 历史记录虽然已保存，但 API 只能方便读取 latest；
7. Frontend 还有少量和 MASTER_WORKFLOW 不一致的展示问题。

---


# 0.1 产品汉化与简化目标

本项目最终面向国内电源研发、电力电子和硬件工程师，因此从 Phase 0–4 Hardening 开始，应同步建立统一的中文产品语言规范。

这里的“汉化”不是把所有代码都改成中文，而是：

> **用户看到的内容尽量使用清晰、简洁、工程化的中文；程序内部代码仍保持标准英文命名。**

这样可以同时满足：

- 国内工程师使用门槛更低；
- 页面不需要大量理解软件开发术语；
- 报告更适合直接在团队内部流转；
- 后续开发人员仍然可以按照 Python / TypeScript / FastAPI / SQLAlchemy 的常规习惯维护代码；
- 不因为中文变量名、中文 API 字段等做法增加后续维护成本。

---

## 0.1.1 汉化边界

### 应优先汉化的内容

以下内容属于用户可见层，应尽量使用中文：

- Frontend 页面标题
- 按钮名称
- 表单字段名称
- 参数说明
- 单位提示
- Review Summary
- Finding 标题
- Finding 描述
- Severity 中文名称
- Missing Information
- Recommended Next Step
- 用户可见错误信息
- HTML Report
- 示例项目说明
- README 中面向使用者的启动和使用说明
- 产品内 Help / Tooltip / Empty State / Warning 文案

### 不建议汉化的内容

以下内容建议继续保持英文：

- Python 变量名
- Python 函数名
- Python Class 名
- TypeScript 变量名
- TypeScript Interface / Type
- API 路径
- JSON Key
- 数据库表名
- 数据库字段名
- Rule ID
- Formula Version
- Git commit 中引用的技术标识
- 第三方框架、库和标准名称

例如：

```text
ProjectCreate
ReviewResult
EngineeringQuantity
MeasurementEvidence
CalculationSnapshot
```

继续保持英文。

但在前端和报告中可以显示为：

```text
项目创建信息
评审结果
工程量
测量证据
计算快照
```

---

## 0.1.2 不建议采用“中文代码变量名”

例如不要改成：

```python
项目名称 = ...
输入电压最大值 = ...
谐振电感 = ...
```

而继续使用：

```python
project_name
vin_max
lr
```

原因：

1. Python / TypeScript / SQLAlchemy / FastAPI 社区和文档都以英文命名为主；
2. Codex / IDE / 静态分析工具对标准英文代码结构支持更稳定；
3. 后续查找资料、报错和调用第三方库更方便；
4. 可以避免中文变量名和英文框架 API 混杂造成阅读负担；
5. 产品汉化和代码国际化可以相互独立。

因此建议采用：

```text
内部代码：英文
用户界面：中文
工程缩写：保留
```

---

## 0.1.3 工程术语的简化原则

项目面向工程师，不需要把所有术语翻译成过度口语化内容，但应避免让用户阅读软件开发术语。

推荐使用：

```text
Resonant Frequency
→ 谐振频率

Characteristic Impedance
→ 谐振腔特征阻抗

Inductance Ratio
→ 电感比 Lm/Lr

Input Power
→ 输入功率

Output Current
→ 输出电流

Design Review
→ 设计评审

Finding
→ 评审项 / 评审结论

Evidence
→ 依据

Calculated Data
→ 计算数据

Input Data
→ 输入数据

Missing Information
→ 缺失信息

Recommended Next Step
→ 建议下一步

Engineering Disclaimer
→ 工程说明 / 免责声明
```

不建议在产品界面直接展示：

```text
Finding
Evidence Gate
Snapshot
Persistence
Schema
```

这些属于软件开发术语。

如果用户不需要理解，不应直接暴露。

---

## 0.1.4 Severity 中文显示规范

内部代码继续使用：

```text
PASS
INFO
WARNING
CRITICAL
INSUFFICIENT_DATA
```

前端和报告统一显示：

| 内部值 | 中文显示 | 建议含义 |
|---|---|---|
| PASS | 通过 | 当前规则检查通过，但不等于整机安全 |
| INFO | 提示 | 提供工程参考信息，不作通过/失败判断 |
| WARNING | 警告 | 存在需要工程师进一步确认的问题 |
| CRITICAL | 严重 | 存在明确的严重风险或条件冲突 |
| INSUFFICIENT_DATA | 数据不足 | 当前信息不足，无法完成可靠判断 |

不要把：

```text
PASS
```

翻译成：

```text
安全
```

也不要把：

```text
INFO
```

翻译成：

```text
正常
```

避免造成过度安全承诺。

---

## 0.1.5 Rule ID 的显示方式

内部继续使用：

```text
LLC-R001
LLC-R002
...
LLC-R020
```

前端建议显示为：

```text
R001 输入电压范围检查
R002 输出规格完整性检查
...
```

也可以在普通用户视图中弱化 Rule ID：

```text
输入电压范围检查
```

在“详细信息”中再显示：

```text
规则编号：LLC-R001
```

这样既保留可追溯性，又不会让普通工程师感觉界面过于“程序化”。

---

## 0.1.6 Formula Version 的显示方式

内部：

```text
LLC-FR-V1
LLC-FP-V1
```

继续保留。

用户界面建议显示：

```text
计算版本：LLC-FR-V1
```

不要直接只显示：

```text
formula_version
```

如果空间足够，可增加：

```text
计算公式版本：LLC-FR-V1
```

这样工程师能理解这是用于追溯计算依据的版本号。

---

## 0.1.7 Frontend 页面语言建议

建议整体改成中文产品语言。

例如：

```text
Projects
→ 项目

Create Project
→ 新建项目

Save
→ 保存

Run Review
→ 开始评审

Latest Review
→ 最新评审

Generate Report
→ 查看评审报告

Design Specifications
→ 设计参数

Review Summary
→ 评审摘要

Critical Findings
→ 严重问题

Warnings
→ 警告项

Passed Checks
→ 已通过检查
```

工程缩写不需要强制翻译：

```text
Vin
Vout
Iout
Pout
Lr
Lm
Cr
Fsw
VDS
ZVS
```

这些对目标工程师本身就是常用语言。

推荐显示为：

```text
最大输入电压 Vin Max
输出电压 Vout
输出功率 Pout
谐振电感 Lr
励磁电感 Lm
谐振电容 Cr
开关频率 Fsw
MOSFET VDS 额定值
```

即：

> **中文名称 + 工程缩写**

比完全只保留英文或者完全只翻译中文都更适合工程师。

---

## 0.1.8 参数说明应更简单

不要只显示：

```text
Measured VDS Peak
```

建议改成：

```text
实测 VDS 峰值
```

并增加简单帮助文字：

```text
填写示波器测得的 MOSFET VDS 最大峰值。
当前阶段该数值视为用户输入数据，不代表系统已验证波形条件。
```

例如：

```text
Current Temperature Condition
```

建议显示：

```text
电流额定值温度条件
```

帮助说明：

```text
填写该电流额定值对应的数据手册温度条件，例如 Tc = 25°C。
```

这样可以显著降低工程师理解表单的成本。

---

## 0.1.9 Review Finding 推荐中文结构

每一个 Finding 推荐显示为：

```text
标题

状态：通过 / 提示 / 警告 / 严重 / 数据不足

为什么
<简短说明>

输入数据
<用户提供的数据>

计算数据
<系统确定性计算结果>

依据
<规则依据、公式版本、比较数据>

缺失信息
<当前缺少什么>

建议下一步
<工程师下一步应该测什么 / 查什么 / 确认什么>

规则编号
LLC-Rxxx
```

相比直接展示大量 JSON，更适合国内工程师。

普通视图应优先：

> **可读信息**

高级详情再显示：

```text
raw evidence
formula version
rule id
source type
```

---

## 0.1.10 错误信息汉化

用户可见 HTTP / Validation Error 不应直接出现大量英文框架报错。

例如：

```text
Project not found
```

建议显示：

```text
未找到该项目。
```

```text
No review has been run
```

建议显示：

```text
该项目尚未执行设计评审。
```

```text
name must not be blank
```

建议显示：

```text
项目名称不能为空。
```

但内部日志可以继续保留英文技术信息。

建议区分：

```text
User Message
中文、简洁、可操作

Developer Log
完整技术错误
```

---

## 0.1.11 HTML Report 汉化要求

当前 HTML Report 已经以中文报告为主要方向，后续继续统一：

```text
Project Information
→ 项目信息

Design Specifications
→ 设计参数

Calculated Parameters
→ 计算结果

Review Summary
→ 评审摘要

Critical Findings
→ 严重问题

Warnings
→ 警告项

Missing Information
→ 缺失信息

Passed Checks
→ 已通过检查

Engineering Disclaimer
→ 工程说明

Calculation Version
→ 计算版本
```

报告正文应避免软件开发术语。

例如不要写：

```text
This finding was generated from persisted ReviewFinding.
```

而应写：

```text
本结论基于本次评审保存的项目参数、计算结果和规则依据生成。
```

---

## 0.1.12 Documentation 汉化建议

建议将项目文档分为两类：

### 面向用户 / 工程师

优先中文：

```text
README.md
docs/USER_GUIDE.md
docs/ENGINEERING_GUIDE.md
docs/REPORT_GUIDE.md
```

### 面向开发者

可以中文为主，保留技术术语英文：

```text
docs/ARCHITECTURE.md
docs/MASTER_WORKFLOW.md
docs/DOMAIN_ASSUMPTIONS.md
AGENTS.md
```

推荐写法：

```text
计算快照（Calculation Snapshot）
测量证据（Measurement Evidence）
规则引擎（Rule Engine）
数据库迁移（Migration）
```

第一次出现时：

> 中文 + 英文

后续可以直接使用中文或缩写。

---

## 0.1.13 产品界面不建议暴露开发 Phase

当前页面如果显示：

```text
Phase 3
Phase 4
```

建议删除。

Phase 是：

> 内部开发路线。

对最终用户没有实际意义。

最终工程师看到的应该是：

```text
LLC 设计评审助手
```

而不是：

```text
LLC Assistant Phase 4
```

如果需要版本信息，可以显示：

```text
版本 0.1.0
```

开发 Phase 保留在：

```text
MASTER_WORKFLOW.md
Git commit
Issue / PR
```

即可。

---

## 0.1.14 推荐新增统一术语表

建议新建：

```text
docs/TERMINOLOGY_ZH.md
```

用于统一项目用词。

例如：

| Internal Term | 中文显示 |
|---|---|
| Project | 项目 |
| Design Review | 设计评审 |
| Review Summary | 评审摘要 |
| Finding | 评审项 |
| Evidence | 依据 |
| Input Data | 输入数据 |
| Calculated Data | 计算数据 |
| Missing Information | 缺失信息 |
| Recommended Next Step | 建议下一步 |
| Measurement Evidence | 测量证据 |
| Calculation Snapshot | 计算快照 |
| Project Snapshot | 项目快照 |
| Rule Engine | 规则引擎 |
| Engineering Disclaimer | 工程说明 |
| Source Type | 数据来源 |
| Human Verified | 人工确认 |

以后 Frontend、Report、README 和 Help Text 都以该表为准。

这样可以避免同一个词在不同页面被翻译成：

```text
Finding
→ 发现
→ 结论
→ 问题
→ 检查项
```

造成产品语言不统一。

---

## 0.1.15 汉化整改优先级

建议增加一项：

| 优先级 | 项目 | 是否阻塞国内工程师 Demo |
|---|---|---|
| P1 | 用户可见内容汉化与术语简化 | **是** |

它不一定阻塞技术上的 Phase 5，但如果项目准备给国内工程师实际试用，应当作为 Phase 0–4 Acceptance 的一部分完成。

---

## 0.1.16 汉化验收标准

### Frontend

- [ ] 页面主要标题全部中文
- [ ] 按钮全部中文
- [ ] 表单字段全部有中文名称
- [ ] 常用工程缩写保留
- [ ] 重要字段有简短帮助说明
- [ ] Finding 用户视图不直接展示大段原始 JSON
- [ ] Severity 统一中文显示
- [ ] 不把 PASS 翻译为“安全”
- [ ] 不展示开发 Phase 编号
- [ ] 错误提示为清晰中文

### Report

- [ ] 所有章节标题中文
- [ ] Finding 主要内容中文
- [ ] Rule ID / Formula Version 保留英文标识
- [ ] 工程免责声明中文
- [ ] 报告不出现无必要的软件开发术语

### Documentation

- [ ] README 主要使用说明中文
- [ ] 用户指南中文
- [ ] 架构文档可使用“中文 + 英文技术术语”
- [ ] 新建统一术语表 `docs/TERMINOLOGY_ZH.md`

### Internal Code

- [ ] Python / TypeScript 标识符继续使用英文
- [ ] API 路径保持英文
- [ ] JSON Key 保持英文
- [ ] Database schema 保持英文
- [ ] Rule ID 保持 `LLC-Rxxx`
- [ ] Formula Version 保持原格式

---

## 0.1.17 推荐单独交给 Codex 的汉化任务

建议不要把汉化和数据库、Calculation Snapshot 重构放在同一次任务中。

可以单独执行：

```text
Phase 0–4 Hardening – Chinese UX Localization
```

任务目标：

```text
将所有用户可见内容统一汉化并简化，
但不修改 API contract、数据库 schema、Rule ID、Formula Version、
Python/TypeScript 内部标识符和确定性工程逻辑。
```

允许修改：

```text
frontend/
backend/app/reports/
backend/app/api/ 中用户可见错误信息
README.md
docs/ 用户说明相关文件
```

不得修改：

```text
Engineering Formula
Rule Logic
Severity Internal Enum
API Path
JSON Key
Database Column
Rule ID
Formula Version
```

完成后应输出：

```text
1. 修改文件列表
2. 新增/修改的中文术语
3. 所有用户可见英文残留搜索结果
4. npm run build 结果
5. pytest 结果
```

建议 Codex 最后执行一次文本搜索：

```text
Projects
Create Project
Save
Run Review
Finding
Evidence
Missing Information
Recommended Next Step
Critical
Warning
Phase 3
Phase 4
Project not found
```

检查是否仍有不必要的用户可见英文残留。

---

# 1. 整改优先级

| 优先级 | 项目 | 是否阻塞 Phase 5 |
|---|---|---|
| P0 | 建立 Phase 0–4 Quality Gate | **是** |
| P1 | 引入 Alembic Migration | **是，建议在 Phase 5 前完成** |
| P1 | 建立统一 Calculation Snapshot | **是，强烈建议 Phase 5 前完成** |
| P1 | 持久化 `excluded_findings` | **是，涉及审计追溯** |
| P1 | Measurement Evidence 结构化 | **是，涉及 Phase 5/6 架构** |
| P2 | Review History API | 否，但建议 Phase 5 前完成 |
| P2 | R013 Current Rating 数据模型预留 | 否 |
| P3 | Frontend Finding 展示修正 | 否，但应在 Phase 0–4 验收前完成 |

---

# 2. P0：建立 Phase 0–4 Quality Gate

## 2.1 问题

当前项目虽然已经有较完整的 `pytest` 测试，但缺少一个统一、自动、可重复执行的工程质量门禁。

当前已知情况：

### Backend

`pyproject.toml` 已包含：

- `pytest`
- `pytest-cov`
- `httpx`

并配置了：

- `testpaths = backend/tests`
- `--strict-config`
- `--strict-markers`

但没有看到明确的：

- Ruff
- mypy / Pyright
- CI 中自动运行测试
- 前后端统一验收流程

### Frontend

`frontend/package.json` 当前主要包含：

```text
npm run dev
npm run build
npm run preview
```

`npm run build` 会执行 TypeScript build + Vite build，这是好的。

但没有：

- lint script
- frontend automated test
- GitHub Actions quality gate

## 2.2 为什么这是 P0

`MASTER_WORKFLOW.md` 对 Phase 0–4 Demo 验收已经明确要求：

- pytest 全部通过；
- 无 Critical lint/type errors；
- Frontend build 成功；
- Backend / Frontend 可运行；
- HTML Report 可生成；
- 20 条规则存在；
- Rule Engine 不依赖 LLM；
- 500 W Example Project 存在。

如果没有自动化 Quality Gate，就无法稳定证明这些条件持续成立。

## 2.3 建议修改

### Backend 增加 Ruff

在开发依赖中加入 Ruff，例如：

```text
ruff
```

增加命令：

```powershell
python -m ruff check backend
```

### Backend 增加 Type Checker

二选一即可：

```text
mypy
```

或：

```text
pyright
```

不要同时引入两个，避免早期维护成本过高。

建议优先：

```text
mypy
```

然后：

```powershell
python -m mypy backend/app
```

如果当前类型错误很多，可以先逐步收紧，不要一次性引入过重规则。

### Frontend 保留 Build Gate

至少执行：

```powershell
npm ci
npm run build
```

`npm run build` 已包含 TypeScript 编译，因此可以作为当前 Phase 的 frontend type/build gate。

### 增加 GitHub Actions

建议新建：

```text
.github/workflows/quality.yml
```

CI 至少执行：

#### Backend

```text
Python 3.12+
pip install -e ".[test]"
pytest
ruff check backend
mypy backend/app
```

#### Frontend

```text
Node 22.x
npm ci
npm run build
```

## 2.4 暂时不要做的事情

不要为了“看起来严格”随便设置一个 coverage threshold，例如：

```text
--cov-fail-under=90
```

除非先评估当前覆盖率并明确接受该阈值。

质量门禁应该先做到：

> 稳定、可重复、不会制造无意义阻塞。

## 2.5 验收标准

- [ ] `python -m pytest` 全部通过
- [ ] `python -m ruff check backend` 通过
- [ ] `python -m mypy backend/app` 或 Pyright 通过
- [ ] `npm ci` 通过
- [ ] `npm run build` 通过
- [ ] 页面主要用户可见内容已汉化
- [ ] 工程术语符合统一中文术语表
- [ ] 用户可见错误提示为中文
- [ ] 内部代码/API/JSON/数据库标识保持英文
- [ ] GitHub Actions 自动执行以上检查
- [ ] CI 失败时 PR / commit 能明显看到失败状态

---

# 3. P1：引入 Alembic Migration

## 3.1 当前实现

当前数据库初始化大致使用：

```python
Base.metadata.create_all(bind=engine)
```

默认数据库：

```text
sqlite:///./llc_assistant.sqlite3
```

这对于 Phase 0–4 开发阶段是可接受的。

但它不是 migration system。

## 3.2 问题

`create_all()` 的能力主要是：

> 如果表不存在，就创建表。

它不适合正式管理：

- 新增列；
- 修改列；
- 数据迁移；
- 索引变化；
- 表结构版本；
- 回滚；
- 多环境一致升级。

Phase 5 之后很可能会增加：

- waveform 记录；
- waveform metadata；
- measurement evidence；
- waveform channels；
- ZVS result；
- 后续 datasheet / diagnosis 数据。

此时继续依赖 `create_all()` 风险会快速增加。

## 3.3 建议方案

引入：

```text
Alembic
```

### 建议步骤

1. 安装 Alembic；
2. 初始化 migration 目录；
3. 以当前 Phase 0–4 schema 作为 baseline；
4. 创建第一版 migration：

```text
0001_phase0_4_baseline
```

5. 后续数据库结构修改只能通过 migration 推进。

## 3.4 对 `initialize_database()` 的处理

开发环境可以暂时保留兼容逻辑，但正式演进建议逐步改成：

```text
数据库 schema 版本
由 Alembic 管理
```

不要长期依赖：

```python
Base.metadata.create_all()
```

作为正式 schema evolution 方案。

## 3.5 验收标准

- [ ] 项目引入 Alembic
- [ ] 当前 schema 有 baseline migration
- [ ] 新空数据库可以通过 migration 完整创建
- [ ] 已有开发数据库可以升级
- [ ] 后续表结构修改不再仅依赖 `create_all()`

---

# 4. P1：统一 Calculation Snapshot

## 4.1 当前问题

目前三个路径之间的 Calculation 数据没有完全统一：

### `/calculate`

`services/calculations.py` 会执行 Phase 1 六项基础计算：

1. Resonant Frequency `fr`
2. Lower Resonant Frequency `fp`
3. Characteristic Impedance `Zr`
4. Inductance Ratio `Lm/Lr`
5. Output Current `Iout`
6. Input Power `Pin`

### Review

`services/reviews.py` 当前会：

- 构造 ReviewContext；
- 必要时通过 `Pout / Vout` 补算 `Iout`；
- 将部分 calculation 结果提供给 Rule Engine。

但没有完整统一复用 `/calculate` 的六项 Calculation Result。

例如：

- `Pin` 并没有明确成为 Review 的统一 calculation snapshot；
- `Iout` 可能在不同路径重新计算。

### Report

当前 Report 主要从：

```text
review.findings[*].calculated_values
```

提取计算结果。

Formula version 也主要通过 Finding Evidence 获取。

这意味着：

> Report 展示的是“被某条规则引用到的计算”，而不是完整的 Phase 1 calculation snapshot。

## 4.2 风险

如果继续这样扩展：

```text
/calculate
Review
Report
Waveform
Diagnosis
```

可能会逐渐形成不同计算路径。

最终出现：

```text
API 显示 fr = A
Review 使用 fr = B
Report 展示 fr = C
```

即使现在没有发生，也应该提前消除这种架构风险。

## 4.3 推荐目标架构

建议改成：

```text
Project
   ↓
Calculation Engine
   ↓
Calculation Snapshot
   ├── API /calculate
   ├── Rule Engine
   └── Report
```

也就是：

> 六项确定性计算只在统一入口执行一次，并形成结构化 Snapshot。

## 4.4 推荐数据结构

可以增加类似：

```text
CalculationSnapshot
```

内容包括：

```text
project_id
created_at / calculated_at
calculation_version / engine_version
calculations[]
missing_information[]
errors{}
```

其中：

```text
calculations[]
```

仍然使用当前 `CalculationResult`：

```text
name
value
unit
inputs
formula_version
```

## 4.5 Review 应怎样修改

运行 Review 时：

```text
Project
↓
run_calculations()
↓
CalculationSnapshot
↓
ReviewContext
↓
R001–R020
```

Rule 不应该自己重新计算同一基础公式。

如果 Rule 需要：

```text
fr
fp
Zr
Lm/Lr
Iout
Pin
```

应从 Snapshot 中读取。

## 4.6 Report 应怎样修改

Report 应读取 Review 当时持久化的：

```text
Project Snapshot
+
Calculation Snapshot
+
Review Findings
```

而不是从 Finding 中“拼出”计算表。

## 4.7 是否应该持久化

建议：

> **每次 Review 持久化 Calculation Snapshot。**

原因：

- Report 可重复；
- 历史 Review 可复现；
- Project 修改后，旧 Review Calculation 不变化；
- Phase 5 后可以继续添加 Waveform Analysis Snapshot；
- 为未来 Audit Trail 打基础。

## 4.8 验收标准

- [ ] 六项基础计算只有一个 canonical execution path
- [ ] `/calculate` 使用该统一路径
- [ ] Review 使用同一个 Calculation Snapshot
- [ ] Report 使用 Review 保存的 Calculation Snapshot
- [ ] Report 不重新调用 Engineering Engine
- [ ] Project 修改后旧 Review 的 Calculation 结果不变化
- [ ] `Pin`、`Iout` 等六项计算都能被完整追溯
- [ ] 每个 CalculationResult 保留 `formula_version`

---

# 5. P1：持久化 `excluded_findings`

## 5.1 当前规则设计

Rule Engine 中：

```text
R020 Evidence Completeness Gate
```

用于检查：

> WARNING / CRITICAL Finding 是否具备足够 Evidence。

如果不满足要求，则原 Finding 不应进入正式 Report。

当前结构中：

```text
ReviewResult
├── findings
└── excluded_findings
```

这种设计本身是合理的。

## 5.2 当前问题

`run_and_store_review()` 当前只持久化：

```python
for finding in result.findings:
```

也就是说：

```text
excluded_findings
```

没有完整写入数据库。

## 5.3 风险

假设未来某条 Rule 产生：

```text
WARNING
但 Evidence 不完整
```

R020 会把它隔离。

如果数据库只保存正式 findings：

> 原始 Finding 详细信息可能丢失。

之后只能看到：

```text
R020 说某条结论被隔离
```

却不能完整恢复：

- 原始 title；
- description；
- calculated values；
- evidence；
- missing information；
- recommended action。

这会损害：

> Audit Traceability。

## 5.4 推荐方案

数据库中：

> **保存所有 Finding。**

增加或使用：

```text
report_eligible
```

区分：

```text
正式 Finding：
report_eligible = true

R020 隔离 Finding：
report_eligible = false
```

Report Layer 只展示：

```text
report_eligible = true
```

但数据库仍然保留全部结果。

## 5.5 可进一步增加

如果需要更明确，可以增加：

```text
excluded_reason
excluded_by_rule_id
```

例如：

```text
excluded_by_rule_id = "LLC-R020"
```

但第一版不是必须。

## 5.6 验收标准

- [ ] `result.findings` 全部持久化
- [ ] `result.excluded_findings` 也全部持久化
- [ ] excluded finding 的 `report_eligible = false`
- [ ] Report 不展示 `report_eligible=false`
- [ ] API / Review History 可以查看 excluded finding
- [ ] 测试验证原始 excluded finding 不丢失

---

# 6. P1：建立结构化 Measurement Evidence

## 6.1 当前情况

当前 Component Rule 已经使用：

```text
measured_vds_peak
measured_peak_current
voltage_stress
rms_current_stress
```

例如：

- R012：Measured VDS Peak vs MOSFET VDS Rating
- R013：Measured Peak Current vs Current Rating
- R014 / R015：Resonant Capacitor Stress vs Rating

但当前这些字段本质上仍然主要是：

> 用户手工输入的 EngineeringQuantity。

现有 `DOMAIN_ASSUMPTIONS.md` 也明确说明：

- `measured_*` 是用户声明的数据；
- 不代表已经验证过的波形证据；
- 不代表 Probe / Bandwidth / Test Condition 已知；
- Phase 4 尚未实现 Waveform Engine。

这个边界是正确的，应继续保留。

## 6.2 Phase 5 后的问题

当 Waveform Engine 引入后：

```text
measured_vds_peak = 580 V
```

不能只知道这个数字。

工程上还需要知道：

```text
从哪条 waveform 得到？
哪个 Channel？
Probe 比例？
Probe 类型？
Sample Rate？
Bandwidth？
测试输入电压？
负载条件？
温度？
时间戳？
是否人工确认？
```

## 6.3 推荐新增统一结构

建议设计：

```text
MeasurementEvidence
```

最低可包含：

```text
value
unit
source_type
source_id / waveform_id
channel
test_condition
timestamp
human_verified
```

Phase 5 可逐步扩展：

```text
sample_rate
probe_ratio
probe_type
bandwidth
polarity
channel_unit
measurement_method
```

## 6.4 source_type 建议

例如：

```text
USER_INPUT
WAVEFORM_DERIVED
DATASHEET
CALCULATED
IMPORTED
```

不要让系统把：

```text
USER_INPUT
```

自动升级成：

```text
VERIFIED_WAVEFORM_EVIDENCE
```

## 6.5 后续 Rule 应怎样使用

R012–R015 以后不应该只拿一个 Float 比较。

应该能看到：

```text
value
+
provenance
+
test condition
+
verification state
```

即：

> **数字 + 来源 + 条件 + 可信度。**

## 6.6 验收标准

- [ ] 有统一 Measurement Evidence schema
- [ ] 用户手填值能标识为 user-provided
- [ ] Phase 5 waveform-derived value 可引用 waveform ID
- [ ] Rule 能区分 user input 和 verified waveform-derived value
- [ ] Evidence 可进入 Report
- [ ] 不因“有 measured 字段”就自动得出 verified safety conclusion

---

# 7. P2：Review History API

## 7.1 当前优点

当前数据库设计已经保存：

```text
ReviewRun
ReviewFinding
ReviewProjectSnapshot
```

并且每次 Review 都保存 Project Snapshot。

Report 读取 Snapshot，而不是读取当前 Project。

这一点非常好。

已有测试也验证：

> 修改 Project 后，旧 Review Report 不应变化。

## 7.2 当前问题

API 目前主要方便读取：

```text
最新一次 Review
```

例如：

```text
GET /projects/{project_id}/review
```

Report 也主要通过：

```text
/projects/{project_id}/report
```

访问 latest。

但数据库实际上已经具备历史 Review 数据。

## 7.3 建议新增 API

建议增加：

```text
GET /projects/{project_id}/reviews
```

用途：

> 列出该 Project 所有 ReviewRun。

建议增加：

```text
GET /reviews/{review_id}
```

用途：

> 获取指定历史 Review。

建议增加：

```text
GET /reviews/{review_id}/report
```

用途：

> 生成指定历史 Review 的 Report。

## 7.4 推荐返回信息

Review List 至少包括：

```text
review_id
created_at
summary
calculation_version / snapshot info
```

不用在 list API 中把所有 Findings 全部展开。

## 7.5 验收标准

- [ ] 可以列出一个 Project 的历史 Reviews
- [ ] 可以通过 review_id 读取任意历史 Review
- [ ] 可以通过 review_id 获取历史 Report
- [ ] 旧 Review 不受当前 Project 修改影响
- [ ] 不再只能依赖 latest Review

---

# 8. P2：R013 Current Rating 条件模型不足

## 8.1 当前行为

R013 当前逻辑总体是保守的：

- measured current > rating → CRITICAL
- measured current < rating → INFO，而不是 PASS
- 需要 `current_temperature_condition`
- 明确提示这不是完整 current-safety conclusion

这一点应保留。

## 8.2 问题

MOSFET / Switch Current Rating 实际依赖很多条件：

```text
Tc
Tj
VGS
pulse duration
continuous / pulsed
package limit
SOA
thermal condition
```

当前只有：

```text
current_rating
current_temperature_condition: str
```

这不足以表达真实 datasheet rating context。

## 8.3 当前阶段建议

Phase 4 不要过度设计。

现阶段继续：

> 维持 R013 为 INFO / CRITICAL 的保守逻辑。

不要把：

```text
measured current < datasheet current rating
```

升级成：

```text
PASS / SAFE
```

## 8.4 Phase 7 Datasheet 阶段再升级

后续 Datasheet Parser 可以引入类似：

```text
ComponentRating
```

包含：

```text
parameter
value
unit
rating_type
temperature_condition
pulse_duration
gate_voltage
source_page
source_table
source_text
```

## 8.5 验收标准

当前 Phase 0–4：

- [ ] R013 继续保持保守 INFO 语义
- [ ] 不输出“current is safe”之类结论
- [ ] 当前 warning / critical 逻辑有 Evidence

Phase 7 再进一步结构化。

---

# 9. P3：Frontend Finding 展示与 MASTER_WORKFLOW 不一致

## 9.1 MASTER_WORKFLOW 要求

Design Review Finding 展开后应明确展示：

1. Title
2. Severity
3. Why
4. Input Data
5. Calculated Data
6. Evidence
7. Missing Information
8. Recommended Next Step

## 9.2 当前 Frontend

当前 FindingCard 已经显示：

- Why
- Calculated Data
- Evidence
- Missing Information
- Recommended Next Step

但缺少明确的：

```text
Input Data
```

区域。

虽然部分 user input 可能存在 Evidence JSON 中，但这不满足 UI 信息结构上的明确要求。

## 9.3 建议修改

在 FindingCard 增加：

```text
Input Data
```

显式区块。

如果当前 Finding schema 没有单独 `input_data` 字段，有两种方案：

### 方案 A：短期

根据 Evidence 中 `user_input` 等结构提取展示。

### 方案 B：推荐

在 Finding schema 中明确引入结构化：

```text
input_data
```

让 Rule 输出时区分：

```text
Input Data
Calculated Data
Evidence
```

长期更清晰。

## 9.4 Stale Phase Label

Frontend 中还存在类似：

```text
Half-Bridge · Phase 3
```

的旧标识。

当前项目已经 Phase 4，应修正。

建议不要在产品 UI 写死 Phase 编号。

更适合：

```text
LLC Design Review
```

或者：

```text
Half-Bridge LLC Design Review
```

Phase 属于开发路线，不一定应该暴露给最终用户。

## 9.5 验收标准

- [ ] Finding 显式显示 Input Data
- [ ] Finding 显式显示 Calculated Data
- [ ] Finding 显式显示 Evidence
- [ ] Missing Information 独立显示
- [ ] Recommended Next Step 独立显示
- [ ] 删除 / 修正 stale `Phase 3` 标签

---

# 10. 当前值得保留的架构，不要在整改时破坏

以下部分是当前代码的优点。整改时应明确要求 Codex：

> **不要为了重构而重构。**

## 10.1 EngineeringQuantity / Unit Boundary

保留：

```text
API：
value + unit
↓
Pint dimensional validation
↓
SI scalar persistence
↓
API / Rule / Calculation 再重建 EngineeringQuantity
```

不要改成到处裸传 Float。

## 10.2 Phase 1 公式必须保持 Deterministic

当前六项公式：

```text
fr
fp
Zr
Lm/Lr
Iout
Pin
```

继续保持 deterministic pure engineering calculation，不引入 LLM。

每个 `CalculationResult` 继续保留：

```text
name
value
unit
inputs
formula_version
```

## 10.3 Rule Engine 不依赖 LLM

继续保持：

```text
R001–R020
```

为确定性规则。

禁止改成：

```text
把 Project 发给 GPT
→ GPT 判断 PASS/WARNING
```

## 10.4 不要随意增加“通用工程阈值”

保留：

- Lm/Lr 不强行设置 universal pass range；
- Output Power 使用 Project 配置 tolerance；
- VDS Margin 使用用户/项目配置 margin；
- Capacitor stress < rating 只给 INFO，不等同于 safety PASS。

## 10.5 保留 R020 Evidence Completeness Gate

整改目标是保存被 R020 排除的原始 Finding，而不是删除 R020。

## 10.6 Report 不能重新计算

继续保持：

```text
Report
只读取 persisted snapshot / findings
```

不要让 Report 调用 Engineering Engine 或 Rule Engine。

## 10.7 Project Snapshot 必须继续不可变

建议最终扩展成：

```text
Review Artifact
├── Project Snapshot
├── Calculation Snapshot
├── Findings
└── Evidence References
```

---

# 11. Phase 0–4 Hardening 推荐执行顺序

建议新建一个明确阶段：

```text
Phase 0–4 Hardening & Acceptance
```

不要直接开始 Phase 5。

## Step 1：Quality Tooling

完成：

- Ruff
- mypy / Pyright
- pytest
- frontend build
- GitHub Actions

验证：

```powershell
python -m pytest
python -m ruff check backend
python -m mypy backend/app

Set-Location frontend
npm ci
npm run build
```

## Step 2：Alembic Baseline

完成 migration infrastructure 和 Phase 0–4 baseline migration。

## Step 3：Calculation Snapshot

先设计 schema / model，再改：

```text
Calculation Service
Review Service
Report Service
API tests
Report tests
```

## Step 4：Persist excluded_findings

新增测试：

```text
unsupported warning
↓
excluded_findings
↓
DB 中仍存在
↓
report_eligible=false
↓
Report 中不显示
```

## Step 5：Measurement Evidence 基础模型

现在只建立最小通用结构，不提前实现完整 Waveform Phase。

## Step 6：Review History API

增加：

```text
/projects/{id}/reviews
/reviews/{review_id}
/reviews/{review_id}/report
```

## Step 7：Frontend Fix

修复 Input Data 和 stale Phase label。

## Step 8：最终 Phase 0–4 Acceptance

全部检查通过后，才能宣布：

```text
Phase 0–4 Design Review MVP accepted
```

然后开始 Phase 5。

---

# 12. Phase 0–4 最终验收 Checklist

## Backend

- [ ] Backend 可启动
- [ ] `/health` 正常
- [ ] create Project 正常
- [ ] get/list Project 正常
- [ ] PATCH Project 正常
- [ ] 六项基础计算正常
- [ ] Rule Engine R001–R020 全部存在
- [ ] Rule Engine 不依赖 LLM
- [ ] Review 可运行
- [ ] Review 可持久化
- [ ] Project Snapshot 可持久化
- [ ] Calculation Snapshot 可持久化
- [ ] excluded_findings 不丢失
- [ ] HTML Report 可生成
- [ ] Report 不重新计算
- [ ] Historical Review 可读取

## Quality

- [ ] pytest 全部通过
- [ ] Ruff 通过
- [ ] mypy / Pyright 通过
- [ ] GitHub Actions 通过
- [ ] 无 Critical lint/type errors

## Frontend

- [ ] Frontend 可启动
- [ ] Project List 正常
- [ ] Project Editor 正常
- [ ] Save 正常
- [ ] Run Review 正常
- [ ] Finding 显式显示 Input Data
- [ ] Finding 显示 Calculated Data
- [ ] Finding 显示 Evidence
- [ ] Missing Information 正常
- [ ] Recommended Next Step 正常
- [ ] `npm run build` 通过

## Example

- [ ] `examples/projects/500w_48v_llc.json` 存在
- [ ] Example 只作为 illustrative example
- [ ] 不声明该 Example 是 verified reference design

---

# 13. Phase 5 前的最终架构目标

```text
Project
   │
   ▼
Project Snapshot
   │
   ├───────────────┐
   │               │
   ▼               │
Calculation Engine │
   │               │
   ▼               │
Calculation Snapshot
   │
   ▼
ReviewContext
   │
   ▼
R001–R020
   │
   ▼
Review Findings
   │
   ├── report_eligible=true
   └── report_eligible=false
   │
   ▼
Persisted Review Artifact
   │
   ├── Project Snapshot
   ├── Calculation Snapshot
   ├── All Findings
   └── Evidence / Provenance
   │
   ├───────────────┐
   ▼               ▼
Frontend          HTML Report
```

Phase 5 Waveform Engine 再接入：

```text
Waveform Upload
↓
Waveform Metadata
↓
Signal Processing
↓
Measurement Evidence
↓
Rule Engine / ZVS Analysis
```

不要让 Waveform Engine 直接绕过现有 Review / Evidence / Snapshot 架构。

---

# 14. 给 Codex 的执行原则

每次只给 Codex 一个明确整改项。

推荐：

```text
现在只执行 Phase 0–4 Hardening Step 1：Quality Gate。
不要开始 Alembic、Calculation Snapshot、Waveform 或 Phase 5。
完成后运行全部相关测试并总结修改文件、测试结果和仍存在的问题。
```

这样：

- diff 更容易审查；
- 出问题容易定位；
- Codex 不容易跨 Phase 擅自扩展；
- 更符合当前 `MASTER_WORKFLOW` “一次只执行一个明确 Phase”的原则。

---

# 15. 建议 Codex 修改任务模板

```text
当前任务：
Phase 0–4 Hardening – Step X：<整改项名称>

目标：
<明确目标>

允许修改：
<相关目录 / 文件>

不得修改：
- 不进入 Phase 5
- 不增加 Waveform 功能
- 不增加 LLM / RAG
- 不改变现有确定性工程公式
- 不新增未经项目定义的 universal engineering thresholds
- 不让 Report Layer 重新计算
- 不删除 Review Project Snapshot
- 不降低 R020 Evidence Gate

必须完成：
1. <任务1>
2. <任务2>
3. <任务3>

测试：
- python -m pytest ...
- python -m ruff ...
- python -m mypy ...
- npm run build ...

完成后输出：
1. 修改文件列表
2. 核心设计说明
3. 测试命令与结果
4. 尚未解决的问题
5. 明确停止，不自动进入下一阶段
```

---

# 16. 上次审计的执行限制

上次审计属于：

> **GitHub Connector 静态代码审计。**

当时尝试 clone 仓库并实际运行测试时，执行环境出现：

```text
Could not resolve host: github.com
```

因此：

- 静态测试代码结构已经检查；
- 项目测试设计整体较强；
- 但当时没有在审计环境中实际证明 `pytest` / `npm run build` 全部执行通过。

所以本次整改完成后，必须在你的本机或 GitHub Actions 实际执行完整 Quality Gate。

---

# 17. 上次审计评分记录

| 项目 | 评价 |
|---|---|
| Architecture | A- |
| Deterministic Calculation | A |
| Unit Handling | A |
| Rule Engine | A- |
| Safety Philosophy | A |
| Tests Design | A- |
| API / Persistence | B+ |
| Report | B+ |
| Frontend | B |
| CI / Engineering | C+ |
| Phase 5 Readiness | 暂不放行 |

整改后的重点不是“提高分数”，而是做到：

> **Phase 0–4 能够被自动、重复、可追溯地证明满足自己的验收标准。**

---

# 18. 最终建议

当前最合适的推进顺序：

```text
Phase 0–4 功能开发
↓
Hardening
↓
Automated Quality Gate
↓
Acceptance
↓
Phase 5 Waveform MVP
```

优先级最高的第一项仍然是：

> **建立完整 Quality Gate。**

完成 Quality Gate 后，再进入 Alembic 和 Calculation Snapshot 重构。这样后续每次架构修改都有自动测试和 build gate 保护。
