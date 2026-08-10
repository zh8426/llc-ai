# Architecture

## Phase 0 范围

当前系统仅包含两个可独立启动的应用：

```text
Frontend (React + TypeScript + Vite)

Backend (FastAPI + Pydantic)
  └── GET /health
```

SQLAlchemy 已作为 Backend 依赖配置，并提供空的 declarative base；Phase 0 不创建领域模型、数据库连接或迁移。

## 分层边界

`backend/app/` 下的目录按照 `MASTER_WORKFLOW.md` 预留。除 `api` 和 `schemas` 中的 health check 支撑代码外，其他目录在 Phase 0 均为空占位，不包含工程行为。

后续实现必须保持 API、Domain Model、Engineering Engine、Rule Engine、Waveform Engine、Datasheet Parser、Persistence、Fault Diagnosis、LLM Orchestration、Reporting 和 Frontend 的职责分离。

## Phase 边界

Phase 0 不包含任何 LLC 公式、阈值、规则、波形算法、诊断逻辑或 LLM 集成。
