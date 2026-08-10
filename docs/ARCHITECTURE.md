# Architecture

## 当前范围：Phase 1

当前系统包含两个可独立启动的应用，以及一个不依赖 Web 或 LLM 的确定性计算层：

```text
Frontend (React + TypeScript + Vite)

Backend (FastAPI + Pydantic)
  └── GET /health

Engineering Engine (pure Python + Pint)
  ├── resonant_tank.py
  ├── power.py
  ├── units.py
  └── structured CalculationResult
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

## 分层边界

`backend/app/` 下的目录按照 `MASTER_WORKFLOW.md` 分层。Phase 1 只启用 `engine` 和相应 `schemas`；`rules`、`waveform`、`datasheet`、`knowledge`、`reports` 和 `services` 仍为空占位。

后续实现必须保持 API、Domain Model、Engineering Engine、Rule Engine、Waveform Engine、Datasheet Parser、Persistence、Fault Diagnosis、LLM Orchestration、Reporting 和 Frontend 的职责分离。

## Phase 边界

Phase 1 只包含 `MASTER_WORKFLOW.md` 指定的六项 LLC 核心计算。不包含工程判定阈值、设计评审规则、增益模型、器件应力模型、波形算法、诊断逻辑或 LLM 集成。
