from collections.abc import Callable

import pytest

from app.rules import run_design_review
from app.schemas.engineering import EngineeringQuantity
from app.schemas.review import ReviewContext, Severity


def q(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def update_section(
    context: ReviewContext, section: str, **changes: object
) -> ReviewContext:
    updated = getattr(context, section).model_copy(update=changes)
    return context.model_copy(update={section: updated})


def invalid_tank_and_voltage_order(context: ReviewContext) -> ReviewContext:
    context = update_section(
        context,
        "project",
        lr=q(-45, "uH"),
        vin_min=q(420, "V"),
        vin_nom=q(360, "V"),
        vin_max=q(300, "V"),
    )
    invalidated_results = {
        "resonant_frequency",
        "lower_resonant_frequency",
        "characteristic_impedance",
        "inductance_ratio",
    }
    return context.model_copy(
        update={
            "calculated_inputs": {
                name: result
                for name, result in context.calculated_inputs.items()
                if name not in invalidated_results
            }
        }
    )


def invalid_project_and_controller_ranges(context: ReviewContext) -> ReviewContext:
    context = update_section(
        context, "project", fsw_min=q(150, "kHz"), fsw_max=q(60, "kHz")
    )
    return update_section(
        context,
        "controller",
        frequency_min=q(500, "kHz"),
        frequency_max=q(40, "kHz"),
    )


def mosfet_voltage_faults(context: ReviewContext) -> ReviewContext:
    return update_section(
        context,
        "mosfet",
        vds_rating=q(400, "V"),
        measured_vds_peak=q(500, "V"),
    )


def capacitor_voltage_and_current_faults(context: ReviewContext) -> ReviewContext:
    return update_section(
        context,
        "resonant_capacitor",
        voltage_stress=q(1100, "V"),
        rms_current_stress=q(15, "A"),
    )


def power_and_controller_mismatch(context: ReviewContext) -> ReviewContext:
    context = update_section(context, "project", iout=q(12, "A"))
    return update_section(context, "controller", frequency_max=q(120, "kHz"))


def missing_zvs_and_gain_prerequisites(context: ReviewContext) -> ReviewContext:
    return update_section(
        context, "project", dead_time=None, transformer_ratio=None
    )


def missing_project_rule_configuration(context: ReviewContext) -> ReviewContext:
    return update_section(
        context,
        "settings",
        output_power_relative_tolerance=None,
        measured_vds_required_margin_ratio=None,
        gain_review_required_parameters=None,
    )


def incompatible_project_and_component_units(context: ReviewContext) -> ReviewContext:
    context = update_section(context, "project", vout=q(48, "A"))
    return update_section(context, "mosfet", current_rating=q(20, "V"))


def missing_resonant_tank(context: ReviewContext) -> ReviewContext:
    return update_section(context, "project", lr=None, lm=None, cr=None)


def mixed_voltage_component_and_control_faults(context: ReviewContext) -> ReviewContext:
    context = update_section(
        context,
        "project",
        vin_min=q(420, "V"),
        vin_nom=q(360, "V"),
        vin_max=q(300, "V"),
    )
    context = update_section(context, "mosfet", vds_rating=q(250, "V"))
    context = update_section(
        context, "resonant_capacitor", voltage_stress=q(1100, "V")
    )
    return update_section(context, "controller", frequency_max=q(120, "kHz"))


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (
            invalid_tank_and_voltage_order,
            {
                "LLC-R002": Severity.CRITICAL,
                "LLC-R003": Severity.CRITICAL,
                "LLC-R005": Severity.INSUFFICIENT_DATA,
            },
        ),
        (
            invalid_project_and_controller_ranges,
            {
                "LLC-R004": Severity.CRITICAL,
                "LLC-R016": Severity.INSUFFICIENT_DATA,
            },
        ),
        (
            mosfet_voltage_faults,
            {"LLC-R011": Severity.CRITICAL, "LLC-R012": Severity.CRITICAL},
        ),
        (
            capacitor_voltage_and_current_faults,
            {"LLC-R014": Severity.CRITICAL, "LLC-R015": Severity.CRITICAL},
        ),
        (
            power_and_controller_mismatch,
            {"LLC-R010": Severity.WARNING, "LLC-R016": Severity.WARNING},
        ),
        (
            missing_zvs_and_gain_prerequisites,
            {
                "LLC-R017": Severity.INSUFFICIENT_DATA,
                "LLC-R018": Severity.INSUFFICIENT_DATA,
                "LLC-R019": Severity.INSUFFICIENT_DATA,
            },
        ),
        (
            missing_project_rule_configuration,
            {
                "LLC-R010": Severity.INSUFFICIENT_DATA,
                "LLC-R012": Severity.INFO,
                "LLC-R019": Severity.INSUFFICIENT_DATA,
            },
        ),
        (
            incompatible_project_and_component_units,
            {
                "LLC-R002": Severity.CRITICAL,
                "LLC-R010": Severity.INSUFFICIENT_DATA,
                "LLC-R013": Severity.INSUFFICIENT_DATA,
            },
        ),
        (
            missing_resonant_tank,
            {
                "LLC-R001": Severity.INSUFFICIENT_DATA,
                "LLC-R005": Severity.INSUFFICIENT_DATA,
                "LLC-R006": Severity.INSUFFICIENT_DATA,
                "LLC-R008": Severity.INSUFFICIENT_DATA,
                "LLC-R009": Severity.INSUFFICIENT_DATA,
            },
        ),
        (
            mixed_voltage_component_and_control_faults,
            {
                "LLC-R003": Severity.CRITICAL,
                "LLC-R011": Severity.CRITICAL,
                "LLC-R014": Severity.CRITICAL,
                "LLC-R016": Severity.WARNING,
            },
        ),
    ],
    ids=[
        "tank-and-voltage-order",
        "project-and-controller-ranges",
        "mosfet-voltage",
        "capacitor-stress",
        "power-and-controller",
        "zvs-and-gain-prerequisites",
        "missing-settings",
        "incompatible-units",
        "missing-tank",
        "mixed-voltage-component-control",
    ],
)
def test_multi_fault_scenarios_remain_deterministic_and_evidence_backed(
    normal_review_context: ReviewContext,
    mutator: Callable[[ReviewContext], ReviewContext],
    expected: dict[str, Severity],
) -> None:
    result = run_design_review(mutator(normal_review_context))
    by_rule = {finding.rule_id: finding for finding in result.findings}

    for rule_id, severity in expected.items():
        assert by_rule[rule_id].severity == severity
    assert all(
        finding.evidence
        for finding in result.findings
        if finding.severity in {Severity.WARNING, Severity.CRITICAL}
    )
    assert result.excluded_findings == ()
    assert by_rule["LLC-R020"].severity == Severity.PASS
