from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.engineering import EngineeringQuantity
from app.schemas.evidence import MeasurementEvidence, MeasurementSourceType
from app.schemas.review import (
    EvidenceItem,
    EvidenceSource,
    Finding,
    ReviewContext,
    ReviewSettings,
    Severity,
)


def test_finding_serializes_standardized_severity_and_required_fields() -> None:
    finding = Finding(
        rule_id="LLC-R001",
        category="input_integrity",
        severity=Severity.WARNING,
        title="Example",
        description="Example warning.",
        evidence=(
            EvidenceItem(
                source=EvidenceSource.USER_INPUT,
                description="Example input evidence.",
                values={"vin": EngineeringQuantity(value=400, unit="V")},
            ),
        ),
        calculated_values={},
        missing_information=("example_field",),
        recommended_action=("Provide the field.",),
        requires_engineer_confirmation=False,
    )

    serialized = finding.model_dump(mode="json")

    assert serialized["severity"] == "WARNING"
    assert serialized["rule_id"] == "LLC-R001"
    assert serialized["evidence"][0]["source"] == "user_input"
    assert serialized["report_eligible"] is True


@pytest.mark.parametrize("severity", ["GOOD", "BAD", "DANGER", "OK", "FAILED"])
def test_finding_rejects_undefined_severity(severity: str) -> None:
    with pytest.raises(ValidationError):
        Finding.model_validate(
            {
                "rule_id": "LLC-R001",
                "category": "input",
                "severity": severity,
                "title": "Invalid severity",
                "description": "Invalid severity should be rejected.",
                "requires_engineer_confirmation": False,
            }
        )


def test_finding_rejects_invalid_rule_identifier() -> None:
    with pytest.raises(ValidationError):
        Finding(
            rule_id="R1",
            category="input",
            severity=Severity.INFO,
            title="Invalid ID",
            description="The rule ID is invalid.",
            requires_engineer_confirmation=False,
        )


def test_review_settings_do_not_supply_implicit_margins() -> None:
    settings = ReviewSettings()

    assert settings.output_power_relative_tolerance is None
    assert settings.measured_vds_required_margin_ratio is None
    assert settings.gain_review_required_parameters is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("output_power_relative_tolerance", -0.01),
        ("measured_vds_required_margin_ratio", -0.01),
        ("measured_vds_required_margin_ratio", 1.0),
    ],
)
def test_review_settings_reject_invalid_configuration(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        ReviewSettings.model_validate({field: value})


def test_review_context_rejects_undeclared_data() -> None:
    with pytest.raises(ValidationError):
        ReviewContext.model_validate({"unverified_safety_margin": 0.2})


def test_measurement_evidence_preserves_value_provenance_and_conditions() -> None:
    timestamp = datetime.now(UTC)
    evidence = MeasurementEvidence(
        value=EngineeringQuantity(value=580, unit="V"),
        source_type=MeasurementSourceType.WAVEFORM_DERIVED,
        source_id="waveform-id",
        channel="VDS_Q1",
        test_condition={
            "vin": EngineeringQuantity(value=420, unit="V"),
            "operating_state": "full_load",
        },
        timestamp=timestamp,
        human_verified=True,
    )

    serialized = evidence.model_dump(mode="json")

    assert serialized["source_type"] == "waveform_derived"
    assert serialized["source_id"] == "waveform-id"
    assert serialized["channel"] == "VDS_Q1"
    assert serialized["test_condition"]["vin"] == {"value": 420.0, "unit": "V"}
    assert serialized["timestamp"] == timestamp.isoformat().replace("+00:00", "Z")
    assert serialized["human_verified"] is True


@pytest.mark.parametrize("missing_field", ["source_id", "channel"])
def test_waveform_derived_measurement_requires_traceable_reference(
    missing_field: str,
) -> None:
    payload: dict[str, object] = {
        "value": {"value": 580, "unit": "V"},
        "source_type": "waveform_derived",
        "source_id": "waveform-id",
        "channel": "VDS_Q1",
    }
    payload[missing_field] = None

    with pytest.raises(ValidationError, match=missing_field):
        MeasurementEvidence.model_validate(payload)
