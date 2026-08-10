# Review Rules

本文定义 Phase 2 的确定性 LLC Design Review Rule Engine。规则依据为 `docs/MASTER_WORKFLOW.md` 第 12–13 节。

## Finding Contract

每条规则返回统一 `Finding`：

```text
rule_id
category
severity
title
description
evidence
calculated_values
missing_information
recommended_action
requires_engineer_confirmation
report_eligible
```

Severity 只允许：

```text
PASS
INFO
WARNING
CRITICAL
INSUFFICIENT_DATA
```

`PASS` 只表示对应规则的有限检查通过，不表示设计安全、合规或可以量产。

## Evidence Policy

Evidence Source 只允许：

```text
user_input
calculation
datasheet
waveform
rule_definition
verified_fault_case
```

当前 Phase 2 尚未实现 Datasheet Parser 或 Waveform Engine，因此器件额定值和用户声明的测量值仍标记为 `user_input`，不得描述为系统已验证的数据手册或波形证据。

所有 WARNING / CRITICAL 必须至少包含一项 Evidence。R020 会将违反该条件的 Finding 标记为 `report_eligible = false`，放入 `excluded_findings`，禁止其进入正式 findings/report 数据流。

## Configurable Settings

以下项目参数没有默认值：

| Setting | Rule | Definition |
| --- | --- | --- |
| `output_power_relative_tolerance` | R010 | `abs(Vout × Iout - Pout) / Pout` 的项目允许上限 |
| `measured_vds_required_margin_ratio` | R012 | `(VDS rating - measured VDS peak) / VDS rating` 的项目要求下限 |
| `gain_review_required_parameters` | R019 | 项目批准的完整增益评审前置字段列表 |

配置缺失时不得由模型补值。

## R001–R020

### LLC-R001 — Critical Parameter Completeness

- Category：`input_integrity`
- Required：Vin Min、Vin Nom、Vin Max、Vout、Pout、Lr、Lm、Cr、Fsw Min、Fsw Max
- 全部存在：`PASS`
- 任一缺失：`INSUFFICIENT_DATA`

R001 只检查字段存在性，不替代单位、数值或物理合理性检查。

### LLC-R002 — Positive Values

- 检查上述核心电压、功率、谐振参数和频率是否维度正确且严格大于零。
- 全部有效：`PASS`
- 缺失：`INSUFFICIENT_DATA`
- 非正值或错误维度：`CRITICAL`

### LLC-R003 — Input Voltage Ordering

- Condition：`Vin Min <= Vin Nom <= Vin Max`
- 满足：`PASS`
- 不满足或输入无效：`CRITICAL`
- 缺失：`INSUFFICIENT_DATA`

### LLC-R004 — Switching Frequency Ordering

- Condition：`Fsw Min < Fsw Max`
- 满足：`PASS`
- 不满足或输入无效：`CRITICAL`
- 缺失：`INSUFFICIENT_DATA`

### LLC-R005 — Resonant Frequency Calculation

- 调用 Phase 1 `calculate_fr()`。
- 成功：`INFO`，保留 `LLC-FR-V1` 结果。
- 输入缺失或无效：`INSUFFICIENT_DATA`

### LLC-R006 — Lower Resonant Frequency Calculation

- 调用 Phase 1 `calculate_fp()`。
- 成功：`INFO`，保留 `LLC-FP-V1` 结果。
- 输入缺失或无效：`INSUFFICIENT_DATA`

### LLC-R007 — Resonant Frequency Operating Range

- Condition：`Fsw Min < fr < Fsw Max`
- 满足：`PASS`
- 不满足：`WARNING`
- 输入缺失或无效：`INSUFFICIENT_DATA`

WARNING 不等于设计失败，只提示工程师复核谐振腔和预期工作范围。

### LLC-R008 — Lm/Lr Ratio Observation

- 调用 `calculate_lm_lr_ratio()`。
- 成功固定为 `INFO`。
- 不设置 Lm/Lr 通用合格范围或 PASS/FAIL 阈值。
- 输入缺失或无效：`INSUFFICIENT_DATA`

### LLC-R009 — Characteristic Impedance

- 调用 `calculate_zr()`。
- 成功固定为 `INFO`。
- 输入缺失或无效：`INSUFFICIENT_DATA`

### LLC-R010 — Output Power Consistency

