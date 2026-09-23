# LLC AI V2 重构设计说明书

版本：0.2｜日期：2026-09-21｜状态：T01 建立的设计契约，运行时代码仍为 V1

仓库：[zh8426/llc-ai](https://github.com/zh8426/llc-ai)。审阅基线：`4ecae6e7ba3e8cd7221c30dbe0d10436534167d1`。

本文将已讨论的重构方案整理为仓库内契约。V2 模型、目录、接口与功能均为目标设计，不表示已经实现。任务顺序和状态以 [MASTER_WORKFLOW.md](MASTER_WORKFLOW.md) 为准；公式和适用条件见 [DOMAIN_ASSUMPTIONS.md](DOMAIN_ASSUMPTIONS.md)；工作约束见 [AGENTS.md](../AGENTS.md)。T01 不新增运行时代码、数据库迁移或硬件验证。

## 1. 重构决策

重建产品流程、核心数据模型和业务编排；逐项验证后迁移已有数学与信号处理模块。沿用 Python / FastAPI、Pydantic、SQLAlchemy / Alembic、Pint、NumPy、React / TypeScript，不为重构更换技术栈。

首个可用版本 M1 完成：**输入规格 → 生成候选谐振腔 → 多工况检查 → 比较与选择 → 保存设计版本 → 导出计算书。**

项目最终覆盖电源设计全流程，首版计算聚焦单输出半桥 LLC。磁件、器件、热、控制、仿真、实测与生产交付逐步接入同一条版本和证据链。

### 1.1 成功标准

- 用户无需先在别处算好 Lr/Lm/Cr，才可使用本产品。
- 候选明确说明通过了哪些模型内检查、违反哪些约束、哪些指标没有建立模型。
- 相同规范化输入、模型和配置可重复得到相同工程结果与候选顺序。
- 结论可追溯到需求、设计、工况、模型版本与证据。
- 修改设计后旧历史保留，当前版本明确提示需要重新分析/测试的内容。
- 无 LLM API 或外部网络时，核心设计流程仍可运行。

### 1.2 首版范围决策

以下为产品范围，不是对真实用户项目的默认工程假设。

| 项目 | M1 目标 | 后续处理 |
|---|---|---|
| 拓扑 | 半桥 LLC、变频控制 | 全桥、CLLC、双向、多相另行立项 |
| 应用定位 | 延续 300–1000 W、300–420 VDC、24 V / 48 V | 范围外输入明确适用性，不静默宣称支持 |
| 器件与副边 | 硅 MOSFET、单输出、中心抽头二极管整流 | 桥式整流、同步整流及其他器件模型另行扩展 |
| 匝比 | n = Np / Ns_half | 区分半绕组与全绕组；V1 未记录连接的数据待确认 |
| 模型 | 理想稳态 FHA、正负载、显式频率范围 | 空载、启动、突发、短路、瞬态使用独立模型或仿真 |
| 参数变化 | 输入、负载与 Lr/Lm/Cr 确定性容差组合 | 温度模型、相关公差和概率分布后续扩展 |
| 输出结论 | 谐振腔候选与模型内初筛 | 不等于已完成磁件制造、效率和硬件验证 |
| AI | 非核心依赖 | 工具契约稳定后用于编排与解释 |

副边连接的明确化是 V2 新模型契约。V1 仅标有“Diode Rectification”的项目不得被自动推断为中心抽头，也不得自动改变匝比。连续匝比候选不能直接作为可制造的整数绕组设计。

## 2. 当前代码与重构依据

| 当前观察 | 代码位置 | V2 决策 |
|---|---|---|
| 计算有单位、输入快照和公式版本 | `backend/app/engine/`、`schemas/engineering.py` | 保留原则，独立核验纯函数后复用 |
| 参数、观测和配置集中在 Project | `models/project.py` | 分离需求、设计、工况、观测和配置 |
| 包络为单一 Pout 下的三档 Vin | `engine/operating_envelope.py` | 使用显式 CaseSet 与逐工况结果 |
| 前端需要预填 Lr/Lm/Cr，部分后端字段未暴露 | `frontend/src/projectForm.ts` | 改为规格驱动，并保留已有设计导入入口 |
| 波形接口没有项目/版本归属和持久化路径 | `api/waveforms.py` | 接入 TestRun / EvidenceArtifact |
| 手册候选数值 confidence 固定为 0.8 | `datasheet/parser.py` | 保留提取插件，不能将固定值当准确率 |
| 故障排序主要为词语重合检索 | `diagnosis/engine.py`、`services/diagnosis.py` | 定位相似案例，物理诊断规则后续单独实现 |
| 已有评审/计算快照 | `models/review.py`、`services/reviews.py` | 保留历史，扩展不可变输入与依赖追踪 |

已有测试是软件行为基础，不等于已完成独立工程验证。迁移时保留单位、异常、边界与证据测试，并增加独立参考对照。

## 3. 电源设计全流程

| 阶段 | 工作台能力 | 交付与完成条件 | 里程碑 |
|---|---|---|---|
| 需求定义 | 电气、动态、效率、环境、尺寸、成本、隔离等指标 | 有来源、版本与验证方法的规格书 | M1，验证能力分阶段补齐 |
| 系统方案 | 母线、LLC、辅助电源与控制接口 | 系统边界及损耗预算 | M1 边界、M2 扩展 |
| 谐振腔综合 | 规格与公开搜索配置产生候选 | 参数来源、搜索范围、淘汰原因 | M1 |
| 多工况检查 | 输入、负载、容差与频率限制 | 逐工况结果、失败原因和覆盖边界 | M1 |
| 磁性器件 | 磁芯、匝数、气隙、绕组、漏感、磁通与损耗 | 磁件规格、可制造性检查 | M2 |
| 器件/BOM | MOSFET、整流器、电容等参数与应力匹配 | 条件匹配的选型依据及 BOM 版本 | M2 |
| 效率与热 | 分项损耗、温度参数与散热路径 | 效率曲线、温升估计和不确定项 | M2 |
| 控制/驱动/保护 | 调频、启动、反馈、死区、保护与恢复 | 参数表、约束和验证用例 | M2–M3 |
| 仿真 | 参数化模板导出、工况执行和结果回读 | 模型版本与计算/仿真差异 | M3 |
| 原理图/PCB | 功率回路、驱动、采样、接地、隔离、EMI、散热评审 | 位置明确、可关闭的问题清单；先人工结构化评审 | M3 |
| 样机测试 | 波形、效率、动态、温升和异常状态 | 工况/仪器/实物配置明确的测试与复测 | M3 |
| 发布与生产 | 需求验证矩阵、可靠性/适用合规记录、替代料与生产测试 | 发布基线、未关闭事项和批准记录 | M4 |

AC-DC 的 PFC、整流、母线纹波和保持时间先作为 LLC 输入接口约束，M1 不实现通用 PFC 引擎。适用标准、版本、条款与验证方法由具体应用确定，不从拓扑名称推导合规结论。

## 4. 核心数据模型

使用关系型核心字段与不可变运行快照。参数、外键、状态、可查询指标结构化保存；完整快照和模型配置可用版本化 JSON。波形、PDF、仿真文件作为独立文件对象，数据库保存来源、校验值和元数据。

### 4.1 对象与最小契约

| 对象 | 最小字段 | 关系与生命周期 |
|---|---|---|
| Project | id、name、application、created_at、archived_at | 稳定项目身份；默认归档，不级联抹除历史 |
| RequirementSet | id、project_id、version、state、source、content_hash | 草稿可改，冻结后派生新版本 |
| Requirement | id、requirement_set_id、metric、operator、target、unit、condition、verification_method | 关联具体分析/测试证据 |
| DesignRevision | id、project_id、requirement_set_id、parent_id、revision、state、topology、secondary_connection、content_hash | 分析绑定冻结版本 |
| DesignParameter | revision_id、key、value_si、unit_si、display_unit、origin、source_ref、tolerance | 目标、假设、选定、估算、实测明确区分 |
| SearchProfile | id、version、parameter_grids、constraints、selection_policy、provenance、content_hash | 有限、显式、可导出的搜索配置 |
| CaseSet | id、project_id、version、coverage_definition、content_hash | 不可变工况集合，声明抽样与覆盖范围 |
| OperatingCase | id、case_set_id、vin、vout、load_power、ambient_temperature、state、corner_values | 未知温度不自动补 25°C |
| SynthesisRun | id、requirement_set_id、search_profile_id、case_set_id、engine_version、status、input_hash | 方案生成先于任何正式设计版本 |
| Candidate | id、synthesis_run_id、parameters、screening_state、reason_codes、metric_summary | 淘汰原因留存；选中后物化为设计版本 |
| AnalysisRun | id、design_revision_id、case_set_id、analysis_type、engine_version、input_hash、status | 输入只读；保存配置、日志和依赖清单 |
| CaseResult | analysis_run_id、case_id、point_status、metrics、roots、selected_branch、limitations | 保留其他成功工况及部分失败 |
| Finding | run_id、case_id、requirement_id、rule_id、rule_version、severity、evidence_refs、recommended_action | 定位到需求、工况和证据 |
| ComponentRevision | id、manufacturer、part_number、revision、parameters、source_document_id | 参数带条件和来源；更新不覆盖历史 |
| DesignComponent | design_revision_id、reference、component_revision_id、quantity | 器件/BOM 与设计关联 |
| EvidenceArtifact | id、project_id、kind、content_sha256、file_ref、metadata、created_at | 分析、仿真、实测、参考、合成分开 |
| TestRun | id、design_revision_id、physical_unit_id、hardware_config_hash、case_id、procedure_version、artifact_ids | 记录真实样机与实际配置，不被设计修改重写 |
| IssueRecord | id、project_id、finding_id、owner、state、action、verification_refs | 问题处理与复测依据 |

M1 实现 Project 至 Finding，并支持最小 EvidenceArtifact 存放参考依据。ComponentRevision、DesignComponent、TestRun、IssueRecord 完整业务放在 M2–M3，不提前建立大量没有业务路径的空表。

T02 实现版本标识和草稿并发控制；T03 定义 content_hash 的规范化算法。表中是目标字段契约，不要求 T02 同时实现最终运行指纹。

### 4.2 输入、变量与观测

- 综合必填：Vin 最小/标称/最大值、Vout、额定功率、需要检查的正负载点、允许调频范围和搜索配置来源。
- 可记录但 M1 不预测：效率曲线目标、纹波、负载阶跃、环境温度、功率密度、成本、隔离要求。
- 设计变量：n、fr、Ln、Qe 或直接给定 Lr/Lm/Cr；两种入口进入同一计算路径。
- 观测：实测效率、Lm、温升、VDS 峰值通过证据接入，不直接覆盖标称设计参数。
- target_efficiency 只能用于目标记录和有明确假设的预算估算，未建立损耗模型前不能声称效率达标。

### 4.3 工程量

API 沿用 `{value, unit}`，内部 SI，保存原始单位和规范化输入；来源、适用条件、容差含义、核验状态可追溯。必须区分峰值/RMS、直流/交流分量、原副边折算、半绕组/全绕组、LLC 母线/整流前交流输入。未知使用缺失状态，不用 0、负数或空字符串替代。

### 4.4 冻结、依赖与失效

1. 修改发生在草稿；正式分析前冻结需求、设计、工况和配置。
2. 修改冻结设计创建新 revision；旧 AnalysisRun、TestRun 和报告不改变。
3. 指纹包含规范化输入、需求版本、模型/规则版本、求解配置与所消费的器件模型校验值。序列化和浮点规范版本化。
4. “过期”表示旧结果未覆盖当前选定版本；旧结果对旧版本的历史意义仍保留。
5. M1 任何被分析读取的输入变化均要求新运行；只改项目名称不失效。
6. M2 可按字段级依赖复用：更换 MOSFET 不改变未消费器件参数的理想 FHA，但应重算依赖寄生、损耗和热参数的结果。
7. 修改实物配置后旧测量不能自动验证新版本；TestRun 核对实物编号、实际配置和工况。
8. 时间与任务 ID 不参与工程数值一致性判定；未来随机分析须记录种子与采样器版本。

## 5. 计算与候选生成

### 5.1 路径与搜索

规格和显式 SearchProfile → 有限候选枚举 → CaseSet → 逐点求解 → 约束筛选 → 证据与排序。首版采用确定性枚举，不引入学习型优化或复杂代理。

搜索维度为 n、fr、Ln、Qe_rated 的有限集合。范围、步长、依据、版本、计算量和未覆盖区域对用户可见；预设须独立核验，不冒充通用工程极限。已有设计直接导入与生成候选共用内核。

### 5.2 参数综合

在首版理想半桥、中心抽头、稳态正负载模型中：

| 量 | 定义 | 约定 |
|---|---|---|
| n | Np / Ns_half | 导通半绕组匝比 |
| Ro_rated | Vout² / Pout_rated | Ω，额定正负载 |
| Re_rated | 8 n² Ro_rated / π² | Ω，原边 FHA 交流等效负载 |
| Mreq | 2 n Vout / Vin | 忽略整流压降和损耗 |
| Ln | Lm / Lr | 不混用其他文献的倒数/加一形式 |
| Qe_rated | Zr / Re_rated | 在额定负载定义 |
| Zr | Qe_rated × Re_rated | Ω |
| Lr | Zr / (2πfr) | H |
| Cr | 1 / (2πfrZr) | F |
| Lm | Ln × Lr | H |

完整来源和适用边界记录在 DOMAIN_ASSUMPTIONS。反算测试需闭合恢复 fr、Zr、Ln、Qe；每个其他负载重新计算 Re 与 Qe。反算公式不提供实际器件型号或可制造绕组。

### 5.3 工况与求解

- 包括 Vin 边界、标称和可选内部点，规格要求的各正负载点，以及 Lr/Lm/Cr 显式容差组合。
- 保存实际参与计算的值。有限网格/角点不证明连续全域通过；报告要说明可能漏掉内点峰值。
- Lr/Lm 相关时，独立角点仅作为标记清楚的包络假设，并允许显式相关组合。
- 温度无模型时只记录，标明未计算影响；空载、启动、突发、短路和瞬态为 OUTSIDE_MODEL。
- 若扩展宽输出范围，Vout 也必须成为工况维度；固定输出的 M1 不能声称覆盖宽输出。
- 已有控制器数据时，有效频率区间是项目范围与器件范围的交集；交集为空报告约束冲突。
- 保留所有找到的根、残差、工作区域、阻抗及拒绝原因。现有扫描/二分需加强对多根、切根、窄峰和端点的验证。
- 未扫到根表述为“搜索范围内未找到可用解”，不冒充数学上不存在解的证明。
- 多个可用根保留，缺少工作分支依据时标记需选择，不能自动宣称控制可实现。
- 低输入增益覆盖、高输入降增益、轻载与有效频率范围均逐工况检查；所有强制模型内检查完成才可称通过 FHA 初筛。
- 感性区域不等于实际 ZVS。节点电容、换流电流、死区和仿真/实测证据在后续模型加入，参考 ST AN2450 第 3 节。

### 5.4 排序和资源限制

分开显示通过已实现约束、存在失败、尚有未完成检查的候选；只比较完成同一检查集合的结果。展示最差工况、所需频率范围、与边界的距离和增益覆盖。排序指标公开，相同值用固定参数顺序与候选 ID 打破平局。

无损耗/磁件/成本模型时不显示“最高效率/最小体积/最低成本”排名。无候选通过时返回主要阻塞约束及工况，不自动放宽参数。

候选数、工况数、计算次数与取消机制作为软件资源配置。执行前预览计算量，超限明确返回，禁止静默丢点；资源上限不是工程阈值。

## 6. 状态与结果契约

Finding 严重程度保留 `PASS / INFO / WARNING / CRITICAL / INSUFFICIENT_DATA`。其他维度独立保存。

| 字段 | 枚举 | 含义 |
|---|---|---|
| execution_status | QUEUED、RUNNING、SUCCEEDED、PARTIAL、FAILED、CANCELLED | 软件任务状态 |
| applicability | APPLICABLE、NOT_APPLICABLE、OUTSIDE_MODEL、NOT_IMPLEMENTED | 能力适用性 |
| point_status | SOLVED、MULTIPLE_SOLUTIONS、NO_SOLUTION_IN_SEARCH、INSUFFICIENT_DATA、SOLVER_ERROR、OUTSIDE_MODEL | 单个工况状态 |
| evidence_kind | ANALYTICAL、SIMULATED、MEASURED、REFERENCE、SYNTHETIC | 证据来源 |
| requirement_verdict | SATISFIED、VIOLATED、UNVERIFIED、NOT_APPLICABLE | 附带方法/范围的需求判定 |

SUCCEEDED 不等于设计通过，SOLVED 不等于硬件验证。效率等未建模指标保持 UNVERIFIED。每次运行保存冻结引用、输入哈希、版本、单位、工况结果、证据索引、覆盖统计、限制与下一项动作。报告与前端只消费结构化结果。

## 7. 页面与操作流程

所有页面共享项目、需求版本、设计版本和工况上下文，并绑定路由/请求。波形、手册和曲线成为当前设计里的工具。

| 页面 | 核心内容 | 主动作 |
|---|---|---|
| 项目总览 | 版本、需求覆盖、阻塞事项与最近运行 | 继续当前任务 |
| 规格与约束 | 规格、单位、来源、未验证的其他需求 | 冻结需求 |
| 方案生成 | 搜索配置、固定参数、数量与资源预算 | 生成或导入已有参数 |
| 候选比较 | 参数、通过/失败工况、约束与限制 | 选择并创建设计版本 |
| 工作范围 | 输入/负载/容差矩阵、曲线、失败筛选 | 定位最差工况 |
| 设计版本 | 参数差异、来源、关联运行与过期提示 | 派生新草稿 |
| 计算书 | 需求、参数、公式、工况、失败项与证据 | 导出 HTML / 可复算 JSON |
| 器件与磁件 | M2 的模型、绕组、应力与损耗 | 建立实物设计/BOM |
| 仿真与测试 | M3 的运行、波形、实物配置、偏差 | 关联验证与复测 |
| 设计发布 | M4 的基线与需求矩阵 | 发布包 |

M1 不展示无功能的可点击页面；未实现能力在需求和报告中说明。缺失项能跳转到对应字段、工况或证据。异步结果绑定完整上下文和请求序号，旧项目/旧版本慢响应不能覆盖当前视图。

## 8. 模块边界

使用模块化单体，不在首版拆微服务。

| 层 | 职责 | 不应做的事 |
|---|---|---|
| API / DTO | 输入校验、错误、资源和任务访问 | 公式与候选优劣判断 |
| Application | 冻结、任务编排、快照和结果保存 | 隐式补参数或单位 |
| Domain | 对象、不变量、状态机 | ORM 会话、网络或 UI 状态 |
| Engineering | 纯计算、综合、求解与工况扫描 | 访问数据库或编写自然语言结论 |
| Rules | 根据结果和明确约束生成 Finding | 第二套不一致的公式 |
| Infrastructure | 数据、文件、执行器和仿真适配 | 把存储默认值当工程输入 |
| Reporting | 结构化结果到 HTML / JSON | 重新计算 |
| Frontend | 输入、比较、展示与上下文 | 浏览器中的另一套工程公式 |
| LLM Adapter | 调工具、解释、定位证据 | 修改冻结设计或生成无依据数值 |

拟在 `backend/app/v2/` 下建立 `api/`、`application/`、`domain/`、`engineering/`、`rules/`、`infrastructure/`、`reporting/`；前端使用 `frontend/src/features/v2/`。这是待实现的迁移隔离方案，不表示目录已存在，也不要求立即移动 V1 文件。

数学模块可通过薄适配复用，核验后再迁入稳定位置，避免维护两套公式。首版任务采用持久化 Run 与有界本地执行器；长计算不阻塞请求，重启后遗留 RUNNING 标记为可重试中断，重试创建新 attempt 并留存日志。分布式队列按真实需求引入。

## 9. M1 API 草案

新接口前缀 `/api/v2`，下表均为目标契约，T01 没有新增这些路由。

| 方法与路径 | 输入重点 | 行为 |
|---|---|---|
| POST /projects | 名称与应用信息 | Project |
| POST /projects/{id}/requirement-sets | 需求草稿 | RequirementSet |
| PATCH /requirement-sets/{id} | draft_etag 与字段 | 只修改草稿，冲突 409 |
| POST /requirement-sets/{id}/freeze | 草稿版本 | 冻结需求 |
| POST /projects/{id}/case-sets | 工况与生成规则 | 冻结集合、数量与覆盖说明 |
| POST /search-profiles | 网格、约束、依据 | 版本化配置 |
| POST /synthesis-runs | requirement_set_id、case_set_id、search_profile_id | 202 与任务 ID |
| GET /synthesis-runs/{id} | ID | 状态、覆盖与失败信息 |
| GET /synthesis-runs/{id}/candidates | 分页、过滤、稳定排序 | 候选及原因码 |
| POST /projects/{id}/design-drafts | candidate_id 或显式参数、需求版本 | 设计草稿 |
| PATCH /design-drafts/{id} | draft_etag 与字段 | 只修改草稿 |
| POST /design-drafts/{id}/freeze | 草稿版本 | 冻结设计 |
| POST /analysis-runs | design_revision_id、case_set_id、analysis_type、配置 | 202 与任务 ID |
| GET /analysis-runs/{id} | ID | 状态、指标、Finding 与证据 |
| GET /analysis-runs/{id}/case-results | 筛选、分页 | 逐工况根、指标和限制 |
| POST /runs/{kind}/{id}/cancel | kind 为 synthesis 或 analysis | 保存部分结果并取消 |
| GET /design-revisions/{id}/comparison | other_revision_id | 参数、需求与分析差异 |
| GET /analysis-runs/{id}/report | HTML 或 JSON | 固定运行的报告 |

运行创建使用幂等键：同键同请求返回同任务，不同请求返回 409。跨项目引用、未冻结输入、单位错误均返回机器可读错误和字段级修复提示。候选物化后重新分析，或在完整输入指纹、模型与工况相同时关联不可变结果，不能只复制 PASS。

## 10. 复用与重写清单

以下路径省略共同前缀 `backend/app/`，前端/测试除外。

| 现有模块 | 处理方式 | 门槛 |
|---|---|---|
| engine/units.py | 优先复用 | 等价单位、错误维度、非有限数 |
| engine/resonant_tank.py、power.py | 优先复用 | 独立公式核验，预算效率与预测分开 |
| engine/gain.py、operating_region.py | 核验后复用 | 匝比、副边、独立参考和边界 |
| engine/operating_point.py | 保留主体并加固 | 多根、切根、窄峰、端点、数值失败和分支 |
| engine/operating_envelope.py | 重写编排 | 多负载、容差、部分失败、覆盖元数据 |
| schemas/engineering.py | 扩展结果契约 | 状态、来源、适用性分开 |
| models/project.py、schemas/project.py | 重建 | 需求、设计、测量、配置分离 |
| services/calculations.py、services/reviews.py | 重写编排 | 冻结、哈希和运行持久化 |
| rules/builtin/ | 逐条迁移 | 保留依据，增加适用性并去除重复检查 |
| waveform/ | M3 核验接入 | 单位、探头、采样、时延、噪声和证据保存 |
| datasheet/parser.py | 候选提取插件 | 条件/核验可追溯，不使用未校准 confidence 冒充概率 |
| diagnosis/ | 案例检索 | 零匹配返回无匹配，物理诊断独立建立 |
| reports/ | 复用渲染、重做适配 | 固定运行、模型边界和未验证需求 |
| frontend/src/App.tsx、projectForm.ts | 重建流程 | 项目/版本/工况上下文与候选比较 |
| backend/tests/ | 分类保留和扩充 | 行为回归与独立工程核验分开 |

确定性计算必须由程序执行，但不构成其比测量天然可信的排序。模型与实测冲突时核对适用范围、工况、仪器与不确定度，保留双方证据。

## 11. 迁移策略

- 在原仓库的 V2 分支开发，保留 V1 和 main 历史；不进行破坏性覆盖。
- 开发使用独立 V2 数据库与文件目录，先做只读导入器和 dry-run 对账。
- V1 Project 映射到 Project、来源明确的需求版本和 imported 设计版本；fsw_nom 保留为原设定值，不冒充求解结果。
- V1 Review 和快照原样保留，标记旧引擎和规则，不伪装成 V2 验证。
- “实测”字段无原始证据时只标用户填报观测，不伪造 TestRun；未保存的波形结果无法从数据库恢复。
- 手册保留 source_page、test_condition、human_verified；不只靠型号字符串自动绑定项目。
- `(source_system, source_id, source_version)` 用于幂等映射；重复导入不重复创建。
- 并行期不做复杂双向同步。导入对账、完整流程验收和备份后才切默认入口；回退使用保留的 V1 应用和原数据库，不强行把 V2 反写旧 schema。

## 12. 里程碑与开发任务

当前进度与权威顺序见 [MASTER_WORKFLOW.md](MASTER_WORKFLOW.md)。下表定义目标交付，不授权自动执行后续任务，也不承诺未经团队规模和实际执行验证的工期。

| 里程碑 | 交付 | 完成门槛 |
|---|---|---|
| M0 | T01–T03：文档、版本、工况和搜索配置基础 | 范围、归属、不变量和单位可验证 |
| M1 | T04–T10：计算、综合、API、UI、报告和导入 | 正向算例和失败用例走完整流程 |
| M2 | 应力、磁件、器件/BOM、损耗热、控制 | 有来源的可打样设计输出及其限制 |
| M3 | 仿真、实测、测试矩阵与问题处理 | 同版计算/仿真/实测可对照、可复测 |
| M4 | 发布、生产测试和核验案例 | 基线与需求验证证据可追溯 |

| 编号 | 工作内容 | 主要位置 | 依赖 | 验收重点 |
|---|---|---|---|---|
| T01 | 设计、主线、Agent 规范、工程假设和归档 | docs、AGENTS、README | 无 | 不同时强制旧 Phase 与新任务 |
| T02 | Project、RequirementSet、DesignRevision 草稿/冻结 | v2 domain、infrastructure、migration | T01 | 冻结不可覆盖，并发和跨项目约束 |
| T03 | CaseSet、SearchProfile、状态和输入哈希 | v2 domain 与契约测试 | T02 | SI、显式配置、数量与覆盖 |
| T04 | 内核适配和独立基准 | v2 engineering、参考数据与测试 | T01 | 公式、单位、匝比、连接和边界 |
| T05 | 多工况与求解器加固 | 执行器、求解器、CaseResult | T03、T04 | 多根、无解、模型外和数值错误 |
| T06 | 有限综合与筛选 | synthesis、候选与规则 | T05 | 可复算、失败原因、不放宽约束 |
| T07 | 运行持久化、任务与 API | application、api、基础执行器 | T05、T06 | 幂等、取消、重试与部分结果 |
| T08 | 规格、生成、比较与版本页面 | frontend/src/features/v2 | T02、T03、T07 | 无需先输入 Lr/Lm/Cr，上下文一致 |
| T09 | HTML/JSON 计算书与变更提示 | reporting、版本比较 | T07、T08 | 绑定运行、旧报告不变 |
| T10 | V1 导入与整体验收 | migration 工具、端到端测试、文档 | T02–T09 | 幂等、对账、完整参考流程 |

T04 与数据任务可独立排期，不需要微服务或额外代理。每次只实施当前任务并完成相应验证。

## 13. M1 验收与参考基准

### 13.1 用户场景

| 编号 | 场景 | 可观察的结果 |
|---|---|---|
| A01 | 只输入规格并选择有依据的搜索配置 | 候选或明确无解说明，无需预填 Lr/Lm/Cr |
| A02 | 候选反算 | 恢复指定 fr、Zr、Ln、额定 Qe |
| A03 | 输入/负载/容差组合 | 实际数量与 CaseSet 相符，无静默漏点 |
| A04 | 等价单位 | SI 后结果满足声明的数值容差 |
| A05 | 低输入增益不足 | 关联工况与 Mreq/可用范围，不返回通过 |
| A06 | 高输入、轻载或频率上限受限 | 单独检查，不借标称工况通过而忽略 |
| A07 | 空载、启动、缺参数、效率未建模 | 分别标模型外、输入不足、未实现 |
| A08 | 多根、端点、切根和窄峰 | 保留证据，不把漏根称为物理无解证明 |
| A09 | 修改 Lm 建新版本 | 新版提示重算，旧运行与报告不变 |
| A10 | 运行中切换项目/版本 | 结果归属正确，不覆盖当前上下文 |
| A11 | 无候选满足要求 | 保留失败摘要，不自动改约束 |
| A12 | 取消、重启和重复提交 | 状态明确、历史留存、幂等有效 |
| A13 | V1 重复导入 | 不重复创建，未知来源/连接仍未确认 |
| A14 | AI 服务不可用 | 核心综合、分析、比较、报告独立可用 |
| A15 | 重现计算书 | 冻结输入/配置/模型版本可重算主要指标 |

不要求每个规格都返回三套可行方案，准确解释搜索域内未找到可行方案也是正确行为。

### 13.2 基准数据包

1. 独立交叉核验的正向算例：记录来源、连接、规格、参数和预期值。复阻抗实现可与独立推导的归一化增益关系及来源工作点对照，不以同函数输出充当测试答案。
2. 现有 500 W / 48 V 示意项目的负向算例：标为演示/失败基准，不当成已验证参考硬件。
3. 边界与数值包：高输入频率受限、容性根、频率边界、多根、单位错误、容差越界、模型外状态。
4. 软件状态包：冻结、派生、过期提示、并发响应、导入幂等与任务中断。

数值误差界由求解和参考精度确定；工程裕量来自项目要求，不混用。正向 FHA 算例不等于实测参考设计，M3 再加入来源明确的仿真与实测对照。

### 13.3 现有示例复核记录

审阅会话中曾用独立标准库脚本按 V1 文档的理想 FHA 定义复算，不是完整后端或硬件测试：

| 项目 | 数值 |
|---|---|
| Vin / Vout / Pout | 300 / 360 / 420 V；48 V；500 W |
| Lr / Lm / Cr | 45 µH / 300 µH / 47 nF |
| n / 频率搜索范围 | 4；60–150 kHz |
| fr | 约 109.437 kHz |
| Re_rated / Qe_rated | 约 59.762 Ω / 0.51777 |
| 300 V 所需增益 | 1.28 |
| 感性区最大增益 | 有限扫描约 1.07791 |

该记录提示既定理想模型下低输入增益不足；数值扫描不冒充解析极值。T04 应把它整理成有配置、误差界和来源的可复现负向测试。真实旧项目的连接方式仍需确认。

## 14. 文档与开发规范

| 文档 | 职责 |
|---|---|
| README.md | 当前状态、产品主线、现有运行方法和文档入口 |
| MASTER_WORKFLOW.md | M0–M4、T01–T10 和任务状态；旧主线归档 |
| AGENTS.md | 单位、证据、测试、范围与工作流程 |
| DOMAIN_ASSUMPTIONS.md | 副边/匝比、Qe、反算、FHA、容差与来源 |
| API.md、ARCHITECTURE.md、RULES.md | 当前 V1 实现说明；V2 实现时按任务同步 |
| EVALUATION.md | 软件、数值、独立工程参考与硬件验证分开 |
| MIGRATION_V1_V2.md | T10 再建立导入、对账与回退操作说明 |

完成报告说明 Changes、Files、Tests、Verification、Engineering Assumptions、Limitations 和一个 Next Step。不把规划、文档或测试数量当成已实现或已验证的工程能力。

## 15. 已选决策与后续配置

已选定：沿用技术栈、原仓库 V2 分支策略、模块化单体、冻结版本/运行模型、确定性有限综合、中心抽头二极管整流首版模型、M1 规格到方案流程。

| 后续配置 | 何时明确 | 当前处理 |
|---|---|---|
| 实际产品输入/负载/环境 | 创建真实项目 | 不从示例继承为事实 |
| 正向参考设计与搜索预设 | T04–T06、M1 发布前 | 来源与独立核验作为门槛 |
| 真实器件/磁芯资料 | M2 | 先定义来源契约，不编造规格 |
| 第一种仿真工具 | M3 | 统一适配接口，不提前实现多工具 |
| 企业裕量、标准与发布流程 | 实际验证/发布 | 明确配置与来源 |
| 多用户权限和远程部署 | 实际出现需求时 | 不混入 M0–M1 核心重构 |

T01 建立本文及配套主线、规范、工程假设与历史归档。下一项为 **T02：Project、RequirementSet、DesignRevision 草稿与冻结基础**；范围和停止点见 MASTER_WORKFLOW。路线图不是自动继续后续任务的指令。

## 16. 来源与交付边界

固定审阅基线，避免后续 main 变化改变依据：

- [V1 README](https://github.com/zh8426/llc-ai/blob/4ecae6e7ba3e8cd7221c30dbe0d10436534167d1/README.md)
- [工程假设](https://github.com/zh8426/llc-ai/blob/4ecae6e7ba3e8cd7221c30dbe0d10436534167d1/docs/DOMAIN_ASSUMPTIONS.md)
- [项目模型](https://github.com/zh8426/llc-ai/blob/4ecae6e7ba3e8cd7221c30dbe0d10436534167d1/backend/app/models/project.py)
- [评审快照](https://github.com/zh8426/llc-ai/blob/4ecae6e7ba3e8cd7221c30dbe0d10436534167d1/backend/app/models/review.py)
- [工作包络](https://github.com/zh8426/llc-ai/blob/4ecae6e7ba3e8cd7221c30dbe0d10436534167d1/backend/app/engine/operating_envelope.py)
- [波形 API](https://github.com/zh8426/llc-ai/blob/4ecae6e7ba3e8cd7221c30dbe0d10436534167d1/backend/app/api/waveforms.py)
- [手册解析](https://github.com/zh8426/llc-ai/blob/4ecae6e7ba3e8cd7221c30dbe0d10436534167d1/backend/app/datasheet/parser.py)
- [诊断检索](https://github.com/zh8426/llc-ai/blob/4ecae6e7ba3e8cd7221c30dbe0d10436534167d1/backend/app/diagnosis/engine.py)
- [示意项目](https://github.com/zh8426/llc-ai/blob/4ecae6e7ba3e8cd7221c30dbe0d10436534167d1/examples/projects/500w_48v_llc.json)
- [ST AN2450](https://www.st.com/resource/en/application_note/an2450-llc-resonant-halfbridge-converter-design-guideline-stmicroelectronics.pdf)：FHA、ZVS 条件和设计过程的技术参照。本文的产品架构及实施顺序为针对仓库的设计建议，不是文献原文流程。

T01 只交付文档契约和历史归档，不宣称完成 V2 运行时、整套自动测试、仿真、器件选型或硬件验证。
