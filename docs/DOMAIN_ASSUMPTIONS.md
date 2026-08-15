# Domain Assumptions

本文记录 Phase 1 确定性计算与 Phase 2 规则引擎引入的公式定义、输入约束、单位约定、项目级配置和适用边界。依据为 `docs/MASTER_WORKFLOW.md` 第 10、12–13 节。

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

## Phase 2 Rule Definitions

Phase 2 引入以下项目级规则定义，不引入通用数值裕量：

- R001 将 `Vin` 展开为 `vin_min`、`vin_nom`、`vin_max`，与 Project Domain Model 和 R003 一致。
- R010 relative error 定义为 `abs(Vout × Iout - Pout) / Pout`；允许上限必须由 `output_power_relative_tolerance` 显式配置。
- R012 measured VDS margin 定义为 `(VDS rating - measured VDS peak) / VDS rating`；要求下限必须由 `measured_vds_required_margin_ratio` 显式配置。
- R013、R014、R015 仅在 stress **大于** supplied rating 时输出 `CRITICAL`。等于或低于 rating 时只输出 `INFO`，除非未来项目配置了经过批准的 margin rule。
- R016 将 controller range 未完整覆盖 project switching range 定义为 `WARNING`，不把它表述为安全失效。
- R017、R018、R019 只验证后续分析的前置数据，不执行 ZVS 或 gain calculation。
- R019 的 required parameter list 必须由项目配置；Phase 2 不猜测完整增益模型需要哪些字段。
- R020 将无 Evidence 的 WARNING / CRITICAL 从正式 findings 数据流中隔离。

## Phase 2 Evidence Boundary

- Phase 2 中的器件 rating、stress 和 measured peak 均来自用户结构化输入，因此 Evidence Source 标记为 `user_input`。
- `measured_*` 字段表示用户声明的数据含义，不代表系统已经验证示波器文件、探头配置或测试条件。
- Review Evidence 中的 `MeasurementEvidence.source_type=user_input` 与
  `human_verified=false` 是当前手工输入的 provenance 标记，不会把该数据升级为
  verified waveform evidence。
- Datasheet Parser 和 Waveform Engine 尚未实现，不得将用户输入升级描述为 verified datasheet 或 waveform evidence。
- R012 margin 可以为负值，用于表示 measured peak 已超过 rating；Phase 1 核心公式结果仍要求为有限正值。
- 所有 `CRITICAL` 器件应力结果要求 Engineer Confirmation。
- 任一 PASS 都是单条有限规则的结果，不构成安全、合规或量产结论。

## Phase 3 API and Persistence Boundary

- Project API 接受显式 `{value, unit}`，在持久化边界只校验物理维度与有限数值，并转换为 SI scalar 保存。
- 维度正确但非正、顺序错误或工程上无效的输入允许保存，由 Calculation Engine 或 Rule Engine 返回结构化错误/Finding；维度错误不得进入数据库。
- 如果 Project 没有显式 `iout`，但 `pout` 与 `vout` 可用于 `LLC-IOUT-V1`，Review Service 使用该确定性计算结果作为 R010 输入。除此之外不自动补充缺失参数。
- SQLite 是开发阶段持久化实现，不改变任何 LLC 工程定义。
- `examples/projects/500w_48v_llc.json` 仅用于软件工作流演示。其数值不是经过验证的参考设计、器件规格、实测数据或安全结论。

## Phase 4 Reporting Boundary

- HTML Report 只展示 Review 时保存的 Project Snapshot 和结构化 Finding，不重新执行任何工程公式或 Rule。
- 报告中的 Calculation Version 来自 persisted `CalculationResult.formula_version` 或 calculation Evidence reference，不由 Reporting Layer 推断。
- 报告将浮点结果格式化为最多 8 位有效数字用于阅读；该显示格式不修改数据库或 structured Review Result。
- 中文报告是展示层，不改变 Rule Severity、Evidence、Engineering Assumption 或 Safety Boundary。

## Phase 5 Waveform Processing Definitions

- 第一版 CSV 必需列固定为 `time`、`VGS_Q1`、`VDS_Q1`、`IRES`。时间归一化为秒，
  电压归一化为伏特，电流归一化为安培。
- `sample_rate` 的单位固定为 Hz。它是采集元数据，不替代 CSV 的 `time`；周期与频率
  均使用实际时间戳计算，因此允许严格递增的非均匀采样。
- 通道样本按 `normalized = unit_converted × probe_ratio × polarity` 归一化。
  `probe_ratio` 必须大于零，`polarity` 只能为 `1` 或 `-1`。
- 可选的 `bandwidth_hz` 只作为采集元数据保留；Phase 5 不根据带宽字段修改波形。
- 任一必需通道或时间为 NaN/Infinity 的整行样本会被丢弃，并在 `discarded_samples`
  中记录数量。过滤后时间必须严格递增；系统不插值、不猜测缺失值。
- `WAVEFORM-SCHMITT-EDGE-V1` 使用 Schmitt 状态机。未显式提供阈值时，先取信号
  第 5 与第 95 百分位作为稳健低/高电平，再以该跨度的 30% 和 70% 作为低/高阈值。
  调用方可同时显式提供两个阈值，结果会记录阈值及其来源。
- 边沿时间定义为样本首次跨过对应 Schmitt 阈值的时间戳；Phase 5 不做亚采样插值。
- `WAVEFORM-FSW-MEAN-PERIOD-V1` 定义为相邻上升沿完整周期平均时长的倒数。
- `WAVEFORM-ABS-PEAK-V1` 定义为样本绝对值最大值。
- `WAVEFORM-RMS-SAMPLE-V1` 用于未提供时间轴的等权样本 RMS；提供时间轴时使用
  `WAVEFORM-RMS-TIME-WEIGHTED-V1` 梯形积分，以支持非均匀采样。
- `WAVEFORM-ANALYSIS-MVP-V1` 串联 CSV 加载、`VGS_Q1` 边沿检测、周期分段、
  开关频率及所有已加载通道的 Peak/RMS；它不产生 ZVS 分类。
- 所有 Phase 5 输出都是确定性信号特征，不是 ZVS、安全、器件合规或故障结论。
