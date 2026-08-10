export type EngineeringQuantity = {
  value: number
  unit: string
}

export type Project = {
  id: string
  name: string
  topology: 'Half-Bridge LLC'
  vin_min: EngineeringQuantity | null
  vin_nom: EngineeringQuantity | null
  vin_max: EngineeringQuantity | null
  vout: EngineeringQuantity | null
  iout: EngineeringQuantity | null
  pout: EngineeringQuantity | null
  target_efficiency: EngineeringQuantity | null
  lr: EngineeringQuantity | null
  lm: EngineeringQuantity | null
  cr: EngineeringQuantity | null
  fsw_min: EngineeringQuantity | null
  fsw_nom: EngineeringQuantity | null
  fsw_max: EngineeringQuantity | null
  transformer_ratio: EngineeringQuantity | null
  dead_time: EngineeringQuantity | null
  rectification_type: 'Diode Rectification'
  primary_switch: {
    manufacturer: string | null
    part_number: string | null
    vds_rating: EngineeringQuantity | null
    measured_vds_peak: EngineeringQuantity | null
    current_rating: EngineeringQuantity | null
    measured_peak_current: EngineeringQuantity | null
    current_temperature_condition: string | null
  }
  resonant_capacitor: {
    voltage_rating: EngineeringQuantity | null
    voltage_stress: EngineeringQuantity | null
    rms_current_rating: EngineeringQuantity | null
    rms_current_stress: EngineeringQuantity | null
  }
  controller: {
    model: string | null
    frequency_min: EngineeringQuantity | null
    frequency_max: EngineeringQuantity | null
  }
  review_requests: {
    zvs_analysis_requested: boolean
    full_gain_review_requested: boolean
  }
  review_settings: {
    output_power_relative_tolerance: number | null
    measured_vds_required_margin_ratio: number | null
    gain_review_required_parameters: string[] | null
  }
  created_at: string
  updated_at: string
}

export type Severity =
  | 'PASS'
  | 'INFO'
  | 'WARNING'
  | 'CRITICAL'
  | 'INSUFFICIENT_DATA'

export type Evidence = {
  source: string
  description: string
  values: Record<string, EngineeringQuantity>
  references: string[]
}

export type Finding = {
  rule_id: string
  category: string
  severity: Severity
  title: string
  description: string
  evidence: Evidence[]
  calculated_values: Record<string, unknown>
  missing_information: string[]
  recommended_action: string[]
  requires_engineer_confirmation: boolean
  report_eligible: boolean
}

export type Review = {
  project_id: string
  review_id: string
  created_at: string
  summary: {
    pass: number
    info: number
    warning: number
    critical: number
    insufficient_data: number
  }
  findings: Finding[]
}

export type ProjectPayload = Record<string, unknown>
