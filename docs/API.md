# REST API

Phase 3–10 提供 Project 持久化、六项确定性计算、R001–R020 Design Review、ZVS 波形分析、MOSFET Datasheet MVP、Verified FaultCase、确定性 Fault Diagnosis 和受约束的 LLM Engineering Orchestration API。默认地址为 `http://127.0.0.1:8000`，交互文档位于 `/docs`。

所有 Engineering Quantity 都使用显式结构：

```json
{
  "value": 45,
  "unit": "uH"
}
```

API 在持久化边界校验物理维度并转换为 SI。负数等维度正确但工程上无效的值允许保存，以便 Rule Engine 返回结构化 `CRITICAL`；单位维度错误直接返回 `422`。

## 统一错误响应

所有 API 错误均返回统一 JSON 结构，不再要求客户端解析 FastAPI 默认的 `detail` 字符串：

```json
{
  "code": "PROJECT_NOT_FOUND",
  "message": "项目不存在。",
  "details": {
    "project_id": "missing-project"
  }
}
```

字段约定如下：

- `code`：稳定的机器可读错误码，前端分支逻辑必须优先使用此字段。
- `message`：面向用户的中文提示，可直接显示。
- `details`：可选的结构化诊断信息，具体内容由错误码决定，不应作为业务分支依据。

当前错误码与 HTTP 状态码：

| 错误码 | HTTP | 含义 |
| --- | ---: | --- |
| `PROJECT_NOT_FOUND` | 404 | 项目不存在 |
| `REVIEW_NOT_FOUND` | 404 | 评审记录不存在 |
| `RESOURCE_NOT_FOUND` | 404 | 请求路径或资源不存在 |
| `METHOD_NOT_ALLOWED` | 405 | 请求方法不被允许 |
| `INVALID_ENGINEERING_UNIT` | 422 | 工程参数单位或数值无效 |
| `MISSING_REQUIRED_DATA` | 422 | 请求缺少必要工程数据 |
| `WAVEFORM_SCHEMA_INVALID` | 422 | 波形 CSV 或元数据不符合输入契约 |
| `WAVEFORM_TOO_LARGE` | 413/422 | 波形文件或样本规模超过限制 |
| `ZVS_INSUFFICIENT_DATA` | 422 | ZVS 分析缺少必要数据 |
| `INVALID_REQUEST` | 422 | 请求参数校验失败 |
| `DATABASE_CONFLICT` | 409 | 持久化数据无法满足当前操作 |
| `INTERNAL_ERROR` | 500 | 未预期的服务器错误 |
| `DATASHEET_TOO_LARGE` | 413 | 数据手册文件超过大小限制 |
| `DATASHEET_PDF_INVALID` | 422 | PDF 无法提取可验证文本 |
| `DATASHEET_NOT_FOUND` | 404 | 数据手册不存在 |
| `DATASHEET_PARAMETER_NOT_FOUND` | 404 | 数据手册参数不存在 |
| `FAULT_CASE_NOT_FOUND` | 404 | 故障案例不存在 |
| `LLM_NOT_CONFIGURED` | 503 | LLM Provider 未显式启用或缺少 API Key |
| `LLM_PROVIDER_ERROR` | 502 | LLM Provider 未返回有效结果 |
| `LLM_OUTPUT_INVALID` | 422 | LLM 输出未通过结构化证据/单位/安全校验 |

客户端不应依赖中文 `message` 或 `details` 的具体文本来判断错误类型；后续新增错误码时保持现有字段结构不变。

## `GET /health`

确认 Backend 进程可用。成功返回 `200`：

```json
{
  "status": "ok",
  "service": "llc-engineering-assistant-backend",
  "version": "0.1.0"
}
```

## Project Schema

Project request 支持：

```text
name, topology
vin_min, vin_nom, vin_max
vout, iout, pout, target_efficiency
lr, lm, cr
fsw_min, fsw_nom, fsw_max
transformer_ratio, dead_time
primary_switch
resonant_capacitor
controller
review_requests
review_settings
```

当前 topology 固定为 `Half-Bridge LLC`，rectification type 固定为 `Diode Rectification`。除 `name` 外，工程字段允许缺失；Review 必须将缺失信息返回为 `INSUFFICIENT_DATA`，不得猜测。

## `GET /projects`

返回按最近更新时间排序的 Project：

```json
{
  "projects": []
}
```

## `POST /projects`

创建 Project。最小请求：

```json
{
  "name": "500 W LLC"
}
```

完整演示请求见 `examples/projects/500w_48v_llc.json`。成功返回 `201` 和完整 Project。

## `GET /projects/{project_id}`

读取一个 Project。不存在时返回 `404`。

## `PATCH /projects/{project_id}`

