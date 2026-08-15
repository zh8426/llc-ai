import type { EngineeringQuantity, Project, ProjectPayload } from './types'

export type ProjectForm = {
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

export const emptyForm: ProjectForm = {
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

export function projectToForm(project: Project): ProjectForm {
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

export function buildPayload(form: ProjectForm): ProjectPayload {
  if (form.name.trim() === '') throw new Error('项目名称不能为空。')
  return {
    name: form.name.trim(),
    vin_min: quantity(form.vinMin, 'V', 'Vin Min'),
    vin_nom: quantity(form.vinNom, 'V', 'Vin Nom'),
    vin_max: quantity(form.vinMax, 'V', 'Vin Max'),
    vout: quantity(form.vout, 'V', 'Vout'),
    pout: quantity(form.pout, 'W', 'Pout'),
    target_efficiency: quantity(form.efficiencyPercent, 'percent', '目标效率'),
    lr: quantity(form.lr, 'uH', 'Lr'),
    lm: quantity(form.lm, 'uH', 'Lm'),
    cr: quantity(form.cr, 'nF', 'Cr'),
    fsw_min: quantity(form.fswMin, 'kHz', 'Fsw Min'),
    fsw_nom: quantity(form.fswNom, 'kHz', 'Fsw Nom'),
    fsw_max: quantity(form.fswMax, 'kHz', 'Fsw Max'),
    transformer_ratio: quantity(form.transformerRatio, 'dimensionless', '变压器匝比'),
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
