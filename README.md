# LLC Engineering Assistant

面向专业电力电子工程师的 **Half-Bridge LLC Design Review & Troubleshooting Assistant**。

本项目的长期目标是把结构化工程数据、确定性计算、工程规则、实测波形和已验证故障案例组织成可追溯的研发辅助系统。LLM 只作为后期的编排与解释层，不替代工程计算、规则判断或工程师确认。

`docs/MASTER_WORKFLOW.md` 是开发范围与 Phase 顺序的主要依据；`AGENTS.md` 定义代码、测试、文档和安全约束。

## Product Scope

第一版产品范围：

- 拓扑：Half-Bridge LLC
- 功率：300–1000 W
- 输入：300–420 VDC
- 输出：24 V / 48 V
- 控制：Variable Frequency Control
- 主开关：Silicon MOSFET
- 整流：Diode Rectification

未经明确授权，不扩展到 Full-Bridge LLC、CLLC、双向、交错、多相或其他谐振拓扑。

## Engineering Principles

工程分析优先级：

```text
Deterministic Engineering Calculation
>
Engineering Rule
>
Measured Waveform Evidence
>
Verified Engineering Case
>
LLM Interpretation
```

核心原则：

- 可以由程序确定性计算的结果不得交给 LLM 猜测。
- 所有工程量必须显式携带单位，计算内部统一使用 SI。
- 计算结果必须结构化、可测试、可重复，并包含公式版本。
- WARNING / CRITICAL 必须有 Evidence。
- 缺少必要数据时返回 `INSUFFICIENT_DATA`，不得静默补值。
- 仿真、估算和测量必须明确区分。
- 系统是 Engineering Assistance Tool，不是 Safety Authority。

## Target Architecture

```text
User Input
  → Structured Engineering Data
  → Deterministic Calculation Engine
  → Engineering Rule Engine
  → Waveform Analysis Engine
  → Datasheet / Evidence Retrieval
  → Verified Fault Cases
  → Fault Diagnosis Orchestration
  → LLM Orchestration and Explanation
  → Structured Report
```

各层必须保持职责分离：

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

即使网络、LLM 或 AI Provider 不可用，确定性计算、设计评审、规则执行、波形分析和基础报告仍应能够独立运行。

## Development Roadmap

| Phase | 目标 | 主要交付物 |
| --- | --- | --- |
| Phase 0 | 项目骨架 | Python/FastAPI Backend、React/TypeScript/Vite Frontend、pytest、health check、基础文档 |
| Phase 1 | LLC 确定性核心计算 | Project Schema、单位处理、`fr`、`fp`、`Zr`、`Lm/Lr`、`Iout`、`Pin` |
| Phase 2 | Design Review Rule Engine | R001–R026、统一 Finding Schema、Evidence、Missing Information、配置化 Margin |
| Phase 3 | Review API 与 Frontend Workflow | Create Project、输入参数、保存、运行 Review、查看 Findings |
| Phase 4 | Design Review Report | 基于结构化结果生成 HTML Report，不重复工程计算 |
| Phase 5 | Waveform Engine | CSV、Schema、单位、边沿、周期、频率、Peak、RMS |
| Phase 6 | ZVS Check | Dead Time、VDS at Turn-On、Evidence Cycles、保守分类结果 |
| Phase 7 | Datasheet Infrastructure | MOSFET 参数提取、测试条件、来源页、Confidence、Human Verification |
| Phase 8 | Verified Fault Cases | 结构化 FaultCase、CRUD、筛选和相似案例基础设施 |
| Phase 9 | Deterministic Fault Diagnosis | Top 3 Candidate Causes、正反证据、缺失信息、下一步测量 |
| Phase 10 | LLM Orchestration | 工具调用、结构化输出、Evidence 约束和不安全结论防护 |

每次只执行一个明确 Phase。当前 Phase 完成并通过测试后停止，不自动开始下一阶段。

### Cross-Phase E1 状态

在 Phase 1–2 的确定性基础上，Cross-Phase E1 已按 E1-A → E1-G 逐步建立 FHA 增益分析：匝比约定、FHA 基础量、复阻抗与单点增益、感性/容性分类、Required Gain 与工作点求解、Operating Envelope 与 R021–R026，以及当前的增益曲线 API、中文前端展示和文档。E1-G 的曲线接口为 `POST /projects/{project_id}/gain-curve`，只读取已保存项目参数并返回带公式版本的结构化点结果。

Evaluation、Safety Policy 和 Deployment 必须按 `MASTER_WORKFLOW.md` 及明确任务单独推进，不得为了演示提前加入认证、支付、云部署或复杂 Agent。

## Technology Stack

Backend：

- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- Pint
- NumPy
- pypdf（Phase 7 PDF 文本提取）
- OpenAI Python SDK（Phase 10，可选 Provider）
- python-multipart
- pytest / pytest-cov
- Ruff
- mypy

Frontend：

- React
- TypeScript
- Vite

后续按 Phase 与实际算法需要引入 PostgreSQL、SciPy 和 pandas。

## Repository Layout

```text
backend/app/api/          REST API
backend/app/models/       Persistence models
backend/app/schemas/      Structured input/output schemas
backend/app/engine/       Deterministic engineering calculations
backend/app/waveform/     Deterministic waveform loading and signal features
backend/app/api/waveforms.py  CSV waveform upload and ZVS API
backend/app/rules/        Design review rules
backend/app/datasheet/    Datasheet ingestion
backend/app/knowledge/    Engineering evidence and fault knowledge
backend/app/reports/      Structured report generation
backend/app/services/     Application orchestration
backend/tests/            Backend automated tests
frontend/                 React application
docs/                     Architecture, assumptions, rules, API and safety
examples/                 Example projects and waveforms
datasets/                 Rules, fault cases and evaluation datasets
scripts/                  Development utilities
```

