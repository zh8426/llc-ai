import { useEffect, useMemo, useState } from 'react'

import {
  createProject,
  getLatestReview,
  listProjects,
  reportUrl,
  runReview,
  updateProject,
} from './api'
import type {
  EngineeringQuantity,
  Finding,
  Project,
  ProjectPayload,
  Review,
  Severity,
} from './types'

type ProjectForm = {
  name: string
  vinMin: string
  vinNom: string
  vinMax: string
  vout: string
  pout: string
  efficiencyPercent: string
  lr: string
  lm: string
  cr: string
  fswMin: string
  fswNom: string
  fswMax: string
  transformerRatio: string
  manufacturer: string
  partNumber: string
  vdsRating: string
  controllerModel: string
  controllerFmin: string
  controllerFmax: string
  powerTolerancePercent: string
  vdsMarginPercent: string
}

const emptyForm: ProjectForm = {
  name: '',
  vinMin: '',
  vinNom: '',
  vinMax: '',
  vout: '',
  pout: '',
  efficiencyPercent: '',
  lr: '',
  lm: '',
  cr: '',
  fswMin: '',
  fswNom: '',
  fswMax: '',
  transformerRatio: '',
  manufacturer: '',
  partNumber: '',
  vdsRating: '',
  controllerModel: '',
  controllerFmin: '',
  controllerFmax: '',
  powerTolerancePercent: '',
  vdsMarginPercent: '',
}

const quantityText = (quantity: EngineeringQuantity | null): string =>
  quantity === null ? '' : Number(quantity.value.toPrecision(12)).toString()

const optionalText = (value: string | null): string => value ?? ''

function projectToForm(project: Project): ProjectForm {
  return {
    name: project.name,
    vinMin: quantityText(project.vin_min),
    vinNom: quantityText(project.vin_nom),
    vinMax: quantityText(project.vin_max),
    vout: quantityText(project.vout),
    pout: quantityText(project.pout),
    efficiencyPercent:
      project.target_efficiency === null
        ? ''
        : (project.target_efficiency.value * 100).toString(),
    lr: quantityText(project.lr),
    lm: quantityText(project.lm),
    cr: quantityText(project.cr),
    fswMin: quantityText(project.fsw_min),
    fswNom: quantityText(project.fsw_nom),
    fswMax: quantityText(project.fsw_max),
    transformerRatio: quantityText(project.transformer_ratio),
    manufacturer: optionalText(project.primary_switch.manufacturer),
    partNumber: optionalText(project.primary_switch.part_number),
    vdsRating: quantityText(project.primary_switch.vds_rating),
    controllerModel: optionalText(project.controller.model),
    controllerFmin: quantityText(project.controller.frequency_min),
    controllerFmax: quantityText(project.controller.frequency_max),
    powerTolerancePercent:
      project.review_settings.output_power_relative_tolerance === null
        ? ''
        : (project.review_settings.output_power_relative_tolerance * 100).toString(),
    vdsMarginPercent:
      project.review_settings.measured_vds_required_margin_ratio === null
        ? ''
        : (project.review_settings.measured_vds_required_margin_ratio * 100).toString(),
  }
}

function quantity(value: string, unit: string, label: string): EngineeringQuantity | null {
  const trimmed = value.trim()
  if (trimmed === '') return null
  const parsed = Number(trimmed)
  if (!Number.isFinite(parsed)) throw new Error(`${label} 必须是有限数值。`)
  return { value: parsed, unit }
}

function optionalString(value: string): string | null {
  const normalized = value.trim()
  return normalized === '' ? null : normalized
}

function percentageRatio(value: string, label: string): number | null {
  const parsed = quantity(value, 'percent', label)
  if (parsed === null) return null
  if (parsed.value < 0 || parsed.value >= 100) {
    throw new Error(`${label} 必须处于 0（含）至 100（不含）之间。`)
  }
  return parsed.value / 100
}