部分更新 Project。省略字段表示保持原值；显式 `null` 用于清除可选字段。

嵌套对象也采用部分更新。例如以下请求只更新 Part Number，不清除 Manufacturer 或 Rating：

```json
{
  "primary_switch": {
    "part_number": "PROJECT-APPROVED-PART"
  }
}
```

## `POST /projects/{project_id}/calculate`

运行 Phase 1 六项基础计算：

```text
fr
fp
Zr
Lm/Lr
Iout
Pin estimate
```

返回：

```json
{
  "project_id": "...",
  "calculated_at": "2026-08-15T00:00:00Z",
  "engine_version": "LLC-CALCULATION-ENGINE-V1",
  "calculations": [],
  "missing_information": [],
  "errors": {}
}
```

每个成功结果保留输入快照、单位和 formula version。该响应就是本次 canonical Calculation Snapshot。项目不完整时 endpoint 仍返回 `200`，并在 `missing_information` 列出缺失字段；公式输入无效时在 `errors` 中返回确定性错误，不生成伪结果。

## `POST /projects/{project_id}/review`

从已保存的结构化 Project 运行一次 canonical calculation，使用该 Calculation Snapshot 构建 `ReviewContext`，运行 R001–R020，并持久化 Project Snapshot、Calculation Snapshot、Review Run 与每条 Finding。成功返回 `201`：

```json
{
  "project_id": "...",
  "review_id": "...",
  "created_at": "...",
  "summary": {
    "pass": 10,
    "info": 3,
    "warning": 4,
    "critical": 0,
    "insufficient_data": 3
  },
  "findings": [],
  "excluded_findings": [],
  "calculation_snapshot": {
    "project_id": "...",
    "calculated_at": "2026-08-15T00:00:00Z",
    "engine_version": "LLC-CALCULATION-ENGINE-V1",
    "calculations": [],
    "missing_information": [],
    "errors": {}
  }
}
```

如果 Project 未显式保存 `iout`，但 `pout` 和 `vout` 有效，R010 使用 Calculation Snapshot 中的 `LLC-IOUT-V1` 结果。不会补充其他缺失工程参数、器件额定值、测量值或项目裕量。

正式 `findings` 只包含通过 R020 Evidence Gate 的结果。未通过 Gate 的原始
Finding 会完整持久化，并在 `excluded_findings` 中返回；这些条目的
`report_eligible` 固定为 `false`，不会进入正式 HTML Report。

R012–R015 的相关 Evidence 可包含 `measurements` 映射。每项均保留明确的
`value + unit` 和 provenance 字段。当前页面手工填写的数据标记为
`source_type=user_input`、`human_verified=false`；API 不会自动把它升级为
datasheet 或 waveform-derived evidence。

API 的用户可见 Finding 标题、说明、建议和 Evidence 说明使用中文展示文案；
Rule ID、Severity 枚举值、字段名、Formula Version 和结构化数值保持原英文契约。
数据库仍保留规则运行时的原始审计文本，本地化不会改变工程判断。

## `GET /projects/{project_id}/review`

返回最近一次已持久化 Review。Project 不存在或从未运行 Review 时返回 `404`。

## `GET /projects/{project_id}/reviews`

按创建时间倒序返回 Project 的全部 Review 历史。列表项只包含：

```text
review_id
created_at
summary
calculation_snapshot.calculated_at
calculation_snapshot.engine_version
calculation_snapshot.calculation_count
```

列表不展开 Findings。Project 存在但尚未运行 Review 时返回空 `reviews`；Project
不存在时返回 `404`。

## `GET /reviews/{review_id}`

通过 Review ID 返回任意一次已持久化 Review，包括当时保存的 Calculation Snapshot、
正式 Findings 和 `excluded_findings`。Review 不存在时返回 `404`。

## `GET /reviews/{review_id}/report`

使用指定历史 Review 的不可变 Project Snapshot、Calculation Snapshot 和 Findings
生成 HTML Report。该 endpoint 不读取当前 Project 参数，也不重新执行计算或规则。
Review 不存在时返回 `404`；旧 Review 缺少必要 Snapshot 时返回 `409`。

## `GET /projects/{project_id}/report`

将最近一次 Review 渲染为自包含、可打印的中文 HTML Design Review Report，成功返回 `200 text/html`。

报告只消费 Review 时保存的不可变 Project Snapshot、Calculation Snapshot、Review Summary 和 structured Findings。Reporting Layer 不调用 Calculation Engine 或 Rule Engine，不从 Findings 反向拼装基础计算，也不会把当前已修改的 Project 参数与旧 Review 混合。

返回规则：

- Project 不存在：`404`
- 尚未运行 Review：`404`
- 旧 Review 不包含 Project Snapshot：`409`，需要重新运行 Review
- 旧 Review 不包含 Calculation Snapshot：`409`，需要重新运行 Review

