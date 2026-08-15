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
  measurements: Record<string, MeasurementEvidence>
  references: string[]
}

export type MeasurementEvidence = {
  value: EngineeringQuantity
  source_type: 'user_input' | 'waveform_derived' | 'datasheet' | 'calculated' | 'imported'
  source_id: string | null
  channel: string | null
  test_condition: Record<string, EngineeringQuantity | string>
  timestamp: string | null
  human_verified: boolean
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
  excluded_findings: Finding[]
}

export type ReviewHistoryItem = {
  review_id: string
  created_at: string
  summary: Review['summary']
  calculation_snapshot: {
    calculated_at: string
    engine_version: string
    calculation_count: number
  } | null
}

export type ProjectReviewHistory = {
  project_id: string
  reviews: ReviewHistoryItem[]
}

export type ProjectPayload = Record<string, unknown>

export type WaveformChannelMetadata = {
  unit: string
  probe_ratio: number
  polarity: 1 | -1
}

export type WaveformAnalysisRequest = {
  file: File
  sampleRate: number
  timeUnit: string
  channels: Record<string, WaveformChannelMetadata>
  testCondition: Record<string, string>
  vdsZvsThreshold: number
  vdsHardSwitchingThreshold: number
  gateLowThreshold: number | null
  gateHighThreshold: number | null
}

export type ZVSStatus =
  | 'LIKELY_ZVS'
  | 'PARTIAL_ZVS'
  | 'LIKELY_HARD_SWITCHING'
  | 'INSUFFICIENT_DATA'

export type ZVSEvidenceCycle = {
  cycle_index: number
  gate_turn_on_time: number
  vds_at_turn_on: number
  ires_at_turn_on: number
  status: ZVSStatus
}

export type DeadTimeEvidence = {
  primary_turn_off_time: number
  complementary_turn_on_time: number
  duration: number
}

export type ZVSAnalysis = {
  switching_frequency: {
    value: number
    unit: string
    cycle_count: number
    formula_version: string
  } | null
  dead_time: {
    value: number | null
    values: number[]
    evidence: DeadTimeEvidence[]
    unit: string
    status: 'AVAILABLE' | 'INSUFFICIENT_DATA'
    formula_version: string
  }
  vds_at_turn_on: {
    value: number | null
    values: number[]
    unit: string
    formula_version: string
  } | null
  zvs_status: ZVSStatus
  confidence: number
  evidence_cycles: ZVSEvidenceCycle[]
  limitations: string[]
  analysis_version: string
  gate_turn_on_timestamps: number[]
  gate_turn_off_timestamps: number[]
}
