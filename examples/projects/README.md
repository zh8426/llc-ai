# Example Projects

`500w_48v_llc.json` 是用于验证 Project API、六项基础计算和 Review Workflow 的示例输入。

其中数值仅为软件演示数据，不是经过验证的参考设计，不包含真实器件规格、实测波形、容差、热设计或安全结论。可通过以下 PowerShell 命令导入正在运行的 Backend：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/projects `
  -ContentType "application/json" `
  -InFile examples/projects/500w_48v_llc.json
```