报告包含 Project Specification、Calculation Results、Summary、Critical、Warning、Insufficient Data、Passed Checks、Information Findings、Evidence、Calculation Versions 和 Engineering Disclaimer。本阶段不生成 PDF。

## Datasheet API（Phase 7，MOSFET MVP）

Phase 7 只接收 MOSFET PDF 数据手册，执行保守的文本提取并保存候选参数。当前不做 OCR，扫描版 PDF 会返回结构化 `DATASHEET_PDF_INVALID` 错误。

### `POST /datasheets`

使用 `multipart/form-data` 上传 PDF：

```text
file: MOSFET PDF 数据手册
manufacturer: 可选，人工提供的制造商
part_number: 可选，人工提供的器件型号
```

当前候选参数包括：

```text
VDS, ID, Rds(on), Qg, Coss, Eoss, RthJC, Tj Max, Package
```

每个候选参数均保留：

```text
value
unit
value_type
test_condition
source_page
confidence
human_verified
```

数值参数会在提取边界转换为明确的标准单位；`test_condition.source_line` 保留原始文本行用于追溯。正则提取的 `confidence` 只是解析器质量提示，不是工程安全裕量，也不会自动升级为安全结论。

成功返回 `201`。新文档的 `parser_status` 为 `NEEDS_HUMAN_REVIEW`；没有识别到支持参数时为 `NO_SUPPORTED_PARAMETERS`。

### `GET /datasheets` 与 `GET /datasheets/{datasheet_id}`

返回已保存的文档、解析状态和参数候选。数据手册参数不会自动写入 Project，也不会自动参与 R011–R013 或其他 CRITICAL 规则。

### `PATCH /datasheets/{datasheet_id}/parameters/{parameter_id}`

用于修正候选值或完成人工确认。例如：

```json
{
  "human_verified": true
}
```

只有所有已提取参数均 `human_verified=true` 时，文档状态才变为 `VERIFIED`。人工确认仍然是工程师责任，不代表系统完成安全认证。

数据手册文件大小上限为 `10 MiB`。错误使用统一结构化响应，主要错误码包括：

```text
DATASHEET_TOO_LARGE
DATASHEET_PDF_INVALID
DATASHEET_NOT_FOUND
DATASHEET_PARAMETER_NOT_FOUND
```

## Fault Case API（Phase 8）

Phase 8 提供结构化故障案例 CRUD 和确定性筛选/相似检索，不生成诊断结论。案例支持：

```text
case_id, topology, power, vin, vout, load
symptom, observed_features, root_cause
verification_steps, fix
waveform_before, waveform_after
engineer_verified
```

### `POST /fault-cases`

创建案例。`power`、`vin`、`vout` 必须使用 `{value, unit}`；案例可以先以
`engineer_verified=false` 保存，供研究和后续人工审核。系统不会根据文本推断根因，也
不会自动把未确认案例作为正式诊断证据。

### `GET /fault-cases`

返回案例列表，并支持以下筛选参数：

```text
query: 对 symptom、root_cause、observed_features、verification_steps、fix 做 token overlap 检索
symptom: 第一批预定义故障类型
engineer_verified: true/false
limit: 1–100，默认 50
```

有 `query` 时返回 `similarity_score`。该分数是可解释的 token overlap 检索分数，不是
根因置信度，不表示安全概率，也不替代 Phase 9 的 Evidence Ranking。

### `GET/PATCH/DELETE /fault-cases/{case_id}`

分别读取、更新和删除案例。将 `engineer_verified` 更新为 `true` 后，响应中的
`production_evidence_eligible` 才会为 `true`。只有人工确认案例才有资格进入未来的正式
诊断证据；Phase 8 不执行诊断、不输出 Top 3 Candidate Causes。

## Development CORS

允许的前端 Origin 由 `CORS_ORIGINS` 配置，默认：

```text
http://127.0.0.1:5173
http://localhost:5173
```

本阶段没有 Authentication、Cloud Deployment 或公开网络安全配置。

## LLM Orchestration API（Phase 10）

Phase 10 的 LLM 只是编排与解释层。LLM 必须通过工具读取项目、调用确定性计算、
运行 Review、读取 Datasheet/Waveform/FaultCase 和生成报告；它不能替代公式、单位
校验、Rule Engine 或工程师确认。

### `GET /llm/tools`

返回当前允许暴露给 Provider 的工具 Schema：

```text
get_project
calculate_resonant_tank
run_design_review
get_component_parameter
analyze_waveform
run_zvs_check
find_similar_fault_cases
search_engineering_evidence
generate_review_report
```

### `POST /llm/orchestrate`

请求：

