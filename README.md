# LLC Engineering Assistant

面向专业电力电子工程师的半桥 LLC 设计与验证工作台。

**当前状态：V2 文档契约已建立，运行时代码仍为 V1。** 本次 T01 不新增计算功能、页面、API 或数据库迁移。下方本地启动与测试命令继续适用于现有 V1。

## V2 产品主线

首个可用版本 M1 的目标：**规格 → 候选谐振腔 → 多工况检查 → 方案比较 → 设计版本 → 计算书**。

数学与波形算法经验证后复用；产品流程、版本/工况数据模型和业务编排按新主线重建。目标、估算与实测分别保存，修改设计后保留旧报告并明确需要重新验证的结果。

| 文档 | 用途 |
|---|---|
| [V2 设计说明](docs/V2_DESIGN.md) | 数据模型、页面、模块边界、API 草案、迁移和验收 |
| [当前开发主线](docs/MASTER_WORKFLOW.md) | M0–M4、T01–T10、当前任务与下一项范围 |
| [Agent 规范](AGENTS.md) | 单位、证据、测试、范围和工作流程 |
| [工程假设](docs/DOMAIN_ASSUMPTIONS.md) | V1 实现与 V2 目标模型的定义和边界 |
| [V1 历史主线](docs/history/V1_MASTER_WORKFLOW.md) | 原 Phase 0–10，只作为历史参考 |

## Product Scope

现有 V1 定位：Half-Bridge LLC、300–1000 W、300–420 VDC、24 V / 48 V、变频控制、硅 MOSFET、二极管整流。

V2 M1 目标进一步固定为中心抽头二极管整流、单输出、理想稳态 FHA 与正负载，`n = Np / Ns_half`。这不自动改变 V1 参数含义；旧项目的副边连接不能由“Diode Rectification”反推。

全桥、CLLC、双向、交错、多相以及其他拓扑不在首版范围。磁件、器件/BOM、损耗热、控制、仿真、测试和设计发布按后续里程碑推进，不表示这些能力已经可用。

## Engineering Principles

- 确定性计算、规则与信号处理由程序执行，LLM 只调用工具并解释结果。
- 所有工程量显式携带单位，内部统一 SI；结果包含输入和公式/模型版本。
- WARNING / CRITICAL 必须有 Evidence，工程裕量有明确来源。
- 缺输入、模型不适用、功能未实现和检查失败分别表达，不静默补值。
- 分析、仿真、测量、参考和合成数据分开记录。
- 计算与实测冲突时检查工况、模型和测量不确定度，不按固定来源排序自动判真伪。
- 报告消费固定运行的结构化结果，不重新计算；系统不是 Safety Authority。
- 网络、LLM 或 AI Provider 不可用时，核心计算、评审、波形和报告仍能独立运行。

## Development Roadmap

| 里程碑 | 目标 | 当前状态 |
|---|---|---|
| M0 | 文档契约、版本、工况与搜索配置基础 | T01 文档交付；T02–T03 未实现 |
| M1 | 规格到候选方案与计算书 | T04–T10 未实现 |
| M2 | 应力、磁件、器件/BOM、损耗热与控制约束 | 规划 |
| M3 | 仿真、实测、偏差分析和问题复测 | 规划 |
| M4 | 发布包、生产测试与核验案例 | 规划 |

每次执行一个明确任务，完成后报告和停止。当前任务、依赖和验收以 [MASTER_WORKFLOW.md](docs/MASTER_WORKFLOW.md) 为准；旧 Phase 不再决定新开发顺序。

## Existing V1 Capabilities

现有程序提供项目参数与设计评审、HTML 报告、FHA 增益曲线、CSV 波形/ZVS 分析、MOSFET 手册候选、案例检索与受约束的 LLM 编排。具体运行时契约见 [API](docs/API.md) 和 [架构](docs/ARCHITECTURE.md)。

已有 Cross-Phase E1 包含匝比、复阻抗、工作区域、工作点求解及单一负载下的输入电压包络。`POST /projects/{project_id}/gain-curve` 读取已保存参数。它不等于 V2 的规格综合和多工况工作台。

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

后续按当前任务与实际算法需要引入其他依赖，不为文档重构提前更换技术栈。

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

Frontend 功能页面使用轻量级 History 路由并按页面懒加载：

- `/`：项目参数与设计评审
- `/gain-curve`：FHA 增益曲线
- `/waveform`：波形与 ZVS 分析
- `/datasheets`：数据手册候选

项目编辑页提供“删除项目”操作；删除前会要求确认，并由 Backend 级联清理该项目的评审历史。

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

- `docs/MASTER_WORKFLOW.md`：当前里程碑、任务依赖和验收
- `docs/V2_DESIGN.md`：V2 目标设计契约
- `docs/history/`：V1 历史主线，不定义当前执行顺序
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
- 涉及实现的功能里程碑完成前运行完整 `pytest`；纯文档变更检查结构、链接和陈述一致性。
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
