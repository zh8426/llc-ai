import { useMemo, useState } from 'react'

import { analyzeZVS } from '../api'
import type {
  WaveformAnalysisRequest,
  WaveformChannelMetadata,
  ZVSAnalysis,
  ZVSStatus,
} from '../types'
import QuantityField from './QuantityField'

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
  const xFor = (timestamp: number) => ((timestamp - firstTime) / timeSpan) * width
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

export default function WaveformPanel() {
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
