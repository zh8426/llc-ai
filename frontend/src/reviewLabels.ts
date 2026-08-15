import type { EngineeringQuantity, Finding, Severity } from './types'

export const severityLabels: Record<Severity, string> = {
  PASS: '通过',
  INFO: '提示',
  WARNING: '警告',
  CRITICAL: '严重',
  INSUFFICIENT_DATA: '数据不足',
}

export const categoryLabels: Record<string, string> = {
  input_integrity: '输入数据完整性',
  resonant_tank: '谐振腔',
  power_consistency: '功率一致性',
  primary_switch: '主开关器件',
  resonant_capacitor: '谐振电容',
  control: '控制与频率',
  transformer: '变压器',
  evidence_integrity: '依据完整性',
}

export const findingTitleLabels: Record<string, string> = {
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

export const evidenceSourceLabels: Record<string, string> = {
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

export function dataLabel(name: string): string {
  const leafName = name.split('.').at(-1) ?? name
  const normalized = leafName.startsWith('valid_') ? leafName.slice(6) : leafName
  return dataLabels[name] ?? dataLabels[normalized] ?? normalized.replaceAll('_', ' ')
}

export function isQuantity(value: unknown): value is EngineeringQuantity {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as Record<string, unknown>
  return typeof candidate.value === 'number' && typeof candidate.unit === 'string'
}

export function formatQuantity(value: EngineeringQuantity): string {
  return `${Number(value.value.toPrecision(8))} ${value.unit}`
}

export function formatCalculatedValue(value: unknown): string {
  if (!isQuantity(value)) return String(value)
  const candidate = value as EngineeringQuantity & { formula_version?: string }
  return candidate.formula_version
    ? `${formatQuantity(candidate)}（计算公式版本：${candidate.formula_version}）`
    : formatQuantity(candidate)
}

export function inputData(finding: Finding): Array<[string, EngineeringQuantity]> {
  const values = new Map<string, EngineeringQuantity>()
  finding.evidence
    .filter((item) => item.source === 'user_input')
    .forEach((item) => {
      Object.entries(item.values).forEach(([name, value]) => values.set(name, value))
    })
  return [...values.entries()]
}
