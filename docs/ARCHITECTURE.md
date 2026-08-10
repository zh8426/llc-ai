# Architecture

## 当前范围：Phase 3

Phase 3 形成第一个 Project Design Review Web Workflow：

```text
React Project List / Editor
  → FastAPI Project API
  → SQLAlchemy Project Persistence (SQLite development)
  → Application Services
      ├── Phase 1 deterministic calculations
      └── Phase 2 R001–R020 Rule Engine
  → structured ReviewRun + ReviewFinding persistence
  → Review Summary / expandable Findings UI
```

Backend 和 Frontend 仍可独立启动。Engineering Engine 与 Rule Engine 不依赖 FastAPI、SQLAlchemy、Frontend、网络或 LLM。

## Persistence

Phase 3 启用三张结构化表：

```text
projects
review_runs
review_findings
```

Project 核心电压、电流、功率、谐振腔、频率、变压器、控制器和第一版器件评审字段均使用独立列保存，不把 Project 整体保存为 JSON Blob。

Review Summary、rule id、category、severity、title、description 和 Engineer Confirmation 使用可查询列。Evidence、Calculated Values、Missing Information 与 Recommended Action 是 Finding 内部的嵌套结构，使用 JSON 列保存。

开发环境默认 SQLite，通过 `DATABASE_URL` 可配置其他 SQLAlchemy Database URL。当前使用启动时 `create_all` 初始化开发数据库，尚未引入正式 migration workflow。

## Unit Boundary

```text
API EngineeringQuantity(value + unit)
  → dimensional validation with Pint
  → SI scalar persistence
  → EngineeringQuantity reconstruction
  → Calculation / Rule Engine normalization
```

API response 为常用边界单位，例如 `uH`、`nF`、`kHz`；数据库保存 H、F、Hz 等 SI scalar。单位换算集中在 Application Service，不分散到 Route 或 Frontend。

## API and Service Boundary

FastAPI Route 只负责 request/response validation、dependency injection、HTTP status mapping 和调用 Application Service。

Route 不实现工程公式或 Review Rule。`services/calculations.py` 调用 Phase 1 纯函数；`services/reviews.py` 负责 Project → ReviewContext 映射、调用 Rule Engine 和持久化 structured result。

## Review Data Flow

```text
Persisted Project
  → ReviewContext
  → R001–R019 deterministic evaluation
  → R020 Evidence Completeness Gate
  → ReviewResult
  → ReviewRun + ordered ReviewFinding rows
  → REST response
  → Frontend grouping and display
```

Frontend 不执行 LLC 公式或 Engineering Rule，只负责结构化输入与结果展示。

## Phase Boundary

Phase 3 不包含：HTML/PDF Report、Waveform、ZVS classification、Datasheet/BOM Parser、Fault Diagnosis、LLM/RAG/AI Chat、Authentication、Payment 或 Cloud Deployment。