## Local Development

环境要求：

- Python 3.12 或更高版本
- Node.js 22.12 或更高版本
- npm 10 或更高版本

不要提交 `.env`、API key、客户数据手册或专有波形数据。

### Backend

在仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m alembic upgrade head
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

应用启动不会自动创建或修改数据库表。新建数据库或拉取包含新 migration 的代码后，应先执行：

```powershell
python -m alembic upgrade head
python -m alembic current --check-heads
```

#### 已有 Phase 0–4 SQLite 数据库

如果 `llc_assistant.sqlite3` 是旧版本通过 `create_all()` 创建的数据库，其中已经存在
`projects`、`review_runs`、`review_findings` 和 `review_project_snapshots` 四张表，不能直接对它执行首个 baseline 的建表操作。

先确认数据库确实来自提交 `81ee4d3` 或相同的 Phase 0–4 schema。确认来源和表结构后，按以下顺序执行：

```powershell
Copy-Item .\llc_assistant.sqlite3 .\llc_assistant.before-alembic.sqlite3
python -m alembic stamp 0001_phase0_4_baseline
python -m alembic upgrade head
python -m alembic current --check-heads
```

正常情况下，最后一条命令应显示：

```text
0002_calculation_snapshot (head)
```

`stamp` 只记录 schema 版本，不创建、删除或修改业务表；后续的 `upgrade head` 才会应用
`0002_calculation_snapshot` 等尚未执行的 migration。升级完成后，原有 Project、Review 及其数据应保留，
并新增 `review_calculation_snapshots` 表。

数据库来源不同，处理方式不同：

| 数据库情况 | 操作 |
| --- | --- |
| 全新数据库 | 直接执行 `python -m alembic upgrade head` |
| 已确认的旧 Phase 0–4 数据库 | 备份后执行 `stamp 0001_phase0_4_baseline`，再执行 `upgrade head` |
| 来源不明或表结构不一致 | 禁止直接 `stamp`；先人工核对或复制数据库后验证 |

不要对来源不明或结构不同的数据库执行 `stamp`，否则 Alembic 会把未知 schema 当作已知 baseline，可能掩盖真实迁移问题。

Health check：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Backend tests：

```powershell
python -m pytest
```

Backend 静态检查：

```powershell
python -m ruff check backend
python -m mypy backend/app
```

### Frontend

```powershell
Set-Location frontend
npm install
npm run dev
```

Production build 与 TypeScript 检查：

```powershell
npm run build
```

Vite 项目必须通过开发服务器访问，不能直接双击 `frontend/index.html`。

### Quality Gate

提交前应从干净安装环境执行完整质量门禁：

```powershell
# 仓库根目录
python -m pip install -e ".[test]"
python -m pytest
python -m ruff check backend
python -m mypy backend/app

# Frontend
Set-Location frontend
npm ci
npm run build
```

GitHub Actions 会在 push 和 pull request 时自动执行相同的后端与前端检查。

## Documentation

- `docs/MASTER_WORKFLOW.md`：产品规划、架构和 Phase 顺序
- `docs/ARCHITECTURE.md`：当前架构与模块边界
- `docs/DOMAIN_ASSUMPTIONS.md`：公式、适用条件、单位和工程假设
- `docs/RULES.md`：Design Review Rule 定义
- `docs/API.md`：REST API 契约
- `docs/SAFETY.md`：安全策略和禁止行为
- `docs/TERMINOLOGY_ZH.md`：用户界面与报告的中文产品术语

新增公式、规则、API、架构决策或安全策略时，必须同步对应文档。

## Testing Policy

- 每个工程公式至少覆盖正常、边界、无效、单位转换和缺失输入。
- 每条 Rule 至少覆盖触发、不触发、缺失数据和无效数据。
- Waveform Algorithm 必须使用 Synthetic Fixtures 验证噪声、采样、缺失 Channel 和数值稳定性。
- Backend Phase 完成前运行完整 `pytest`。
- Frontend 修改后至少运行 `npm run build`。
- 测试失败时不得声称 Task Complete，除非失败与当前任务无关且已记录原因。

自动化测试通过表示软件符合当前定义，不表示真实 LLC 硬件已经安全、合规或通过工程评审。

## Git Workflow

README 维护项目的长期规划和稳定使用说明，不记录每次开发改动，也不维护重复的手工 Changelog。

每次更新的具体内容通过 Git commit message 和 Git history 追踪。Commit、tag 和 push 由项目维护者手动执行；自动化助手不得在没有明确指令时自行提交或推送。

推荐每个 commit 只处理一个 Logical Task，并在提交前检查：

```powershell
git status
git diff
python -m pytest
python -m ruff check backend
python -m mypy backend/app
```

Frontend 有变更时额外执行：

```powershell
Set-Location frontend
npm run build
```

推荐 commit style：

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

## Safety Boundary

本项目涉及高压、高电流和高能量储能元件，可能存在致命危险。

系统不得：

- 绕过或关闭 OCP、OVP、OTP；
- 自动降低 Safety Limit；
- 直接控制 Converter PWM；
- 自动修改实时保护参数；
- 建议未经适当保护直接给实验硬件上电；
- 将估算或仿真结果称为实测；
- 在 Evidence 不足时声明设计安全、符合标准或可直接量产。

涉及高风险工程操作时必须要求 Engineer Confirmation，并在必要时明确提示：

```text
Requires qualified engineer review.
```