function buildPayload(form: ProjectForm): ProjectPayload {
  if (form.name.trim() === '') throw new Error('项目名称不能为空。')
  return {
    name: form.name.trim(),
    vin_min: quantity(form.vinMin, 'V', 'Vin Min'),
    vin_nom: quantity(form.vinNom, 'V', 'Vin Nom'),
    vin_max: quantity(form.vinMax, 'V', 'Vin Max'),
    vout: quantity(form.vout, 'V', 'Vout'),
    pout: quantity(form.pout, 'W', 'Pout'),
    target_efficiency: quantity(
      form.efficiencyPercent,
      'percent',
      '目标效率',
    ),
    lr: quantity(form.lr, 'uH', 'Lr'),
    lm: quantity(form.lm, 'uH', 'Lm'),
    cr: quantity(form.cr, 'nF', 'Cr'),
    fsw_min: quantity(form.fswMin, 'kHz', 'Fsw Min'),
    fsw_nom: quantity(form.fswNom, 'kHz', 'Fsw Nom'),
    fsw_max: quantity(form.fswMax, 'kHz', 'Fsw Max'),
    transformer_ratio: quantity(
      form.transformerRatio,
      'dimensionless',
      '变压器匝比',
    ),
    primary_switch: {
      manufacturer: optionalString(form.manufacturer),
      part_number: optionalString(form.partNumber),
      vds_rating: quantity(form.vdsRating, 'V', 'MOSFET VDS 额定值'),
    },
    controller: {
      model: optionalString(form.controllerModel),
      frequency_min: quantity(form.controllerFmin, 'kHz', '控制器最低频率'),
      frequency_max: quantity(form.controllerFmax, 'kHz', '控制器最高频率'),
    },
    review_settings: {
      output_power_relative_tolerance: percentageRatio(
        form.powerTolerancePercent,
        '输出功率容差',
      ),
      measured_vds_required_margin_ratio: percentageRatio(
        form.vdsMarginPercent,
        '实测 VDS 裕量',
      ),
    },
  }
}

type QuantityFieldProps = {
  label: string
  unit: string
  value: string
  onChange: (value: string) => void
  disabled: boolean
}

function QuantityField({
  label,
  unit,
  value,
  onChange,
  disabled,
}: QuantityFieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <div className="input-with-unit">
        <input
          type="number"
          step="any"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
        />
        <small>{unit}</small>
      </div>
    </label>
  )
}

const severityLabels: Record<Severity, string> = {
  PASS: '通过',
  INFO: '提示',
  WARNING: '警告',
  CRITICAL: '严重',
  INSUFFICIENT_DATA: '数据不足',
}

const categoryLabels: Record<string, string> = {
  input_integrity: '输入数据完整性',
  resonant_tank: '谐振腔',
  power_consistency: '功率一致性',
  primary_switch: '主开关器件',
  resonant_capacitor: '谐振电容',
  control: '控制与频率',
  transformer: '变压器',
  evidence_integrity: '依据完整性',
}

const findingTitleLabels: Record<string, string> = {
  'LLC-R001': '关键参数完整性',
  'LLC-R002': '工程量正值检查',
  'LLC-R003': '输入电压顺序',
  'LLC-R004': '开关频率顺序',
  'LLC-R005': '串联谐振频率',
  'LLC-R006': '低端谐振频率',
  'LLC-R007': '谐振频率与工作范围',
  'LLC-R008': '电感比 Lm/Lr',
  'LLC-R009': '谐振腔特征阻抗',
  'LLC-R010': '输出功率一致性',
  'LLC-R011': 'MOSFET 静态耐压检查',
  'LLC-R012': 'MOSFET 实测 VDS 峰值',
  'LLC-R013': 'MOSFET 电流检查',
  'LLC-R014': '谐振电容耐压检查',
  'LLC-R015': '谐振电容 RMS 电流',
  'LLC-R016': '控制器频率能力',
  'LLC-R017': '死区时间信息',
  'LLC-R018': '变压器匝比要求',
  'LLC-R019': '增益评审前置条件',
  'LLC-R020': '依据完整性检查',
}

const evidenceSourceLabels: Record<string, string> = {
  user_input: '用户输入',
  calculation: '确定性计算',
  datasheet: '数据手册',
  waveform: '波形',
  rule_definition: '规则定义',
  verified_fault_case: '已验证故障案例',
}

