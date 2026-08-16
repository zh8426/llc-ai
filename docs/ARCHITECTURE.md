# Architecture

## 当前范围：Phase 9

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

Phase 4 在该数据流之后增加只读 Reporting Layer：

```text
Review-time Project Snapshot + persisted Review Findings
  → pure HTML renderer
  → self-contained Chinese Design Review Report
```

Backend 和 Frontend 仍可独立启动。Engineering Engine 与 Rule Engine 不依赖 FastAPI、SQLAlchemy、Frontend、网络或 LLM。

Phase 5 新增独立的确定性 Waveform Engine：

```text
CSV + Acquisition Metadata
  → schema validation
  → unit / probe ratio / polarity normalization
  → invalid sample filtering
  → Schmitt edge detection
  → switching cycle segmentation
  → frequency / absolute peak / RMS features
```

`backend/app/waveform/` 不依赖 FastAPI、SQLAlchemy、Rule Engine、Frontend、网络或
LLM。Phase 5 只建立波形加载和基础信号处理能力，尚不持久化波形，也不输出 ZVS、
dead time、VDS at turn-on 或故障诊断结论。

Phase 6 在该纯函数引擎之上增加只读分析适配层：

```text
CSV Upload + Acquisition Metadata + Explicit ZVS Thresholds
  → Phase 5 normalized waveform
  → gate turn-on / turn-off evidence
  → VDS at gate turn-on
  → complementary-gate dead-time when VGS_Q2 exists
  → conservative ZVS classification
  → FastAPI structured response
  → React SVG waveform view
```

API 和 Frontend 只负责文件/元数据边界、结构化结果传输和展示；所有边沿、周期、
dead-time、VDS 采样与分类仍由 `backend/app/waveform/` 的确定性代码完成。Dead-time
只在完整 Q1 周期内按 `Q1 falling < Q2 rising < Q1 next rising` 配对，并保留有效、缺失和拒绝窗口计数。
没有 `VGS_Q2` 时，系统明确返回 dead-time `INSUFFICIENT_DATA`，不把单个 Q1 的
关断到下一次导通间隔冒充半桥互补 dead time。
波形上传边界为单文件 `25 MiB`、`1,000,000` 个原始采样行和 `8` 个通道（不含 `time`）；
API 在读取文件时即限制最大读取量，分析层对样本和通道数量再次校验。

## Persistence

Phase 3–4 与 Hardening 启用五张表：

```text
projects
review_runs
review_findings
review_project_snapshots
review_calculation_snapshots
```

Project 核心电压、电流、功率、谐振腔、频率、变压器、控制器和第一版器件评审字段均使用独立列保存，不把 Project 整体保存为 JSON Blob。

Review Summary、rule id、category、severity、title、description、Engineer Confirmation 和 `report_eligible` 使用可查询列。Evidence、Calculated Values、Missing Information 与 Recommended Action 是 Finding 内部的嵌套结构，使用 JSON 列保存。R020 隔离的 Finding 也完整持久化，并以 `report_eligible=false` 标识；API 将其放入 `excluded_findings`，Report 只消费正式 `findings`。

Finding Evidence 中的测量或应力数据使用统一 `MeasurementEvidence`，把数值与
`source_type`、source/channel reference、test condition、timestamp 和人工确认状态
一起保存。现有 Project 表单输入保持原有结构化 SI 列作为 source of truth；Review
时将相关值明确标记为未验证的 `user_input`。该 Persistence 基础模型尚不保存
Waveform 文件、信号处理结果或 ZVS 分类。

每次运行 Review 时同时保存不可变 Project Snapshot。报告读取该 Snapshot，而不是读取之后可能已修改的当前 Project，避免规格与 Findings 失配。Snapshot 是 Review Audit Artifact；Project 当前状态仍使用结构化列作为 source of truth。

Review 还会保存同一次运行生成的 Calculation Snapshot，包括计算引擎版本、时间、完整六项 `CalculationResult`、缺失信息和公式错误。`/calculate` 与 Review 共用 `services/calculations.py::calculate_project()` 这一条 canonical execution path。R005–R010 从传入 ReviewContext 的快照结果读取基础计算，不重复执行 Phase 1 公式。

开发环境默认 SQLite，通过 `DATABASE_URL` 可配置其他 SQLAlchemy Database URL。数据库 schema 由 Alembic migration 管理，基础 revision 为 `0001_phase0_4_baseline`，当前 Phase 8 schema head 为 `0004_fault_cases`。应用启动不再调用 `create_all()`，部署或本地启动前必须先执行 `python -m alembic upgrade head`。应用创建的 SQLite Engine 会显式启用 `PRAGMA foreign_keys=ON`，使模型声明的 `ON DELETE CASCADE` 在运行时生效。

测试 fixture 可以对隔离的临时内存数据库显式调用 `Base.metadata.create_all()`；该调用只负责测试装配，不是正式 schema evolution 路径。

迁移路径：

```text
空数据库
  → alembic upgrade head
  → Phase 0–4 schema + alembic_version

旧 Phase 0–4 create_all 数据库（先备份并确认 schema）
  → alembic stamp 0001_phase0_4_baseline
  → 后续使用 alembic upgrade head
```

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
  → canonical Calculation Snapshot
  → ReviewContext
  → R001–R019 deterministic evaluation
  → R020 Evidence Completeness Gate
  → ReviewResult
  → ReviewRun + all ordered ReviewFinding rows
      ├── report_eligible=true
      └── report_eligible=false (R020 excluded audit record)
  → REST response
  → Frontend grouping and display
