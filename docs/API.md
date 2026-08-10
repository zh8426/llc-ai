# API

## `GET /health`

用于确认 Backend 进程已启动并能够响应请求。

成功响应：`200 OK`

```json
{
  "status": "ok",
  "service": "llc-engineering-assistant-backend",
  "version": "0.1.0"
}
```

该 endpoint 不执行数据库、工程计算、规则、波形或外部服务检查。

## Phase 1 Boundary

Phase 1 的确定性计算引擎仅作为 Python 模块提供，尚未暴露 REST API。Calculation API 属于后续明确授权的 Phase，当前不得通过 `/health` 或临时 endpoint 绕过架构边界。