const dataLabels: Record<string, string> = {
  vin_min: '最小输入电压 Vin Min',
  vin_nom: '标称输入电压 Vin Nom',
  vin_max: '最大输入电压 Vin Max',
  vout: '输出电压 Vout',
  iout: '输出电流 Iout',
  pout: '输出功率 Pout',
  target_efficiency: '目标效率',
  lr: '谐振电感 Lr',
  lm: '励磁电感 Lm',
  cr: '谐振电容 Cr',
  fsw_min: '最低开关频率 Fsw Min',
  fsw_max: '最高开关频率 Fsw Max',
  transformer_ratio: '变压器匝比',
  dead_time: '死区时间',
  resonant_frequency: '串联谐振频率 fr',
  lower_resonant_frequency: '低端谐振频率 fp',
  characteristic_impedance: '谐振腔特征阻抗 Zr',
  lm_lr_ratio: '电感比 Lm/Lr',
  output_current: '输出电流 Iout',
  input_power: '输入功率 Pin',
  mosfet_vds_rating: 'MOSFET VDS 额定值',
  measured_vds_peak: '实测 VDS 峰值',
  measured_vds_margin_ratio: '实测 VDS 裕量',
  current_rating: '器件电流额定值',
  current_temperature_condition: '电流额定值温度条件',
  measured_peak_current: '实测峰值电流',
  capacitor_voltage_rating: '谐振电容额定电压',
  capacitor_voltage_stress: '谐振电容电压应力',
  capacitor_rms_current_rating: '谐振电容 RMS 电流额定值',
  capacitor_rms_current_stress: '谐振电容 RMS 电流应力',
  frequency_min: '最低频率',
  frequency_max: '最高频率',
  output_power_relative_tolerance: '输出功率容差',
  measured_vds_required_margin_ratio: '实测 VDS 裕量要求',
}

function dataLabel(name: string): string {
  const leafName = name.split('.').at(-1) ?? name
  const normalized = leafName.startsWith('valid_') ? leafName.slice(6) : leafName
  return dataLabels[name] ?? dataLabels[normalized] ?? normalized.replaceAll('_', ' ')
}

function isQuantity(value: unknown): value is EngineeringQuantity {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as Record<string, unknown>
  return typeof candidate.value === 'number' && typeof candidate.unit === 'string'
}

function formatQuantity(value: EngineeringQuantity): string {
  return `${Number(value.value.toPrecision(8))} ${value.unit}`
}

function formatCalculatedValue(value: unknown): string {
  if (!isQuantity(value)) return String(value)
  const candidate = value as EngineeringQuantity & { formula_version?: string }
  return candidate.formula_version
    ? `${formatQuantity(candidate)}（计算公式版本：${candidate.formula_version}）`
    : formatQuantity(candidate)
}

function inputData(finding: Finding): Array<[string, EngineeringQuantity]> {
  const values = new Map<string, EngineeringQuantity>()
  finding.evidence
    .filter((item) => item.source === 'user_input')
    .forEach((item) => {
      Object.entries(item.values).forEach(([name, value]) => values.set(name, value))
    })
  return [...values.entries()]
}

function DataList({ values }: { values: Array<[string, EngineeringQuantity]> }) {
  if (values.length === 0) return <p className="empty-detail">无直接用户输入数据。</p>
  return (
    <dl className="data-list">
      {values.map(([name, value]) => (
        <div key={name}>
          <dt>{dataLabel(name)}</dt>
          <dd>{formatQuantity(value)}</dd>
        </div>
      ))}
    </dl>
  )
}