```

Frontend 不执行 LLC 公式或 Engineering Rule，只负责结构化输入与结果展示。
Finding 的“输入数据”区域从 `source=user_input` 的 Evidence values 提取；“计算数据”
直接展示 persisted `calculated_values`。该展示层不推导新数值，不修改 Severity，并保留
Rule ID 与 Formula Version 供追溯。用户界面使用中文产品术语，内部 TypeScript、API
字段和值枚举保持英文。

Phase 6.1-G 将 Frontend 按职责拆分，保持 `App.tsx` 只负责页面编排：

```text
App.tsx
  ├── hooks/useProjectWorkspace.ts
  │     └── Project 列表、表单状态、保存和 Review 操作
  ├── components/ProjectSidebar.tsx
  ├── components/ProjectEditor.tsx
  ├── components/ReviewPanel.tsx
  │     └── Finding 展示与本地化标签
  ├── components/WaveformPanel.tsx
  │     └── CSV 选择、ZVS API 调用与 SVG 展示
  └── projectForm.ts / reviewLabels.ts
        └── 表单转换与纯展示格式化函数
```

组件只消费 `frontend/src/types.ts` 与 `frontend/src/api.ts` 的结构化契约；项目表单
转换和评审标签格式化保持为独立的非工程计算模块。任何 LLC 公式、Rule Engine 或
Waveform 判定仍由 Backend 确定性模块执行。

## Reporting Boundary

`backend/app/reports/` 只依赖 Pydantic Project/Review Schema。它不导入 Engineering Engine、Rule Engine、SQLAlchemy 或 FastAPI。

HTML renderer 负责转义用户文本、组织章节、从持久化 Calculation Snapshot 展示完整六项计算与 Formula Version，并附加 Engineering Disclaimer。它不得从 Finding 拼装基础计算表、重新计算数值、修改 Severity 或恢复被 R020 隔离的 Finding。

数据库中的 Review Finding 保留规则执行时的原始审计文本。`app/presentation/zh.py`
只在 API response 与 HTML Report 的展示边界生成中文标题、说明、建议和依据说明；
它不得改变 Severity、Evidence values、Missing Information、Rule ID、Formula Version
或 `report_eligible`。因此产品语言本地化不会改写历史工程判定。

Review History API 直接查询持久化的 Review Artifact：项目列表 endpoint 返回轻量
Summary 和 Calculation Snapshot 摘要，Review ID endpoint 返回完整历史 Artifact，
历史 Report endpoint 复用同一个只读 renderer。Project 后续修改不会改变旧 Review
或旧 Report。

## Datasheet Boundary（Phase 7）

Phase 7 新增独立的 MOSFET Datasheet ingestion boundary：

```text
PDF upload
  → bounded text extraction (pypdf)
  → explicit MOSFET label matching
  → unit normalization and source-page capture
  → candidate parameter persistence
  → human verification API
```

`backend/app/datasheet/parser.py` 只做可追溯的文本候选提取，不做 OCR、不猜测缺失
参数、不把 Typical 当作 Maximum，也不生成安全结论。候选值保留标准单位、原始文本行、
页码、解析器 confidence 和 `human_verified` 状态。Datasheet 表只保存抽取结果；当前
不会自动修改 Project 的器件字段，也不会绕过 Review Context 接入 R011–R013。

只有人工确认状态会被持久化为 `human_verified=true`；这仍不等同于工程师批准设计或
完成器件安全认证。扫描版 PDF、无法提取文本的 PDF 和未识别的参数都必须明确显示为
解析限制，而不是由系统补全。

## Fault Case Boundary（Phase 8）

Phase 8 新增结构化 Verified Fault Case 存储与可解释检索基础设施：

```text
FaultCase 输入
  → 显式单位校验与归一化（W / V）
  → 结构化持久化
  → symptom / engineer_verified 筛选
  → token overlap 检索分数
  → 证据记录返回
```

`FaultCase` 保存拓扑、功率/电压工况、症状、观察特征、工程师记录的根因、
验证步骤、修复措施和波形引用。当前拓扑限定为 `Half-Bridge LLC`，症状使用
工作流定义的固定枚举。`engineer_verified=true` 只表示该案例被明确标记为
工程师已核验，并使其具备 `production_evidence_eligible` 标志；系统不会根据
相似度自动核验案例，也不会把未核验案例升级为正式诊断证据。

检索分数是查询 token 集合与案例文本 token 集合的 Jaccard overlap，属于可解释的
检索排序信号，不是根因置信度、安全概率或工程裕量。Phase 8 不生成候选根因、
不执行故障诊断、不调用 LLM/RAG，也不自动修改 Project、Datasheet 或 Review 数据。

## Fault Diagnosis Boundary（Phase 9）

Phase 9 只实现确定性的诊断编排：

```text
Project ID + symptom + observed / waveform features
  → latest Design Review context
  → engineer_verified=true FaultCase filter
  → deterministic token-overlap ranking
  → up to 3 candidate causes
  → supporting / contradicting / missing evidence
  → next measurement and recorded repair action
```

候选 `cause`、验证步骤和修复措施必须来自已核验 FaultCase；没有已核验案例时不生成
新的根因。项目参数和 Review Finding 作为可追溯上下文返回，但 Phase 9 不把文本匹配
冒充 LLC 物理因果模型，也不自动把任何 Finding 解释为根因。`confidence` 只是检索
匹配分数，不是概率或安全判断。当前诊断结果不持久化，避免在未经工程师确认前形成
不可变诊断记录。

## Phase Boundary

Phase 9 不包含：OCR、BOM Parser、自动 Datasheet-to-Project mapping、LLM/RAG/AI Chat、
自动安全结论、自动控制器调整、Authentication、Payment 或 Cloud Deployment。
