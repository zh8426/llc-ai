# Unified Evaluation Audit

> 以下审计工具与合成 fixture 属于现有 V1。V2 验收见 [V2_DESIGN.md](V2_DESIGN.md) 第 13 节；软件行为、数值交叉核验和硬件验证分开报告，T01 不声称通过 V2 实现验收。

本项目的 Unified Evaluation Audit 是跨 Phase 的软件质量检查，不是新的
Engineering Phase，也不是 LLC 参考设计、器件规格、认证或量产安全结论。

## 运行

在仓库根目录执行：

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.evaluation.audit
```

脚本读取 `datasets/evaluation/` 下的两个合成 fixture，并输出 JSON 报告。返回码为
`0` 表示当前软件指标达到目标，非 `0` 表示 fixture、实现或目标需要检查。

## 指标

- Fault Diagnosis：Top-1 accuracy、known-fault Top-3 recall、evidence correctness。
- LLM Guardrails：fixture rejection accuracy、unsafe recommendation count、unsupported
  conclusion count。
- 当前软件门槛：Top-3 recall 至少 `0.80`、evidence correctness 至少 `0.95`，且
  unsafe/unsupported 计数为 `0`。

fixture 规模很小且全部为合成案例，因此通过只说明确定性软件行为与 guardrail 合同被
覆盖；不能外推真实硬件性能或工程安全性。

