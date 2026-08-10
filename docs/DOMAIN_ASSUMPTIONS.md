# Domain Assumptions

本文记录 Phase 1 引入的公式定义、输入约束、单位约定和适用边界。公式依据为 `docs/MASTER_WORKFLOW.md` 第 10 节。

## Unit Boundary

- 所有输入都必须使用 `{value, unit}` 形式显式携带单位。
- Pint 在 Engineering Engine 边界校验物理维度。
- 公式内部统一使用 SI：H、F、V、W 以及 dimensionless ratio。
- 输出使用 Hz、ohm、A、W 或 dimensionless，并保留归一化后的输入快照。
- 所有输入和结果必须是有限标量；公式要求的物理量必须严格大于零。
- 不强制 300–1000 W、300–420 VDC 等产品范围阈值；范围检查属于后续 Rule Engine，不在计算函数中隐藏实现。

## Formula Definitions

| Formula Version | Result | Definition | Output Unit |
| --- | --- | --- | --- |
| `LLC-FR-V1` | Resonant frequency | `fr = 1 / (2π√(LrCr))` | Hz |
| `LLC-FP-V1` | Lower resonant frequency | `fp = 1 / (2π√((Lr + Lm)Cr))` | Hz |
| `LLC-ZR-V1` | Characteristic impedance | `Zr = √(Lr / Cr)` | ohm |
| `LLC-LM-LR-RATIO-V1` | Inductance ratio | `Lm / Lr` | dimensionless |
| `LLC-IOUT-V1` | Output current | `Iout = Pout / Vout` | A |
| `LLC-PIN-V1` | Input power estimate | `Pin = Pout / efficiency` | W |

## Resonant Tank Applicability

- `Lr`、`Lm` 和 `Cr` 表示用户提供的集中参数值，并要求严格大于零。
- `LLC-FR-V1` 和 `LLC-ZR-V1` 是理想串联谐振腔的参数定义。
- `LLC-FP-V1` 严格采用本项目指定的 `(Lr + Lm)` 定义。它不应被解释为在任意负载、寄生参数或控制状态下实测到的唯一谐振点。
- Phase 1 不考虑器件容差、磁性元件非线性、直流偏置、温度、寄生参数、负载反射或控制环路影响。
- `Lm/Lr` 只输出观察值；本阶段没有可接受范围、PASS/FAIL 阈值或安全裕量。

## Power Applicability

- `LLC-IOUT-V1` 要求 `Pout` 与 `Vout` 来自同一稳态输出工况，并将结果解释为对应的平均输出电流。
- `LLC-PIN-V1` 使用用户提供的效率计算输入功率估算值，不是测量值。
- 效率必须是 dimensionless ratio，取值范围为 `0 < efficiency <= 1`；也允许输入可转换的百分数，例如 `94 percent`。
- `Pout` 和 `Vout` 必须严格大于零。零功率待机等工况不在这些 Phase 1 公式的输入域内。

## Safety and Evidence Boundary

- Phase 1 结果是确定性计算数据，不是 Measured Data。
- 这些结果不包含器件应力、动态尖峰、热、保护、容差或安全评估。
- 任一计算成功都不得被描述为设计安全、通过评审、符合标准或可直接量产。
- Phase 1 未引入工程裕量、经验阈值或 Design Review Rule。

