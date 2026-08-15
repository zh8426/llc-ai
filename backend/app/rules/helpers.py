from app.schemas.engineering import CalculationResult, EngineeringQuantity
from app.schemas.evidence import MeasurementEvidence, MeasurementSourceType
from app.schemas.review import (
    EvidenceItem,
    EvidenceSource,
    Finding,
    Severity,
)


def available_values(
    **values: EngineeringQuantity | None,
) -> dict[str, EngineeringQuantity]:
    return {name: value for name, value in values.items() if value is not None}


def user_input_evidence(
    description: str,
    **values: EngineeringQuantity | None,
) -> EvidenceItem:
    return EvidenceItem(
        source=EvidenceSource.USER_INPUT,
        description=description,
        values=available_values(**values),
    )


def user_measurement_evidence(
    description: str,
    measurement_names: tuple[str, ...],
    /,
    **values: EngineeringQuantity | None,
) -> EvidenceItem:
    available = available_values(**values)
    return EvidenceItem(
        source=EvidenceSource.USER_INPUT,
        description=description,
        values=available,
        measurements={
            name: MeasurementEvidence(
                value=available[name],
                source_type=MeasurementSourceType.USER_INPUT,
            )
            for name in measurement_names
            if name in available
        },
    )


def rule_definition_evidence(
    rule_id: str,
    description: str,
    *,
    values: dict[str, EngineeringQuantity] | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        source=EvidenceSource.RULE_DEFINITION,
        description=description,
        values=values or {},
        references=(rule_id,),
    )


def calculation_evidence(
    result: CalculationResult,
    description: str,
) -> EvidenceItem:
    return EvidenceItem(
        source=EvidenceSource.CALCULATION,
        description=description,
        values={result.name: EngineeringQuantity(value=result.value, unit=result.unit)},
        references=(result.formula_version,),
    )


def insufficient_finding(
    *,
    rule_id: str,
    category: str,
    title: str,
    description: str,
    missing_information: tuple[str, ...],
    recommended_action: tuple[str, ...],
    evidence: tuple[EvidenceItem, ...] = (),
) -> Finding:
    return Finding(
        rule_id=rule_id,
        category=category,
        severity=Severity.INSUFFICIENT_DATA,
        title=title,
        description=description,
        evidence=evidence,
        missing_information=missing_information,
        recommended_action=recommended_action,
        requires_engineer_confirmation=False,
    )
