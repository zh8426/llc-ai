# REST API

Phase 3 提供 Project 持久化、六项确定性计算和 R001–R020 Design Review API。默认地址为 `http://127.0.0.1:8000`，交互文档位于 `/docs`。

所有 Engineering Quantity 都使用显式结构：

```json
{
  "value": 45,
  "unit": "uH"
}
```

API 在持久化边界校验物理维度并转换为 SI。负数等维度正确但工程上无效的值允许保存，以便 Rule Engine 返回结构化 `CRITICAL`；单位维度错误直接返回 `422`。

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

## Development CORS

允许的前端 Origin 由 `CORS_ORIGINS` 配置，默认：

```text
http://127.0.0.1:5173
http://localhost:5173
```

本阶段没有 Authentication、Cloud Deployment 或公开网络安全配置。

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
`zvs_status`、`confidence`、逐周期 `evidence_cycles`、gate turn-on/turn-off 时间戳
和 limitations。`zvs_status` 只允许：

```text
LIKELY_ZVS
PARTIAL_ZVS
LIKELY_HARD_SWITCHING
INSUFFICIENT_DATA
```

没有 `VGS_Q2` 时 `dead_time.status` 为 `INSUFFICIENT_DATA`。该 endpoint 不保存上传的
CSV，不调用 LLM，不输出安全认证或量产结论。CSV、单位、阈值或测试条件不符合契约时
返回 `422`。
