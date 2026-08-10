"""Built-in Phase 2 review rules R001 through R020."""

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
    "GainReviewPrerequisiteRule",
    "InductanceRatioObservationRule",
    "InputVoltageOrderingRule",
    "LowerResonantFrequencyCalculationRule",
    "MOSFETCurrentScreeningRule",
    "MOSFETMeasuredPeakVoltageRule",
    "MOSFETStaticVoltageScreeningRule",
    "OutputPowerConsistencyRule",
    "PositiveValuesRule",
    "ResonantCapacitorRMSCurrentRule",
    "ResonantCapacitorVoltageRatingRule",
    "ResonantFrequencyCalculationRule",
    "ResonantFrequencyOperatingRangeRule",
    "SwitchingFrequencyOrderingRule",
    "TransformerRatioRequiredRule",
]

