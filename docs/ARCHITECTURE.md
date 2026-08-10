# Architecture

## 当前范围：Phase 2

当前系统包含两个可独立启动的应用，以及不依赖 Web 或 LLM 的确定性计算层与规则层：

```text
Frontend (React + TypeScript + Vite)

Backend (FastAPI + Pydantic)
  └── GET /health

Engineering Engine (pure Python + Pint)
  ├── resonant_tank.py
  ├── power.py
  ├── units.py
  └── structured CalculationResult

Rule Engine (pure Python)
  ├── ReviewContext
  ├── ReviewRule interface
  ├── built-in R001–R020
  ├── Evidence integrity gate
  └── ReviewResult + excluded_findings
```

SQLAlchemy 已作为 Backend 依赖配置，并提供空的 declarative base；Phase 1 仍不创建领域数据库模型、连接或迁移。

## Calculation Data Flow

```text
EngineeringQuantity(value + unit)
  → dimensional validation
  → SI normalization
  → deterministic formula
  → finite-result validation
  → CalculationResult(value + unit + SI inputs + formula version)
```

`backend/app/engine/` 不导入 FastAPI、SQLAlchemy、Frontend 或任何 LLM 依赖，因此能够离线独立运行和测试。

`backend/app/rules/` 只依赖 structured schemas 和 deterministic engineering functions。规则执行不访问数据库、网络、Frontend 或 LLM。

## Review Data Flow

```text
ReviewContext
  → R001–R019 deterministic evaluation
  → structured Findings
  → R020 Evidence Completeness Gate
  → eligible findings + excluded unsupported findings
  → ReviewSummary
```

Report Layer 尚未实现。未来报告只能消费 `eligible findings`，不得重新计算工程结果或恢复被 R020 隔离的 Finding。

## 分层边界

`backend/app/` 下的目录按照 `MASTER_WORKFLOW.md` 分层。Phase 2 启用 `engine`、`rules` 和相应 `schemas`；`waveform`、`datasheet`、`knowledge`、`reports` 和 `services` 仍为空占位。

后续实现必须保持 API、Domain Model、Engineering Engine、Rule Engine、Waveform Engine、Datasheet Parser、Persistence、Fault Diagnosis、LLM Orchestration、Reporting 和 Frontend 的职责分离。

## Phase 边界

Phase 2 只包含 `MASTER_WORKFLOW.md` 指定的 R001–R020。它不包含 Project CRUD/API、Frontend Review Workflow、HTML Report、增益模型、波形算法、ZVS 分类、诊断逻辑或 LLM 集成。
