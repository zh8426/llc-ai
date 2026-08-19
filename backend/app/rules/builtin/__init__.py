"""Built-in review rules R001 through R026."""

from app.rules.builtin.calculation_rules import (
    CharacteristicImpedanceRule,
    InductanceRatioObservationRule,
    LowerResonantFrequencyCalculationRule,
    OutputPowerConsistencyRule,
    ResonantFrequencyCalculationRule,
    ResonantFrequencyOperatingRangeRule,
)
from app.rules.builtin.component_rules import (
    ControllerFrequencyCapabilityRule,
    MOSFETCurrentScreeningRule,
    MOSFETMeasuredPeakVoltageRule,
    MOSFETStaticVoltageScreeningRule,
    ResonantCapacitorRMSCurrentRule,
    ResonantCapacitorVoltageRatingRule,
)
from app.rules.builtin.gain_rules import (
    FHAApplicabilityRule,
    FrequencyCapabilityRule,
    GainModelPrerequisitesRule,
    GainPeakMarginRule,
    OperatingPointRegionRule,
    RequiredGainCoverageRule,
)
from app.rules.builtin.input_rules import (
    CriticalParameterCompletenessRule,
    InputVoltageOrderingRule,
    PositiveValuesRule,
    SwitchingFrequencyOrderingRule,
)
from app.rules.builtin.prerequisite_rules import (
    DeadTimeInformationRule,
    EvidenceCompletenessRule,
    GainReviewPrerequisiteRule,
    TransformerRatioRequiredRule,
)

__all__ = [
    "CharacteristicImpedanceRule",
    "ControllerFrequencyCapabilityRule",
    "CriticalParameterCompletenessRule",
    "DeadTimeInformationRule",
    "EvidenceCompletenessRule",
    "FHAApplicabilityRule",
    "FrequencyCapabilityRule",
    "GainReviewPrerequisiteRule",
    "GainModelPrerequisitesRule",
    "GainPeakMarginRule",
    "InductanceRatioObservationRule",
    "InputVoltageOrderingRule",
    "LowerResonantFrequencyCalculationRule",
    "MOSFETCurrentScreeningRule",
    "MOSFETMeasuredPeakVoltageRule",
    "MOSFETStaticVoltageScreeningRule",
    "OutputPowerConsistencyRule",
    "OperatingPointRegionRule",
    "PositiveValuesRule",
    "ResonantCapacitorRMSCurrentRule",
    "ResonantCapacitorVoltageRatingRule",
    "ResonantFrequencyCalculationRule",
    "ResonantFrequencyOperatingRangeRule",
    "RequiredGainCoverageRule",
    "SwitchingFrequencyOrderingRule",
    "TransformerRatioRequiredRule",
]