- Required：Pout、Vout、Iout、`output_power_relative_tolerance`
- Formula Version：`LLC-R010-POWER-V1`、`LLC-R010-REL-ERROR-V1`
- Relative Error：`abs(Vout × Iout - Pout) / Pout`
- Error <= configured tolerance：`PASS`
- Error > configured tolerance：`WARNING`
- 输入或配置缺失/无效：`INSUFFICIENT_DATA`

### LLC-R011 — MOSFET Static Voltage Screening

- Required：MOSFET VDS Rating、Vin Max
- `Rating <= Vin Max`：`CRITICAL`
- `Rating > Vin Max`：`PASS`

PASS 描述只能是 `Static screening passed.`，并必须说明尚未包含 overshoot、ringing、parasitic inductance 和 transient conditions。

### LLC-R012 — MOSFET Measured Peak Voltage

- Required：MOSFET VDS Rating、user-provided measured VDS Peak
- `Measured Peak > Rating`：`CRITICAL`
- 未配置 margin 且 Peak 未超过 Rating：`INFO`，只执行绝对额定值比较
- 已配置 margin 且实际 margin 低于要求：`WARNING`
- 已配置 margin 且满足要求：`PASS`
- 输入缺失/无效：`INSUFFICIENT_DATA`

`PASS` 不代表 MOSFET voltage design is safe。

### LLC-R013 — MOSFET Current Screening

- Required：Measured Peak Current、Device Current Rating、Temperature Condition
- `Measured > Rating`：`CRITICAL`
- `Measured <= Rating`：`INFO`
- 输入或温度条件缺失/无效：`INSUFFICIENT_DATA`

INFO 只表示在用户记录的条件下未超过提供的额定值，不是完整的电流、热或 SOA 结论。

### LLC-R014 — Resonant Capacitor Voltage Rating

- Required：Voltage Rating、Measured or Calculated Voltage Stress
- `Stress > Rating`：`CRITICAL`
- `Stress <= Rating`：`INFO`
- 输入缺失/无效：`INSUFFICIENT_DATA`

没有硬编码电压裕量。

### LLC-R015 — Resonant Capacitor RMS Current

- Required：RMS Current Rating、Measured or Calculated RMS Current
- `Stress > Rating`：`CRITICAL`
- `Stress <= Rating`：`INFO`
- 输入缺失/无效：`INSUFFICIENT_DATA`

没有硬编码电流、温升或寿命裕量。

### LLC-R016 — Controller Frequency Capability

- Required：Project Fsw Min/Max、Controller Frequency Min/Max
- Controller range 完整覆盖 project range：`PASS`
- 未完整覆盖：`WARNING`
- 任一范围缺失、单位错误或顺序错误：`INSUFFICIENT_DATA`

### LLC-R017 — Dead-Time Information

- 未请求 ZVS analysis：`INFO`
- 已请求且 dead-time 有效：`PASS`
- 已请求但 dead-time 缺失/无效：`INSUFFICIENT_DATA`

R017 只检查前置数据，不执行 ZVS 判断。

### LLC-R018 — Transformer Ratio Required

- 未请求 full gain review：`INFO`
- 已请求且 transformer ratio 为正 dimensionless quantity：`PASS`
- 已请求但缺失/无效：`INSUFFICIENT_DATA`

R018 只检查前置数据，不执行增益计算。

### LLC-R019 — Gain Review Prerequisite

- 未请求 full gain review：`INFO`
- 未配置 prerequisite list：`INSUFFICIENT_DATA`
- 配置字段存在缺失：`INSUFFICIENT_DATA`
- 配置字段全部存在：`PASS`

R019 只检查项目配置的字段存在性。具体单位和数值有效性由对应规则负责；本阶段不实现增益模型。

### LLC-R020 — Evidence Completeness

- 所有 WARNING / CRITICAL 有 Evidence：`PASS`
- 任一 WARNING / CRITICAL 无 Evidence：`INSUFFICIENT_DATA`
- 无 Evidence 的 Finding 被移入 `excluded_findings`，不能进入正式报告输入。

## Test Fixtures

- `normal_review_context`：所有规则可执行，项目容差和 prerequisite list 显式配置。
- `incomplete_review_context`：验证缺失数据和 `INSUFFICIENT_DATA`。
- `invalid_review_context`：验证负值、错误顺序和无效输入。
- Multi-fault scenarios：验证多条规则同时触发、Evidence 完整性和执行确定性。

