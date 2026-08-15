import { useEffect, useMemo, useState } from 'react'

import {
  analyzeZVS,
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
  WaveformAnalysisRequest,
  WaveformChannelMetadata,
  ZVSAnalysis,
  ZVSStatus,
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

type PlotData = {
  time: number[]
  channels: Record<string, number[]>
}

const waveformStatusLabels: Record<ZVSStatus, string> = {
  LIKELY_ZVS: '可能为 ZVS',
  PARTIAL_ZVS: '部分 ZVS',
  LIKELY_HARD_SWITCHING: '可能硬开关',
  INSUFFICIENT_DATA: '数据不足',
}

function parsePlotData(csvText: string): PlotData {
  const lines = csvText.trim().split(/\r?\n/).filter(Boolean)
  if (lines.length < 2) throw new Error('CSV 至少需要表头和一行采样数据。')
  const headers = lines[0].split(',').map((header) => header.trim())
  const required = ['time', 'VGS_Q1', 'VDS_Q1', 'IRES']
  const indexes = Object.fromEntries(
    required.map((name) => [name, headers.indexOf(name)]),
  )
  if (Object.values(indexes).some((index) => index < 0)) {
    throw new Error('CSV 必须包含 time、VGS_Q1、VDS_Q1、IRES 列。')
  }
  const rawRows = lines.slice(1).map((line) => line.split(',').map(Number))
  const validRows = rawRows.filter((row) =>
    required.every((name) => Number.isFinite(row[indexes[name]])),
  )
  const stride = Math.max(1, Math.ceil(validRows.length / 700))
  const rows = validRows.filter((_, index) => index % stride === 0)
  return {
    time: rows.map((row) => row[indexes.time]),
    channels: Object.fromEntries(
      required.slice(1).map((name) => [
        name,
        rows.map((row) => row[indexes[name]]),
      ]),
    ),
  }
}

const waveformColors: Record<string, string> = {
  VGS_Q1: '#207d5d',
  VDS_Q1: '#bc6b2e',
  IRES: '#3f6ea8',
}

function WaveformPlot({
  csvText,
  result,
  selectedCycle,
}: {
  csvText: string
  result: ZVSAnalysis
  selectedCycle: number
}) {
  const plot = useMemo(() => parsePlotData(csvText), [csvText])
  const width = 780
  const laneHeight = 86
  const height = laneHeight * 3
  const firstTime = plot.time[0] ?? 0
  const lastTime = plot.time.at(-1) ?? firstTime + 1
  const timeSpan = Math.max(lastTime - firstTime, Number.EPSILON)
  const xFor = (timestamp: number) =>
    ((timestamp - firstTime) / timeSpan) * width
  const selectedStart = result.gate_turn_on_timestamps[selectedCycle]
  const selectedEnd =
    result.gate_turn_on_timestamps[selectedCycle + 1] ?? lastTime

  function pathFor(values: number[], lane: number): string {
    const minimum = Math.min(...values)
    const maximum = Math.max(...values)
    const span = Math.max(maximum - minimum, Number.EPSILON)
    return values
      .map((value, index) => {
        const x = (index / Math.max(values.length - 1, 1)) * width
        const y = lane * laneHeight + 14 + (1 - (value - minimum) / span) * 54
        return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
      })
      .join(' ')
  }

  return (
    <div className="waveform-chart-wrap">
      <svg
        className="waveform-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="VGS、VDS、谐振电流波形及门极时刻"
      >
        {selectedStart !== undefined && (
          <rect
            x={xFor(selectedStart)}
            y="0"
            width={Math.max(xFor(selectedEnd) - xFor(selectedStart), 1)}
            height={height}
            className="waveform-selected-cycle"
          />
        )}
        {['VGS_Q1', 'VDS_Q1', 'IRES'].map((name, lane) => (
          <g key={name}>
            <line
              x1="0"
              x2={width}
              y1={lane * laneHeight + 73}
              y2={lane * laneHeight + 73}
              className="waveform-gridline"
            />
            <text x="10" y={lane * laneHeight + 20} className="waveform-label">
              {name}
            </text>
            <path
              d={pathFor(plot.channels[name], lane)}
              fill="none"
              stroke={waveformColors[name]}
              strokeWidth="1.7"
            />
          </g>
        ))}
        {result.gate_turn_on_timestamps.map((timestamp, index) => (
          <line
            key={`on-${index}`}
            x1={xFor(timestamp)}
            x2={xFor(timestamp)}
            y1="0"
            y2={height}
            className="waveform-marker waveform-marker-on"
          />
        ))}
        {result.gate_turn_off_timestamps.map((timestamp, index) => (
          <line
            key={`off-${index}`}
            x1={xFor(timestamp)}
            x2={xFor(timestamp)}
            y1="0"
            y2={height}
            className="waveform-marker waveform-marker-off"
          />
        ))}
        {result.dead_time.evidence.map((evidence, index) => (
          <line
            key={`dead-${index}`}
            x1={xFor(evidence.primary_turn_off_time)}
            x2={xFor(evidence.complementary_turn_on_time)}
            y1={height - 9}
            y2={height - 9}
            className="waveform-dead-time"
          />
        ))}
      </svg>
      <div className="waveform-legend">
        <span><i className="legend-on" />Gate turn-on</span>
        <span><i className="legend-off" />Gate turn-off</span>
        <span><i className="legend-dead" />Dead time</span>
      </div>
    </div>
  )
}

function WaveformPanel() {
  const [file, setFile] = useState<File | null>(null)
  const [csvText, setCsvText] = useState('')
  const [result, setResult] = useState<ZVSAnalysis | null>(null)
  const [selectedCycle, setSelectedCycle] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [sampleRate, setSampleRate] = useState('10000000')
  const [timeUnit, setTimeUnit] = useState('s')
  const [vdsZvsThreshold, setVdsZvsThreshold] = useState('10')
  const [vdsHardThreshold, setVdsHardThreshold] = useState('300')
  const [gateLowThreshold, setGateLowThreshold] = useState('')
  const [gateHighThreshold, setGateHighThreshold] = useState('')
  const [testVin, setTestVin] = useState('400 VDC')
  const [testLoad, setTestLoad] = useState('500 W')
  const [includeQ2, setIncludeQ2] = useState(false)
  const [channelSettings, setChannelSettings] = useState<
    Record<string, WaveformChannelMetadata>
  >({
    VGS_Q1: { unit: 'V', probe_ratio: 1, polarity: 1 },
    VDS_Q1: { unit: 'V', probe_ratio: 1, polarity: 1 },
    IRES: { unit: 'A', probe_ratio: 1, polarity: 1 },
  })

  async function selectFile(selected: File | undefined) {
    if (selected === undefined) return
    setFile(selected)
    setResult(null)
    setError('')
    setCsvText(await selected.text())
  }

  function updateChannel(
    name: string,
    field: keyof WaveformChannelMetadata,
    value: string,
  ) {
    const current = channelSettings[name]
    if (current === undefined) return
    const nextValue: WaveformChannelMetadata[keyof WaveformChannelMetadata] =
      field === 'probe_ratio'
        ? Number(value)
        : field === 'polarity'
          ? (Number(value) as 1 | -1)
          : value
    setChannelSettings((current) => ({
      ...current,
      [name]: {
        ...current[name],
        [field]: nextValue,
      },
    }))
  }

  async function submit() {
    if (file === null) {
      setError('请先选择 CSV 文件。')
      return
    }
    if ((gateLowThreshold.trim() === '') !== (gateHighThreshold.trim() === '')) {
      setError('门极低阈值和高阈值必须同时填写，或同时留空使用自动阈值。')
      return
    }
    const parsed = (value: string, label: string): number => {
      const number = Number(value)
      if (!Number.isFinite(number)) throw new Error(`${label} 必须是有限数值。`)
      return number
    }
    try {
      const channels = { ...channelSettings }
      if (includeQ2) channels.VGS_Q2 = { unit: 'V', probe_ratio: 1, polarity: 1 }
      const request: WaveformAnalysisRequest = {
        file,
        sampleRate: parsed(sampleRate, '采样率'),
        timeUnit: timeUnit.trim(),
        channels,
        testCondition: { vin: testVin.trim(), load: testLoad.trim() },
        vdsZvsThreshold: parsed(vdsZvsThreshold, 'ZVS VDS 阈值'),
        vdsHardSwitchingThreshold: parsed(vdsHardThreshold, '硬开关 VDS 阈值'),
        gateLowThreshold:
          gateLowThreshold.trim() === '' ? null : parsed(gateLowThreshold, '门极低阈值'),
        gateHighThreshold:
          gateHighThreshold.trim() === '' ? null : parsed(gateHighThreshold, '门极高阈值'),
      }
      setBusy(true)
      setError('')
      setSelectedCycle(0)
      setResult(await analyzeZVS(request))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '波形分析失败。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="waveform-panel" aria-labelledby="waveform-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Phase 6 · 确定性波形引擎</p>
          <h2 id="waveform-title">ZVS 波形检查</h2>
        </div>
        <span className="phase-badge">仅输出保守分类</span>
      </div>
      <p className="section-note">
        CSV 必须包含 time、VGS_Q1、VDS_Q1、IRES。所有阈值、单位、探头倍率和测试条件都必须由用户明确提供；系统不替代工程师确认。
      </p>
      <div className="waveform-controls">
        <label className="field field-wide">
          <span>CSV 文件</span>
          <input type="file" accept=".csv,text/csv" onChange={(event) => void selectFile(event.target.files?.[0])} disabled={busy} />
          <small>{file?.name ?? '尚未选择文件'}</small>
        </label>
        <QuantityField label="采样率" unit="Hz" value={sampleRate} onChange={setSampleRate} disabled={busy} />
        <label className="field">
          <span>时间单位</span>
          <input value={timeUnit} onChange={(event) => setTimeUnit(event.target.value)} disabled={busy} />
        </label>
        <QuantityField label="ZVS VDS 阈值" unit="V" value={vdsZvsThreshold} onChange={setVdsZvsThreshold} disabled={busy} />
        <QuantityField label="硬开关 VDS 阈值" unit="V" value={vdsHardThreshold} onChange={setVdsHardThreshold} disabled={busy} />
        <QuantityField label="门极低阈值（可选）" unit="V" value={gateLowThreshold} onChange={setGateLowThreshold} disabled={busy} />
        <QuantityField label="门极高阈值（可选）" unit="V" value={gateHighThreshold} onChange={setGateHighThreshold} disabled={busy} />
        <label className="field">
          <span>测试 Vin</span>
          <input value={testVin} onChange={(event) => setTestVin(event.target.value)} disabled={busy} />
        </label>
        <label className="field">
          <span>测试负载</span>
          <input value={testLoad} onChange={(event) => setTestLoad(event.target.value)} disabled={busy} />
        </label>
      </div>
      <div className="waveform-channel-settings">
        {Object.entries(channelSettings).map(([name, channel]) => (
          <div className="channel-setting" key={name}>
            <strong>{name}</strong>
            <label>单位<input value={channel.unit} onChange={(event) => updateChannel(name, 'unit', event.target.value)} disabled={busy} /></label>
            <label>探头倍率<input type="number" min="0" step="any" value={channel.probe_ratio} onChange={(event) => updateChannel(name, 'probe_ratio', event.target.value)} disabled={busy} /></label>
            <label>极性<select value={channel.polarity} onChange={(event) => updateChannel(name, 'polarity', event.target.value)} disabled={busy}><option value={1}>正</option><option value={-1}>反相</option></select></label>
          </div>
        ))}
      </div>
      <label className="waveform-checkbox">
        <input type="checkbox" checked={includeQ2} onChange={(event) => setIncludeQ2(event.target.checked)} disabled={busy} />
        CSV 中包含 VGS_Q2（用于估算互补门极 dead time）
      </label>
      <button className="button-primary waveform-submit" type="button" onClick={() => void submit()} disabled={busy}>
        {busy ? '正在分析…' : '上传并分析 ZVS'}
      </button>
      {error && <p className="inline-error">{error}</p>}
      {result && (
        <div className="waveform-result">
          <div className={`zvs-status zvs-${result.zvs_status.toLowerCase()}`}>
            <span>ZVS 状态</span>
            <strong>{waveformStatusLabels[result.zvs_status]}</strong>
            <small>周期一致性 {Math.round(result.cycle_consistency * 100)}%</small>
          </div>
          <div className="waveform-summary-grid">
            <div><span>开关频率</span><strong>{result.switching_frequency ? `${result.switching_frequency.value.toPrecision(8)} Hz` : '数据不足'}</strong></div>
            <div><span>VDS at turn-on 平均值</span><strong>{result.vds_at_turn_on?.value === null || result.vds_at_turn_on === null ? '数据不足' : `${result.vds_at_turn_on.value.toPrecision(8)} V`}</strong></div>
            <div><span>Dead time</span><strong>{result.dead_time.value === null ? '数据不足' : `${(result.dead_time.value * 1e9).toPrecision(8)} ns`}</strong></div>
            <div><span>Dead-time 配对</span><strong>{result.dead_time.valid_cycle_count} 有效 / {result.dead_time.missing_cycle_count} 缺失 / {result.dead_time.rejected_cycle_count} 拒绝</strong></div>
            <div><span>证据周期</span><strong>{result.evidence_cycles.length}</strong></div>
          </div>
          {csvText && (
            <>
              <label className="selected-cycle-control">
                <span>选择 switching cycle</span>
                <select
                  value={selectedCycle}
                  onChange={(event) => setSelectedCycle(Number(event.target.value))}
                >
                  {result.evidence_cycles.map((evidence) => (
                    <option key={evidence.cycle_index} value={evidence.cycle_index}>
                      Cycle {evidence.cycle_index + 1}
                    </option>
                  ))}
                </select>
              </label>
              <WaveformPlot csvText={csvText} result={result} selectedCycle={selectedCycle} />
            </>
          )}
          <div className="waveform-evidence">
            <h3>逐周期证据</h3>
            <div className="evidence-table-wrap">
              <table>
                <thead><tr><th>周期</th><th>Gate turn-on</th><th>VDS at turn-on</th><th>IRES</th><th>分类</th></tr></thead>
                <tbody>{result.evidence_cycles.map((evidence) => <tr key={evidence.cycle_index}><td>{evidence.cycle_index + 1}</td><td>{evidence.gate_turn_on_time.toExponential(5)} s</td><td>{evidence.vds_at_turn_on.toPrecision(8)} V</td><td>{evidence.ires_at_turn_on.toPrecision(8)} A</td><td>{waveformStatusLabels[evidence.status]}</td></tr>)}</tbody>
              </table>
            </div>
          </div>
          <ul className="waveform-limitations">{result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
        </div>
      )}
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
        <WaveformPanel />
      </div>
    </main>
  )
}

export default App
