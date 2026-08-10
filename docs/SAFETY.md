# Safety

本项目是面向具备专业能力的电力电子工程师的 Engineering Assistance Tool，不是安全认证工具或 Safety Authority。

系统不得在证据不足时声明设计安全、符合标准、可直接量产或已经充分验证，也不得控制 Converter PWM、绕过保护、降低保护阈值或建议未经适当保护直接给实验硬件上电。

任何 Design Review Report 都必须明确：

- PASS 只表示对应有限规则通过；
- 报告不是安全认证、法规符合性证明或量产批准；
- 过冲、振铃、寄生参数、瞬态、热、保护和实测数据缺失时不得推导安全结论；
- WARNING、CRITICAL 和高风险工程决策需要合格工程师复核原始 Evidence。

HTML 或后续 PDF Reporting Layer 不得重新计算工程结果、改变 Finding Severity、隐藏 Contradicting/Missing Evidence，或将用户声明数据描述为系统已验证的测量数据。
