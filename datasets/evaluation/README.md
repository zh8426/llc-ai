# Evaluation Fixtures

这些 JSON 是软件 Evaluation Fixture，不是经过验证的 LLC 参考设计、器件规格或安全结论。

- `fault_diagnosis_cases.json`：验证 Phase 9 的 Top-1、Top-3、证据 token 匹配和已核验案例边界。
- `llm_guardrail_cases.json`：验证 Phase 10 对未知 Evidence、缺失 Evidence、工程数字缺少单位和不安全措辞的拒绝行为。

运行审计：

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.evaluation.audit
```

审计结果是软件质量指标，不是行业认证指标，也不能证明 LLC 设计安全或可量产。
