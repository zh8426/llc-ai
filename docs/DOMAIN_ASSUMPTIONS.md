# Domain Assumptions

本文记录 Phase 1 确定性计算与 Phase 2 规则引擎引入的公式定义、输入约束、单位约定、项目级配置和适用边界。依据为 `docs/MASTER_WORKFLOW.md` 第 10、12–13 节。

## Cross-Phase E1-A：变压器匝比约定

- 项目统一定义变压器匝比为 `n = Np / Ns`，即原边匝数除以副边匝数。
- `transformer_ratio` 的 API 单位为 `dimensionless`，数值必须为有限正值；它表示匝数比，不表示百分比、增益或电压比的另一种隐式定义。
- 任何后续 FHA、Required Gain 或 Operating Point 计算必须复用该约定，不得在模块内部改用 `Ns / Np`。
- 当前 E1-A 只统一定义和输入边界；现有 R018 仍只检查完整增益评审的前置数据，不执行增益计算。
- 当前不根据 `Vin`、`Vout` 或文件名反推匝比，也不自动修改用户保存的 `transformer_ratio`。

## Cross-Phase E1-B：FHA 基础量

- 直流输出负载电阻定义为 `Ro = Vout² / Pout`，其中 `Pout` 与 `Vout` 必须来自同一稳态工作点。
- 对当前限定的 Half-Bridge LLC + Diode Rectification，FHA 等效初级负载采用
  `Re = (8 / π²) × n² × Ro`，公式版本为 `LLC-RE-FHA-V1`。该系数与 `n = Np / Ns` 约定来自 TI UCC25600 数据手册的半桥 LLC 设计方程。
- 品质因数定义为 `Qe = Zr / Re`，其中 `Zr = √(Lr / Cr)`，公式版本为 `LLC-QE-FHA-V1`。
- 归一化开关频率定义为 `Fn = fs / fr`，公式版本为 `LLC-FN-FHA-V1`；`fs = fr` 时 `Fn = 1`。
- E1-B 仅计算 FHA 的输入量，不计算复阻抗、增益曲线、感性/容性区域、工作点频率或安全结论。FHA 的适用性仍受寄生参数、整流器行为、轻载和偏离谐振点等因素影响。

## Cross-Phase E1-C：FHA 复阻抗与增益

- 角频率定义为 `ω = 2πfs`，其中 `fs` 为正的实际开关频率。
- 理想 FHA 网络的元件阻抗定义为 `ZLr = jωLr`、`ZCr = 1/(jωCr)`、`ZLm = jωLm`；等效负载 `Re` 与励磁电感并联：`Zp = ZLm || Re`。
- 输入阻抗定义为 `Zin = ZLr + ZCr + Zp`，结构化结果同时保存其实部、虚部、幅值和归一化输入。
- FHA tank gain 定义为 `H(jω) = Zp / Zin`、`MFHA = |H(jω)|`，公式版本分别为 `LLC-ZIN-FHA-V1` 和 `LLC-GAIN-FHA-V1`。
- E1-C 假设稳态、理想线性 FHA 阻抗网络，所有 `Lr`、`Lm`、`Cr`、`Re`、`fs` 均为正值；不推断寄生参数、整流器换流细节或测试安全性。
- E1-C 只计算单个给定频率的复阻抗与增益，不进行感性/容性区域分类、Required Gain、工作点求解、增益曲线 API 或前端展示。

## Cross-Phase E1-D：感性/容性工作区域

- 工作区域只根据 FHA 输入阻抗的虚部 `Im(Zin)` 判定，不使用 `fs < fr` 或 `fs > fr` 作为替代规则。
- `Im(Zin) > 0` 分类为 `INDUCTIVE`，`Im(Zin) < 0` 分类为 `CAPACITIVE`，接近零时分类为 `BOUNDARY`。
- `LLC-REGION-FHA-V1` 使用 `1e-12 ohm` 作为浮点数零点比较容差；该容差仅用于数值边界处理，不是工程裕量、ZVS 阈值或安全判据。
- E1-D 的 `INDUCTIVE` 结果只表示 FHA 模型下的输入阻抗区域，不等同于 ZVS 成功、设计安全或可量产结论。
- E1-D 只复用 E1-C 的单频 `Zin`；不执行 Required Gain、工作点求解、频率扫描或控制器范围覆盖判断。

