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
  "calculations": [],
  "missing_information": [],
  "errors": {}
}
```

每个成功结果保留输入快照、单位和 formula version。项目不完整时 endpoint 仍返回 `200`，并在 `missing_information` 列出缺失字段；公式输入无效时在 `errors` 中返回确定性错误，不生成伪结果。

## `POST /projects/{project_id}/review`

从已保存的结构化 Project 构建 `ReviewContext`，运行 R001–R020，并持久化 Review Run 与每条 Finding。成功返回 `201`：

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
  "findings": []
}
```

如果 Project 未显式保存 `iout`，但 `pout` 和 `vout` 有效，Review Service 使用 `LLC-IOUT-V1` 确定性结果作为 R010 输入。不会补充其他缺失工程参数、器件额定值、测量值或项目裕量。

正式 `findings` 只包含通过 R020 Evidence Gate 的结果。

## `GET /projects/{project_id}/review`

返回最近一次已持久化 Review。Project 不存在或从未运行 Review 时返回 `404`。

## Development CORS

允许的前端 Origin 由 `CORS_ORIGINS` 配置，默认：

```text
http://127.0.0.1:5173
http://localhost:5173
```

本阶段没有 Authentication、Cloud Deployment 或公开网络安全配置。
