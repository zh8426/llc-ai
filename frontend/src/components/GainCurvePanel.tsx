import { useEffect, useMemo, useState } from 'react'

import { generateGainCurve } from '../api'
import type { GainCurve, Project } from '../types'

type GainCurvePanelProps = {
  project: Project | null
}

function formatFrequency(quantity: { value: number; unit: string }): string {
  const valueKhz = quantity.unit.toLowerCase() === 'hz' ? quantity.value / 1000 : quantity.value
  return `${valueKhz.toFixed(2)} kHz`
}

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toPrecision(5)
}

function regionColor(region: 'INDUCTIVE' | 'CAPACITIVE' | 'BOUNDARY'): string {
  if (region === 'INDUCTIVE') return '#238461'
  if (region === 'CAPACITIVE') return '#ba7045'
  return '#7d6aa9'
}

function GainCurveChart({ curve }: { curve: GainCurve }) {
  const width = 860
  const height = 300
  const padding = { top: 22, right: 28, bottom: 42, left: 58 }
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom
  const gains = curve.points.map((point) => point.tank_gain.value)
  const minGain = Math.min(...gains)
  const maxGain = Math.max(...gains)
  const gainSpan = maxGain - minGain || Math.max(maxGain * 0.1, 0.1)
  const axisMin = Math.max(0, minGain - gainSpan * 0.1)
  const axisMax = maxGain + gainSpan * 0.1
  const points = curve.points
    .map((point, index) => {
      const x = padding.left + (index / (curve.points.length - 1)) * chartWidth
      const y = padding.top + ((axisMax - point.tank_gain.value) / (axisMax - axisMin)) * chartHeight
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
  const yTicks = [axisMin, (axisMin + axisMax) / 2, axisMax]

  return (
    <div className="gain-chart-wrap">
      <svg
        className="gain-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="FHA tank gain versus switching frequency"
      >
        {yTicks.map((tick) => {
          const y = padding.top + ((axisMax - tick) / (axisMax - axisMin)) * chartHeight
          return (
            <g key={tick}>
              <line
                className="gain-gridline"
                x1={padding.left}
                x2={width - padding.right}
                y1={y}
                y2={y}
              />
              <text className="gain-label" x={padding.left - 9} y={y + 4} textAnchor="end">
                {tick.toFixed(2)}
              </text>
            </g>
          )
        })}
        <line
          className="gain-axis"
          x1={padding.left}
          x2={padding.left}
          y1={padding.top}
          y2={height - padding.bottom}
        />
        <line
          className="gain-axis"
          x1={padding.left}
          x2={width - padding.right}
          y1={height - padding.bottom}
          y2={height - padding.bottom}
        />
        <polyline className="gain-line" points={points} />
        {curve.points.length <= 151 &&
          curve.points.map((point, index) => {
            const x = padding.left + (index / (curve.points.length - 1)) * chartWidth
            const y = padding.top + ((axisMax - point.tank_gain.value) / (axisMax - axisMin)) * chartHeight
            return (
              <circle key={`${point.switching_frequency.value}-${index}`} cx={x} cy={y} r="2.7" fill={regionColor(point.operating_region)}>
                <title>
                  {formatFrequency(point.switching_frequency)} · M = {formatNumber(point.tank_gain.value)} · {point.operating_region}
                </title>
              </circle>
            )
          })}
        <text className="gain-label" x={padding.left} y={height - 15}>
          {formatFrequency(curve.frequency_min)}
        </text>
        <text className="gain-label" x={width - padding.right} y={height - 15} textAnchor="end">
          {formatFrequency(curve.frequency_max)}
        </text>
        <text className="gain-axis-title" x={width / 2} y={height - 2} textAnchor="middle">
          开关频率
        </text>
        <text
          className="gain-axis-title"
          x={15}
          y={height / 2}
          textAnchor="middle"
          transform={`rotate(-90 15 ${height / 2})`}
        >
          FHA 增益 MFHA
        </text>
      </svg>
      <div className="gain-legend" aria-label="工作区域图例">
        <span><i className="gain-legend-inductive" />感性区</span>
        <span><i className="gain-legend-capacitive" />容性区</span>
        <span><i className="gain-legend-boundary" />边界</span>
      </div>
    </div>
  )
}

export default function GainCurvePanel({ project }: GainCurvePanelProps) {
  const [pointCount, setPointCount] = useState('101')
  const [curve, setCurve] = useState<GainCurve | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setCurve(null)
    setError('')
  }, [project?.id, project?.updated_at])

  const hasProject = project !== null
  const missingProjectData = useMemo(() => {
    if (!project) return []
    return ['lr', 'lm', 'cr', 'vout', 'pout', 'transformer_ratio', 'fsw_min', 'fsw_max'].filter(
      (field) => project[field as keyof Project] === null,
    )
  }, [project])

  async function handleGenerate() {
    if (!project) return
    const parsedPointCount = Number(pointCount)
    if (!Number.isInteger(parsedPointCount) || parsedPointCount < 2 || parsedPointCount > 1001) {
      setError('扫描点数必须是 2–1001 之间的整数。')
      return
    }
    setBusy(true)
    setError('')
    try {
      setCurve(await generateGainCurve(project.id, parsedPointCount))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '增益曲线生成失败。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="gain-curve-panel" aria-labelledby="gain-curve-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Cross-Phase E1-G · FHA 频率扫描</p>
          <h2 id="gain-curve-title">LLC 增益曲线</h2>
        </div>
        <span className="phase-badge">确定性模型 · 仅作工程参考</span>
      </div>
      <p className="section-note">
        使用当前已保存项目参数扫描 Fsw Min–Max，展示 FHA 谐振腔增益、归一化频率和输入阻抗工作区域；这不是实测波形或安全结论。
      </p>

      {!hasProject ? (
        <p className="inline-notice">请先创建项目并保存参数。</p>
      ) : (
        <>
          <div className="gain-curve-controls">
            <label className="field">
              <span>扫描点数</span>
              <input
                type="number"
                min="2"
                max="1001"
                step="1"
                value={pointCount}
                onChange={(event) => setPointCount(event.target.value)}
                disabled={busy}
              />
              <small>2–1001 点；点数越多，曲线越细。</small>
            </label>
            <button className="button-primary gain-curve-submit" onClick={() => void handleGenerate()} disabled={busy} type="button">
              {busy ? '正在计算…' : '生成增益曲线'}
            </button>
          </div>
          {missingProjectData.length > 0 && (
            <p className="inline-error">缺少项目参数：{missingProjectData.join('、')}。保存完整参数后再生成。</p>
          )}
          {error !== '' && <p className="inline-error">{error}</p>}
          {curve !== null && (
            <div className="gain-curve-result">
              <div className="gain-summary-grid">
                <div><span>谐振频率 fr</span><strong>{formatFrequency({ value: curve.resonant_frequency.value, unit: curve.resonant_frequency.unit })}</strong></div>
                <div><span>等效负载 Re</span><strong>{formatNumber(curve.equivalent_load.value)} {curve.equivalent_load.unit}</strong></div>
                <div><span>品质因数 Qe</span><strong>{formatNumber(curve.quality_factor.value)}</strong></div>
                <div><span>扫描点数</span><strong>{curve.point_count}</strong></div>
              </div>
              <GainCurveChart curve={curve} />
              <p className="gain-curve-footnote">
                公式版本：{curve.formula_version}。每个点均保留 MFHA、Zin 实部/虚部与感性/容性分类，最终设计判断仍需工程师复核。
              </p>
            </div>
          )}
        </>
      )}
    </section>
  )
}