## Cross-Phase E1-E：Required Gain 与工作点求解

- 当前限定的 Half-Bridge LLC 使用 `Mreq = Vin / (2 × n × Vout)`，其中 `n = Np / Ns`；公式版本为 `LLC-MREQ-FHA-V1`。
- `solve_operating_frequency()` 在显式的 `[fsw_min, fsw_max]` 范围内求解 `MFHA(fsw) = Mreq`，并保留范围内的全部数值根作为 `candidates` 证据。
- 每个候选根都会重新计算 `Zin` 和工作区域；只有 `operating_region = INDUCTIVE` 的候选根才可成为 `selected` 工作点。容性或边界根不会被伪装成正常工作点。
- 求解器使用确定性的对数频率扫描和二分收敛；扫描点数与收敛容差是数值算法设置，不是工程裕量或安全阈值。
- 无根或没有感性候选根时返回 `NO_VALID_OPERATING_POINT`，同时保留已找到的候选根，不抛出“可运行”结论。
- E1-E 只输出 FHA 工作点估计，不判断控制器频率覆盖、峰值增益裕量、ZVS 成功、器件应力或设计安全。

## Cross-Phase E1-F：Operating Envelope 与 R021–R026

- Operating Envelope 在 `[fsw_min, fsw_max]` 内扫描 FHA 增益，保留最大可用增益、对应频率和输入阻抗区域，并分别求解 `Vin Min`、`Vin Nom`、`Vin Max` 的 Required Gain 工作点。
- R021 检查建立 FHA 工作包络所需的完整输入；缺失或量纲无效时返回 `INSUFFICIENT_DATA`。
- R022 比较扫描得到的 `Mavailable,max` 与 `Mrequired,max`；不足时只返回 `WARNING`，不输出 `CRITICAL` 或安全结论。
- R023 检查标称工作点的 FHA 区域；感性为 `PASS`，容性为 `WARNING`，不得将容性结果表述为 ZVS 必然失败。
- R024 检查标称工作频率是否落在配置的 `[fsw_min, fsw_max]` 内；不满足时返回 `WARNING`。
- R025 只报告 FHA 峰值增益和所需增益对比，当前不硬编码峰值增益裕量阈值，因此为 `INFO`。
- R026 提醒远离谐振点、轻载和寄生参数可能降低 FHA 估计适用性；不把模型估计描述为实测或安全结论。
- R021–R026 仅在请求完整增益评审时执行；未请求时返回 `INFO`，不猜测或补全 FHA 输入。

## Cross-Phase E1-G：增益曲线 API 与前端展示