```json
{
  "message": "请读取项目并说明当前缺少哪些证据。",
  "project_id": "project-uuid"
}
```

响应要求结构化包含 `claims`、`evidence`、`missing_information`、`next_actions` 和
`requires_engineer_confirmation`。每条 Claim 必须引用响应中的 `evidence_id`；工程
数字必须带显式单位；安全、认证或量产相关措辞必须有 Evidence 且要求工程师确认。
未经验证的 Datasheet 值、仿真值和估算值不能被模型改写为实测值。

LLM 默认关闭。只有显式设置以下环境变量后才会发起 Provider 请求：

```text
LLM_ENABLED=true
OPENAI_API_KEY=<local secret>
OPENAI_MODEL=gpt-5.6-terra
OPENAI_MAX_TOOL_ROUNDS=4
```

未配置时接口返回 `LLM_NOT_CONFIGURED`，不会回退到虚假的模型回答。测试使用 Fake
Provider，不发送真实网络请求。

## Fault Diagnosis API（Phase 9）

Phase 9 提供确定性的故障诊断编排，不调用 LLM/RAG，也不凭空生成根因。输入由项目
ID、症状、工程师提供的观察特征和可选波形特征组成；系统读取该项目最新 Design
Review，并只检索 `engineer_verified=true` 的 FaultCase。

### `POST /fault-diagnoses`

请求示例：

```json
{
  "project_id": "project-uuid",
  "symptom": "ZVS lost",
  "observed_features": ["low resonant current at gate turn-on"],
  "waveform_features": ["zvs_status=PARTIAL_ZVS"],
  "contradicting_features": []
}
```

响应包含最多 3 个 `candidate_causes`。每个候选均带有：

```text
source_case_id
cause
confidence
supporting_evidence
contradicting_evidence
missing_information
next_measurement
recommended_action
```

`confidence` 是确定性的 token overlap 检索分数，不是概率、安全结论或工程裕量。
`cause`、`next_measurement` 和 `recommended_action` 均直接来自已核验案例记录；系统
不会把案例结论自动宣称为当前项目的唯一根因。若没有足够的已核验案例，响应返回少于
3 个候选或空列表，并在 `limitations` 中明确说明证据不足。`contradicting_features`
只记录调用方明确标记的反证文本，系统不会自行判断文本是否与根因矛盾。

## `POST /waveforms/zvs`

上传 CSV 并执行 Phase 5–6 的确定性波形与 ZVS 分析。请求使用 `multipart/form-data`：

```text
file: CSV 文件（必须包含 time、VGS_Q1、VDS_Q1、IRES）
sample_rate: Hz
time_unit: 默认 s
channels: JSON 通道元数据映射
test_condition: JSON 测试条件映射
vds_zvs_threshold: V
vds_hard_switching_threshold: V
gate_low_threshold: 可选
gate_high_threshold: 可选
```

`channels` 示例：

```json
{
  "VGS_Q1": {"unit": "V", "probe_ratio": 1, "polarity": 1},
  "VDS_Q1": {"unit": "V", "probe_ratio": 1, "polarity": 1},
  "IRES": {"unit": "A", "probe_ratio": 1, "polarity": 1},
  "VGS_Q2": {"unit": "V", "probe_ratio": 1, "polarity": 1}
}
```

成功返回 `200`，包括 `switching_frequency`、`dead_time`、`vds_at_turn_on`、
`zvs_status`、`cycle_consistency`、逐周期 `evidence_cycles`、gate turn-on/turn-off 时间戳
和 limitations。`dead_time` 只在完整的 Q1 周期窗口内配对：
`Q1 falling < Q2 rising < Q1 next rising`。它还返回
`valid_cycle_count`、`missing_cycle_count` 和 `rejected_cycle_count`；跨周期、缺失或
不唯一的 edge 不会被拼接成貌似合理的 dead time。`zvs_status` 只允许：

```text
LIKELY_ZVS
PARTIAL_ZVS
LIKELY_HARD_SWITCHING
INSUFFICIENT_DATA
```

没有 `VGS_Q2` 时 `dead_time.status` 为 `INSUFFICIENT_DATA`。该 endpoint 不保存上传的
CSV，不调用 LLM，不输出安全认证或量产结论。CSV、单位、阈值或测试条件不符合契约时
返回 `422`。

波形上传有明确资源边界：单个 CSV 最大 `25 MiB`，最多 `1,000,000` 个原始采样行，最多
`8` 个波形通道（不含 `time` 列）。超过文件大小时返回 HTTP `413`，错误标识为
`WAVEFORM_TOO_LARGE`；超过样本或通道上限时返回 `422`，错误码仍为
`WAVEFORM_TOO_LARGE`。服务端使用有上限的读取，不会为了检查文件大小而将无限输入读入内存。
