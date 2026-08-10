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
  if (form.name.trim() === '') throw new Error('Project Name 不能为空。')
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
      'Target Efficiency',
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
      'Transformer Ratio',
    ),
    primary_switch: {
      manufacturer: optionalString(form.manufacturer),
      part_number: optionalString(form.partNumber),
      vds_rating: quantity(form.vdsRating, 'V', 'MOSFET VDS Rating'),
    },
    controller: {
      model: optionalString(form.controllerModel),
      frequency_min: quantity(form.controllerFmin, 'kHz', 'Controller Fmin'),
      frequency_max: quantity(form.controllerFmax, 'kHz', 'Controller Fmax'),
    },
    review_settings: {
      output_power_relative_tolerance: percentageRatio(
        form.powerTolerancePercent,
        'Output Power Tolerance',
      ),
      measured_vds_required_margin_ratio: percentageRatio(
        form.vdsMarginPercent,
        'Measured VDS Margin',
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
  PASS: 'PASS',
  INFO: 'INFO',
  WARNING: 'WARNING',
  CRITICAL: 'CRITICAL',
  INSUFFICIENT_DATA: 'INSUFFICIENT DATA',
}

function FindingCard({ finding }: { finding: Finding }) {
  return (
    <details className={`finding finding-${finding.severity.toLowerCase()}`}>
      <summary>
        <span className="rule-id">{finding.rule_id}</span>
        <strong>{finding.title}</strong>
        <span className={`severity severity-${finding.severity.toLowerCase()}`}>
          {severityLabels[finding.severity]}
        </span>
      </summary>
      <div className="finding-body">
        <section>
          <h4>Why</h4>
          <p>{finding.description}</p>
        </section>

        {Object.keys(finding.calculated_values).length > 0 && (
          <section>
            <h4>Calculated Data</h4>
            <pre>{JSON.stringify(finding.calculated_values, null, 2)}</pre>
          </section>
        )}

        {finding.evidence.length > 0 && (
          <section>
            <h4>Evidence</h4>
            <ul>
              {finding.evidence.map((item, index) => (
                <li key={`${item.source}-${index}`}>
                  <strong>{item.source}</strong> — {item.description}
                  {Object.keys(item.values).length > 0 && (
                    <code>{JSON.stringify(item.values)}</code>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {finding.missing_information.length > 0 && (
          <section>
            <h4>Missing Information</h4>
            <ul>
              {finding.missing_information.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        )}

        {finding.recommended_action.length > 0 && (
          <section>
            <h4>Recommended Next Step</h4>
            <ul>
              {finding.recommended_action.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        )}

        {finding.requires_engineer_confirmation && (
          <p className="confirmation">Requires qualified engineer review.</p>
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
    ['PASS', review.summary.pass, 'pass'],
    ['INFO', review.summary.info, 'info'],
    ['WARNING', review.summary.warning, 'warning'],
    ['CRITICAL', review.summary.critical, 'critical'],
    ['INSUFFICIENT DATA', review.summary.insufficient_data, 'insufficient_data'],
  ] as const

  return (
    <section className="review-panel" aria-labelledby="review-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">DETERMINISTIC RULE ENGINE</p>
          <h2 id="review-title">Design Review</h2>
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
        PASS 仅表示对应有限规则通过，不代表设计安全、合规或可以量产。
      </p>

      <div className="finding-groups">
        {Object.entries(grouped).map(([category, findings]) => (
          <section className="finding-group" key={category}>
            <h3>{category.replaceAll('_', ' ')}</h3>
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
  const [notice, setNotice] = useState('正在连接 Backend…')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    void listProjects()
      .then(async (items) => {
        if (!active) return
        setProjects(items)
        if (items.length === 0) {
          setNotice('创建一个 Project 开始设计评审。')
          return
        }
        const first = items[0]
        setSelectedProject(first)
        setForm(projectToForm(first))
        setReview(await getLatestReview(first.id))
        setNotice('Project 已加载。')
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError(reason instanceof Error ? reason.message : '无法连接 Backend。')
        setNotice('请确认 Backend 已在 127.0.0.1:8000 启动。')
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
    setNotice('正在加载最近一次 Review…')
    try {
      setReview(await getLatestReview(project.id))
      setNotice('Project 已加载。')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Review 加载失败。')
    }
  }

  async function handleCreateProject() {
    if (newProjectName.trim() === '') {
      setError('请输入 Project Name。')
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
      setNotice('Project 已创建，请填写参数。')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Project 创建失败。')
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
      setNotice('Project 参数已保存。')
      return updated
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Project 保存失败。')
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
      setNotice('Design Review 已完成。')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Review 执行失败。')
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
            <strong>Engineering Assistant</strong>
            <small>Half-Bridge · Phase 3</small>
          </div>
        </div>

        <form
          className="create-project"
          onSubmit={(event) => {
            event.preventDefault()
            void handleCreateProject()
          }}
        >
          <label htmlFor="new-project">New Project</label>
          <div>
            <input
              id="new-project"
              value={newProjectName}
              onChange={(event) => setNewProjectName(event.target.value)}
              placeholder="Project name"
              disabled={busy}
            />
            <button type="submit" disabled={busy} aria-label="Create project">
              +
            </button>
          </div>
        </form>

        <nav aria-label="Projects">
          <p className="nav-label">PROJECTS</p>
          {projects.length === 0 && <p className="empty-list">No projects yet.</p>}
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
            <p className="eyebrow">PROJECT → SAVE → REVIEW → FINDINGS</p>
            <h1>{selectedProject?.name ?? 'LLC Design Review'}</h1>
          </div>
          <div className="status-area" aria-live="polite">
            <span className={error === '' ? 'status-dot' : 'status-dot status-error'} />
            <span>{error || notice}</span>
          </div>
        </header>

        {selectedProject === null ? (
          <section className="empty-state">
            <p className="eyebrow">PHASE 3</p>
            <h2>Create your first LLC project</h2>
            <p>
              使用左侧输入框创建 Project，然后填写带单位的设计参数并运行确定性评审。
            </p>
          </section>
        ) : (
          <>
            <section className="editor-panel" aria-labelledby="editor-title">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">STRUCTURED ENGINEERING DATA</p>
                  <h2 id="editor-title">Project Editor</h2>
                </div>
                <div className="editor-actions">
                  <button
                    className="button-secondary"
                    onClick={() => void saveProject()}
                    disabled={busy}
                    type="button"
                  >
                    Save
                  </button>
                  <button
                    className="button-primary"
                    onClick={() => void saveAndRunReview()}
                    disabled={busy}
                    type="button"
                  >
                    {busy ? 'Working…' : 'Save & Run Review'}
                  </button>
                </div>
              </div>

              <div className="form-section">
                <h3>Basic</h3>
                <div className="form-grid">
                  <label className="field field-wide">
                    <span>Project Name</span>
                    <input
                      value={form.name}
                      onChange={(event) => updateForm('name', event.target.value)}
                      disabled={busy}
                    />
                  </label>
                  <QuantityField label="Vin Min" unit="V" value={form.vinMin} onChange={(value) => updateForm('vinMin', value)} disabled={busy} />
                  <QuantityField label="Vin Nom" unit="V" value={form.vinNom} onChange={(value) => updateForm('vinNom', value)} disabled={busy} />
                  <QuantityField label="Vin Max" unit="V" value={form.vinMax} onChange={(value) => updateForm('vinMax', value)} disabled={busy} />
                  <QuantityField label="Vout" unit="V" value={form.vout} onChange={(value) => updateForm('vout', value)} disabled={busy} />
                  <QuantityField label="Pout" unit="W" value={form.pout} onChange={(value) => updateForm('pout', value)} disabled={busy} />
                  <QuantityField label="Target Efficiency" unit="%" value={form.efficiencyPercent} onChange={(value) => updateForm('efficiencyPercent', value)} disabled={busy} />
                </div>
              </div>

              <div className="form-section">
                <h3>Resonant Tank</h3>
                <div className="form-grid">
                  <QuantityField label="Lr" unit="µH" value={form.lr} onChange={(value) => updateForm('lr', value)} disabled={busy} />
                  <QuantityField label="Lm" unit="µH" value={form.lm} onChange={(value) => updateForm('lm', value)} disabled={busy} />
                  <QuantityField label="Cr" unit="nF" value={form.cr} onChange={(value) => updateForm('cr', value)} disabled={busy} />
                </div>
              </div>

              <div className="form-section">
                <h3>Frequency & Transformer</h3>
                <div className="form-grid">
                  <QuantityField label="Fsw Min" unit="kHz" value={form.fswMin} onChange={(value) => updateForm('fswMin', value)} disabled={busy} />
                  <QuantityField label="Fsw Nom" unit="kHz" value={form.fswNom} onChange={(value) => updateForm('fswNom', value)} disabled={busy} />
                  <QuantityField label="Fsw Max" unit="kHz" value={form.fswMax} onChange={(value) => updateForm('fswMax', value)} disabled={busy} />
                  <QuantityField label="Turns Ratio" unit="ratio" value={form.transformerRatio} onChange={(value) => updateForm('transformerRatio', value)} disabled={busy} />
                </div>
              </div>

              <div className="form-section">
                <h3>Primary Switch & Controller</h3>
                <div className="form-grid">
                  <label className="field">
                    <span>Manufacturer</span>
                    <input value={form.manufacturer} onChange={(event) => updateForm('manufacturer', event.target.value)} disabled={busy} />
                  </label>
                  <label className="field">
                    <span>Part Number</span>
                    <input value={form.partNumber} onChange={(event) => updateForm('partNumber', event.target.value)} disabled={busy} />
                  </label>
                  <QuantityField label="VDS Rating" unit="V" value={form.vdsRating} onChange={(value) => updateForm('vdsRating', value)} disabled={busy} />
                  <label className="field">
                    <span>Controller Model</span>
                    <input value={form.controllerModel} onChange={(event) => updateForm('controllerModel', event.target.value)} disabled={busy} />
                  </label>
                  <QuantityField label="Controller Fmin" unit="kHz" value={form.controllerFmin} onChange={(value) => updateForm('controllerFmin', value)} disabled={busy} />
                  <QuantityField label="Controller Fmax" unit="kHz" value={form.controllerFmax} onChange={(value) => updateForm('controllerFmax', value)} disabled={busy} />
                </div>
              </div>

              <div className="form-section">
                <h3>Project Review Settings</h3>
                <p className="section-note">留空表示没有项目批准的阈值；系统不会自动补充通用裕量。</p>
                <div className="form-grid">
                  <QuantityField label="Output Power Tolerance" unit="%" value={form.powerTolerancePercent} onChange={(value) => updateForm('powerTolerancePercent', value)} disabled={busy} />
                  <QuantityField label="Measured VDS Margin" unit="%" value={form.vdsMarginPercent} onChange={(value) => updateForm('vdsMarginPercent', value)} disabled={busy} />
                </div>
              </div>
            </section>

            {review === null ? (
              <section className="review-placeholder">
                <p className="eyebrow">NO REVIEW RESULT</p>
                <h2>Save parameters and run R001–R020</h2>
                <p>缺少的数据将明确显示为 INSUFFICIENT_DATA，不会由系统猜测。</p>
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