- `calculate_gain_curve()` 在项目保存的 `[fsw_min, fsw_max]` 范围内执行线性频率扫描；频率端点和扫描点数均保留在结构化结果中。
- 增益曲线每个点复用 E1-C 的 `MFHA`、`Zin`，复用 E1-D 的 `Im(Zin)` 工作区域分类，并记录 `Fn = fs / fr`；曲线不是另一套 FHA 公式。
- API `POST /projects/{project_id}/gain-curve` 只接受 `point_count`（2–1001）作为扫描控制量。`Lr/Lm/Cr/Vout/Pout/transformer_ratio/Fsw Min/Max` 必须来自已保存项目；缺失时返回 `MISSING_REQUIRED_DATA`，不猜测或补值。
- `LLC-GAIN-CURVE-FHA-V1` 只标识当前确定性扫描实现；前端 SVG 图表是展示层，不改变结构化结果，也不把 FHA 估计描述为实测、ZVS、安全或量产结论。
- 扫描点上限是 API 资源边界，不是工程阈值；线性扫描选择是展示与可重复性约定，不代表控制器实际调频轨迹或最优工作点。

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
| `LLC-RO-FHA-V1` | Output resistance | `Ro = Vout² / Pout` | ohm |
| `LLC-RE-FHA-V1` | FHA equivalent load | `Re = (8 / π²) × n² × Ro` | ohm |
| `LLC-QE-FHA-V1` | FHA quality factor | `Qe = Zr / Re` | dimensionless |
| `LLC-FN-FHA-V1` | Normalized frequency | `Fn = fs / fr` | dimensionless |
| `LLC-MREQ-FHA-V1` | Required gain | `Mreq = Vin / (2 × n × Vout)` | dimensionless |
| `LLC-ZIN-FHA-V1` | FHA input impedance | `Zin = ZLr + ZCr + (ZLm || Re)` | ohm |
| `LLC-GAIN-FHA-V1` | FHA tank gain | `MFHA = abs((ZLm || Re) / Zin)` | dimensionless |
| `LLC-REGION-FHA-V1` | FHA operating region | sign of `Im(Zin)` | enum |
| `LLC-OPERATING-POINT-FHA-V1` | FHA operating point | `MFHA(fsw) = Mreq` with inductive-region selection | structured |
| `LLC-AVAILABLE-GAIN-FHA-V1` | Available FHA maximum gain | `max(MFHA(fsw))` over configured frequency range | dimensionless |
| `LLC-OPERATING-ENVELOPE-FHA-V1` | FHA operating envelope | Vin Min/Nom/Max targets plus scanned gain peak | structured |
| `LLC-GAIN-CURVE-FHA-V1` | FHA gain curve | linear scan of `MFHA`, `Fn`, `Zin`, and operating region over `[fsw_min, fsw_max]` | structured |

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
- Phase 7 Datasheet Parser 的候选值来自 PDF 文本正则提取，必须保留来源页、原始文本行、
  解析器 confidence 和 `human_verified` 状态；未人工确认的数据不得升级描述为 verified
  datasheet evidence，也不得自动进入 CRITICAL 规则。
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

## Phase 6 ZVS Processing Definitions

- `calculate_vds_at_gate_turn_on()` 取检测到的 `VGS_Q1` 上升沿所在采样点的 `VDS_Q1`
  值，不做亚采样插值；同一行过滤保证 `VGS_Q1`、`VDS_Q1`、`IRES` 时间轴对齐。
- `dead_time` 只有在同时提供 `VGS_Q2` 时才计算，定义为 Q1 下降沿到其后第一个
  Q2 上升沿的时间差。只有 Q1 时返回 `INSUFFICIENT_DATA`，不进行替代估算。
- ZVS 分类阈值必须由本次分析显式提供：`VDS <= vds_zvs_threshold` 为
  `LIKELY_ZVS`，`VDS >= vds_hard_switching_threshold` 为
  `LIKELY_HARD_SWITCHING`，两者之间为 `PARTIAL_ZVS`。这两个阈值是信号分类配置，
  不是通用安全裕量。
- 多周期汇总只有全部周期同类时才返回对应的 `LIKELY_*`；存在混合结果时返回
  `PARTIAL_ZVS`。`cycle_consistency` 是占主导分类的周期比例，不是概率或安全置信度。
- 每个 ZVS 结果必须带有逐周期 VDS、IRES 和 gate turn-on 时间证据，并明确声明
  这是波形特征分类，不是安全认证或量产批准，且需要合格工程师复核原始探头、缩放、
  极性和测试条件。

## Phase 7 Datasheet Processing Definitions

- Phase 7 MVP 只支持 MOSFET PDF 文本提取；扫描版 PDF、图片表格和无法提取文本的文档
  返回明确的解析限制，不自动执行 OCR。
- 支持字段固定为 `VDS`、`ID`、`Rds(on)`、`Qg`、`Coss`、`Eoss`、`RthJC`、`Tj Max`
  和 `Package`。未在文本中明确标注的字段保持缺失，不使用文件名或模型知识补全。
- 数值字段在提取边界归一化为标准单位：V、A、ohm、coulomb、farad、joule、K/W 和
  degC；原始单位和文本行通过 `test_condition.source_line` 保留用于追溯。
- `confidence` 是解析器对标签与单位匹配质量的提示，不是概率、不代表器件可靠性，
  也不是工程裕量。当前正则标签匹配候选为 `0.8`，文本 Package 候选为 `0.6`。
- `human_verified` 默认必须为 `false`。只有工程师通过确认 API 后才可标记为 `true`；
  当前 Phase 7 不会将任何 Datasheet 值自动映射到 Project 或 Rule Engine。

## Phase 8 Fault Case Definitions

