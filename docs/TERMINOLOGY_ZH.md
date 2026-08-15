# 中文产品术语表

本表用于统一用户界面、HTML Report 和面向工程师的文档用词。内部代码、API
字段、数据库列、Rule ID 和 Formula Version 继续使用英文标识。

| Internal Term | 中文显示 |
| --- | --- |
| Project | 项目 |
| Design Review | 设计评审 |
| Review Summary | 评审摘要 |
| Finding | 评审项 / 评审结论 |
| Evidence | 依据 |
| Input Data | 输入数据 |
| Calculated Data | 计算数据 |
| Missing Information | 缺失信息 |
| Recommended Next Step | 建议下一步 |
| Measurement Evidence | 测量证据 |
| Resonant Tank | 谐振腔 |
| Resonant Frequency | 谐振频率 |
| Characteristic Impedance | 谐振腔特征阻抗 |
| Inductance Ratio | 电感比 Lm/Lr |
| Input Power | 输入功率 |
| Output Current | 输出电流 |
| Engineering Disclaimer | 工程说明 / 免责声明 |

## Severity

| Internal Value | 中文显示 | 含义 |
| --- | --- | --- |
| `PASS` | 通过 | 当前有限规则检查通过，不等于整机安全 |
| `INFO` | 提示 | 工程参考信息，不作通过或失败判断 |
| `WARNING` | 警告 | 存在需要工程师进一步确认的问题 |
| `CRITICAL` | 严重 | 存在明确的严重风险或条件冲突 |
| `INSUFFICIENT_DATA` | 数据不足 | 信息不足，无法完成可靠判断 |

## 显示原则

- 工程缩写 `Vin`、`Vout`、`Iout`、`Pout`、`Lr`、`Lm`、`Cr`、`Fsw`、
  `VDS`、`ZVS` 保留。
- 优先使用“中文名称 + 工程缩写”，例如“最大输入电压 Vin Max”。
- `PASS` 不翻译为“安全”，`INFO` 不翻译为“正常”。
- 开发 Phase 编号不在产品界面展示。
- Rule ID 和 Formula Version 作为追溯标识保留英文。