function FindingCard({ finding }: { finding: Finding }) {
  const inputs = inputData(finding)
  const calculated = Object.entries(finding.calculated_values)
  return (
    <details className={`finding finding-${finding.severity.toLowerCase()}`}>
      <summary>
        <span className="rule-id">{finding.rule_id}</span>
        <strong>{findingTitleLabels[finding.rule_id] ?? finding.title}</strong>
        <span className={`severity severity-${finding.severity.toLowerCase()}`}>
          {severityLabels[finding.severity]}
        </span>
      </summary>
      <div className="finding-body">
        <section>
          <h4>为什么</h4>
          <p>{finding.description}</p>
        </section>

        <section>
          <h4>输入数据</h4>
          <DataList values={inputs} />
        </section>

        <section>
          <h4>计算数据</h4>
          {calculated.length === 0 ? (
            <p className="empty-detail">本评审项没有单独的计算结果。</p>
          ) : (
            <dl className="data-list">
              {calculated.map(([name, value]) => (
                <div key={name}>
                  <dt>{dataLabel(name)}</dt>
                  <dd>{formatCalculatedValue(value)}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>

        <section>
          <h4>依据</h4>
          {finding.evidence.length === 0 ? (
            <p className="empty-detail">未提供依据。</p>
          ) : (
            <ul>
              {finding.evidence.map((item, index) => (
                <li key={`${item.source}-${index}`}>
                  <strong>{evidenceSourceLabels[item.source] ?? item.source}</strong>
                  {' — '}
                  {item.description}
                  {Object.keys(item.values).length > 0 && (
                    <dl className="data-list compact-data-list">
                      {Object.entries(item.values).map(([name, value]) => (
                        <div key={name}>
                          <dt>{dataLabel(name)}</dt>
                          <dd>{formatQuantity(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h4>缺失信息</h4>
          {finding.missing_information.length === 0 ? (
            <p className="empty-detail">无。</p>
          ) : (
            <ul>
              {finding.missing_information.map((item) => (
                <li key={item}>{dataLabel(item)}</li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h4>建议下一步</h4>
          {finding.recommended_action.length === 0 ? (
            <p className="empty-detail">暂无额外建议。</p>
          ) : (
            <ul>
              {finding.recommended_action.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </section>

        <p className="finding-trace">规则编号：{finding.rule_id}</p>

        {finding.requires_engineer_confirmation && (
          <p className="confirmation">需要具备相应资质的工程师确认。</p>
        )}
      </div>
    </details>
  )
}

function ReviewPanel({ review }: { review: Review }) {
  const grouped = useMemo(() => {
    return review.findings.reduce<Record<string, Finding[]>>((result, finding) => {
      const category = finding.category
      result[category] = [...(result[category] ?? []), finding]
      return result
    }, {})
  }, [review])

  const summary = [
    ['通过', review.summary.pass, 'pass'],
    ['提示', review.summary.info, 'info'],
    ['警告', review.summary.warning, 'warning'],
    ['严重', review.summary.critical, 'critical'],
    ['数据不足', review.summary.insufficient_data, 'insufficient_data'],
  ] as const

  return (
    <section className="review-panel" aria-labelledby="review-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">确定性规则引擎</p>
          <h2 id="review-title">设计评审结果</h2>
        </div>
        <div className="review-actions">
          <time>{new Date(review.created_at).toLocaleString()}</time>
          <a
            className="report-link"
            href={reportUrl(review.project_id)}
            target="_blank"
            rel="noreferrer"
          >
            查看中文 HTML 报告
          </a>
        </div>
      </div>

      <div className="summary-grid">
        {summary.map(([label, count, key]) => (
          <article className={`summary-card summary-${key}`} key={key}>
            <span>{label}</span>
            <strong>{count}</strong>
          </article>
        ))}
      </div>

      <p className="review-disclaimer">
        “通过”仅表示对应有限规则检查通过，不代表设计安全、合规或可以量产。
      </p>

      <div className="finding-groups">
        {Object.entries(grouped).map(([category, findings]) => (
          <section className="finding-group" key={category}>
            <h3>{categoryLabels[category] ?? category.replaceAll('_', ' ')}</h3>
            {findings.map((finding) => (
              <FindingCard finding={finding} key={finding.rule_id} />
            ))}
          </section>
        ))}
      </div>
    </section>
  )
}

function App() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [form, setForm] = useState<ProjectForm>(emptyForm)
  const [review, setReview] = useState<Review | null>(null)
  const [newProjectName, setNewProjectName] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('正在连接后端服务…')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    void listProjects()
      .then(async (items) => {
        if (!active) return
        setProjects(items)
        if (items.length === 0) {
          setNotice('新建一个项目后即可开始设计评审。')
          return
        }
        const first = items[0]
        setSelectedProject(first)
        setForm(projectToForm(first))
        setReview(await getLatestReview(first.id))
        setNotice('项目已加载。')
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError(reason instanceof Error ? reason.message : '无法连接后端服务。')
        setNotice('请确认后端服务已在 127.0.0.1:8000 启动。')
      })
    return () => {
      active = false
    }
  }, [])

  function updateForm(field: keyof ProjectForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function openProject(project: Project) {
    setSelectedProject(project)
    setForm(projectToForm(project))
    setReview(null)
    setError('')
    setNotice('正在加载最近一次评审…')
    try {
      setReview(await getLatestReview(project.id))
      setNotice('项目已加载。')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '评审加载失败。')
    }
  }

  async function handleCreateProject() {
    if (newProjectName.trim() === '') {
      setError('请输入项目名称。')
      return
    }
    setBusy(true)
    setError('')
    try {
      const project = await createProject(newProjectName.trim())
      setProjects((current) => [project, ...current])
      setNewProjectName('')
      setSelectedProject(project)
      setForm(projectToForm(project))
      setReview(null)
      setNotice('项目已创建，请填写设计参数。')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '项目创建失败。')
    } finally {
      setBusy(false)
    }
  }

  async function saveProject(): Promise<Project | null> {
    if (selectedProject === null) return null
    setBusy(true)
    setError('')
    try {
      const updated = await updateProject(selectedProject.id, buildPayload(form))
      setSelectedProject(updated)
      setForm(projectToForm(updated))
      setProjects((current) =>
        current.map((project) => (project.id === updated.id ? updated : project)),
      )
      setNotice('项目参数已保存。')
      return updated
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '项目保存失败。')
      return null
    } finally {
      setBusy(false)
    }
  }

  async function saveAndRunReview() {
    const updated = await saveProject()
    if (updated === null) return
    setBusy(true)
    setError('')
    setNotice('正在执行 R001–R020…')
    try {
      setReview(await runReview(updated.id))
      setNotice('设计评审已完成。')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '评审执行失败。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="app-shell">
      <aside className="project-sidebar">
        <div className="brand">
          <span>LLC</span>
          <div>
            <strong>工程评审助手</strong>
            <small>Half-Bridge LLC 设计评审</small>
          </div>
        </div>

        <form
          className="create-project"
          onSubmit={(event) => {
            event.preventDefault()
            void handleCreateProject()
          }}
        >
          <label htmlFor="new-project">新建项目</label>
          <div>
            <input
              id="new-project"
              value={newProjectName}
              onChange={(event) => setNewProjectName(event.target.value)}
              placeholder="输入项目名称"
              disabled={busy}
            />
            <button type="submit" disabled={busy} aria-label="创建项目">
              +
            </button>
          </div>
        </form>

        <nav aria-label="项目列表">
          <p className="nav-label">项目</p>
          {projects.length === 0 && <p className="empty-list">暂无项目。</p>}
          {projects.map((project) => (
            <button
              className={project.id === selectedProject?.id ? 'project-active' : ''}
              key={project.id}
              onClick={() => void openProject(project)}
              type="button"
            >
              <strong>{project.name}</strong>
              <small>{project.topology}</small>
            </button>
          ))}
        </nav>
      </aside>

      <div className="workspace">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">项目 → 保存 → 评审 → 查看结论</p>
            <h1>{selectedProject?.name ?? 'LLC 设计评审'}</h1>
          </div>
          <div className="status-area" aria-live="polite">
            <span className={error === '' ? 'status-dot' : 'status-dot status-error'} />
            <span>{error || notice}</span>
          </div>
        </header>

        {selectedProject === null ? (
          <section className="empty-state">
            <p className="eyebrow">LLC 设计评审</p>
            <h2>新建第一个 LLC 项目</h2>
            <p>
              使用左侧输入框创建项目，然后填写带单位的设计参数并运行确定性评审。
            </p>
          </section>
        ) : (
          <>
            <section className="editor-panel" aria-labelledby="editor-title">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">结构化工程数据</p>
                  <h2 id="editor-title">设计参数</h2>
                </div>
                <div className="editor-actions">
                  <button
                    className="button-secondary"
                    onClick={() => void saveProject()}
                    disabled={busy}
                    type="button"
                  >
                    保存
                  </button>
                  <button
                    className="button-primary"
                    onClick={() => void saveAndRunReview()}
                    disabled={busy}
                    type="button"
                  >
                    {busy ? '处理中…' : '保存并开始评审'}
                  </button>
                </div>
              </div>

              <div className="form-section">
                <h3>基本规格</h3>
                <div className="form-grid">
                  <label className="field field-wide">
                    <span>项目名称</span>
                    <input
                      value={form.name}
                      onChange={(event) => updateForm('name', event.target.value)}
                      disabled={busy}
                    />
                  </label>
                  <QuantityField label="最小输入电压 Vin Min" unit="V" value={form.vinMin} onChange={(value) => updateForm('vinMin', value)} disabled={busy} />
                  <QuantityField label="标称输入电压 Vin Nom" unit="V" value={form.vinNom} onChange={(value) => updateForm('vinNom', value)} disabled={busy} />
                  <QuantityField label="最大输入电压 Vin Max" unit="V" value={form.vinMax} onChange={(value) => updateForm('vinMax', value)} disabled={busy} />
                  <QuantityField label="输出电压 Vout" unit="V" value={form.vout} onChange={(value) => updateForm('vout', value)} disabled={busy} />
                  <QuantityField label="输出功率 Pout" unit="W" value={form.pout} onChange={(value) => updateForm('pout', value)} disabled={busy} />
                  <QuantityField label="目标效率" unit="%" value={form.efficiencyPercent} onChange={(value) => updateForm('efficiencyPercent', value)} disabled={busy} />
                </div>
              </div>

              <div className="form-section">
                <h3>谐振腔</h3>
                <div className="form-grid">
                  <QuantityField label="谐振电感 Lr" unit="µH" value={form.lr} onChange={(value) => updateForm('lr', value)} disabled={busy} />
                  <QuantityField label="励磁电感 Lm" unit="µH" value={form.lm} onChange={(value) => updateForm('lm', value)} disabled={busy} />
                  <QuantityField label="谐振电容 Cr" unit="nF" value={form.cr} onChange={(value) => updateForm('cr', value)} disabled={busy} />
                </div>
              </div>

              <div className="form-section">
                <h3>开关频率与变压器</h3>
                <div className="form-grid">
                  <QuantityField label="最低开关频率 Fsw Min" unit="kHz" value={form.fswMin} onChange={(value) => updateForm('fswMin', value)} disabled={busy} />
                  <QuantityField label="标称开关频率 Fsw Nom" unit="kHz" value={form.fswNom} onChange={(value) => updateForm('fswNom', value)} disabled={busy} />
                  <QuantityField label="最高开关频率 Fsw Max" unit="kHz" value={form.fswMax} onChange={(value) => updateForm('fswMax', value)} disabled={busy} />
                  <QuantityField label="变压器匝比" unit="ratio" value={form.transformerRatio} onChange={(value) => updateForm('transformerRatio', value)} disabled={busy} />
                </div>
              </div>

              <div className="form-section">
                <h3>主开关器件与控制器</h3>
                <div className="form-grid">
                  <label className="field">
                    <span>制造商</span>
                    <input value={form.manufacturer} onChange={(event) => updateForm('manufacturer', event.target.value)} disabled={busy} />
                  </label>
                  <label className="field">
                    <span>器件型号</span>
                    <input value={form.partNumber} onChange={(event) => updateForm('partNumber', event.target.value)} disabled={busy} />
                  </label>
                  <QuantityField label="MOSFET VDS 额定值" unit="V" value={form.vdsRating} onChange={(value) => updateForm('vdsRating', value)} disabled={busy} />
                  <label className="field">
                    <span>控制器型号</span>
                    <input value={form.controllerModel} onChange={(event) => updateForm('controllerModel', event.target.value)} disabled={busy} />
                  </label>
                  <QuantityField label="控制器最低频率" unit="kHz" value={form.controllerFmin} onChange={(value) => updateForm('controllerFmin', value)} disabled={busy} />
                  <QuantityField label="控制器最高频率" unit="kHz" value={form.controllerFmax} onChange={(value) => updateForm('controllerFmax', value)} disabled={busy} />
                </div>
              </div>

              <div className="form-section">
                <h3>项目评审设置</h3>
                <p className="section-note">留空表示没有项目批准的阈值；系统不会自动补充通用裕量。</p>
                <div className="form-grid">
                  <QuantityField label="输出功率容差" unit="%" value={form.powerTolerancePercent} onChange={(value) => updateForm('powerTolerancePercent', value)} disabled={busy} />
                  <QuantityField label="实测 VDS 裕量" unit="%" value={form.vdsMarginPercent} onChange={(value) => updateForm('vdsMarginPercent', value)} disabled={busy} />
                </div>
              </div>
            </section>

            {review === null ? (
              <section className="review-placeholder">
                <p className="eyebrow">暂无评审结果</p>
                <h2>保存参数并运行 R001–R020</h2>
                <p>缺少的数据将明确显示为“数据不足”，不会由系统猜测。</p>
              </section>
            ) : (
              <ReviewPanel review={review} />
            )}
          </>
        )}
      </div>
    </main>
  )
}

export default App