- `FaultCase` 当前只接受 `Half-Bridge LLC` 拓扑；症状枚举与工作流保持一致：ZVS lost、
  MOSFET overheating、VDS overshoot、excessive resonant current、startup failure、
  output undervoltage、output oscillation、transformer saturation suspected、
  protection false triggering 和 light-load instability。
- `power`、`vin`、`vout` 必须携带显式工程单位，持久化时分别归一化为 W、V；`load` 目前
  仅保存为描述性文本，不对负载类型、阻抗或工作点作未声明的工程推断。
- `observed_features`、`verification_steps` 和 `fix` 是工程师提供的结构化文本证据，
  `root_cause` 是案例记录中的人工结论；Phase 8 不从这些字段推导新的 LLC 计算结果。
- `engineer_verified` 默认是 `false`。只有调用方明确设置为 `true` 的案例才标记为
  `production_evidence_eligible`；该标记不等同于安全认证、量产批准或系统自动验证。
- 检索使用查询 token 集合与案例文本 token 集合的 Jaccard overlap：
  `|intersection| / |union|`。该分数仅用于可解释的相似案例排序，不是置信度、故障
  概率、严重度、安全裕量或根因正确率。
- 当前检索在应用服务中读取结构化案例后进行确定性筛选和排序；Phase 8 不引入向量库、
  语义嵌入、LLM/RAG 或自动故障诊断。

## Phase 9 Fault Diagnosis Definitions

- 诊断请求必须指定现有 `project_id` 和第一批故障症状；项目当前拓扑仍限定为
  `Half-Bridge LLC`。
- 诊断上下文由项目结构化参数、该项目最新的 report-eligible Review Finding、请求中
  明确提供的 `observed_features` / `waveform_features` 以及匹配症状的
  `engineer_verified=true` FaultCase 组成。缺少的上下文必须在 `missing_information`
  或 `limitations` 中明确显示。
- 候选根因只允许复制已核验 FaultCase 的 `root_cause`；系统不从症状、参数名称或
  Finding 文本自行推导新的 LLC 物理根因。没有足够案例时返回少于 Top 3 的候选或空列表，
  不使用占位根因填充结果。
- `confidence` 定义为输入观察/波形特征 token 集合与候选案例文本 token 集合的
  Jaccard overlap，范围为 `[0, 1]`。该值是检索排序分数，不是概率、准确率、严重度、
  安全裕量或工程师信心。
- `next_measurement` 与 `recommended_action` 直接来自候选案例的验证步骤和修复措施；
  它们是待工程师复核的历史案例建议，不是对当前硬件的自动操作指令。
- `contradicting_features` 只有在调用方明确提供时才会出现在候选的反证列表中；系统不
  使用关键词或语言模型自行判断一段文本是否与候选根因矛盾。
- Phase 9 不持久化诊断结果，不调用 LLM/RAG，不实现自动 Evidence Ranking 以外的
  物理模型推理，也不修改 Project、Review、Waveform 或 FaultCase 数据。

## Phase 10 LLM Orchestration Definitions

- LLM 只作为 Engineering Orchestrator；所有可由现有 Python 模块确定性完成的计算、
  单位转换、Waveform 分析、Review 规则和 FaultCase 检索必须通过 allow-listed tool
  执行，不能由模型自行计算或猜测。
- Provider 默认关闭。只有 `LLM_ENABLED=true` 且 `OPENAI_API_KEY` 存在时才允许发起
  外部请求；API Key 只从运行环境读取，不写入仓库或数据库。
- LLM 输出采用结构化 Schema：每条 Claim 必须引用同一响应中的 Evidence ID；没有
  Evidence 的 Claim、未知 Evidence 引用、未带单位的工程数字和未要求工程师确认的
  安全/认证/量产措辞都会被拒绝。
- `OPENAI_MAX_TOOL_ROUNDS` 是调用次数上限（当前允许 1–8），用于限制 Provider 循环；
  它不是工程阈值或安全裕量。
- 工具结果与最终模型消息均保留在响应的结构化 `tool_calls` 和 `evidence` 字段中；
  Phase 10 不把 LLM 文本持久化为工程事实，也不自动修改 Project、Review、Waveform、
  Datasheet 或 FaultCase。
