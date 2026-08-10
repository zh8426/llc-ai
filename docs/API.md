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

