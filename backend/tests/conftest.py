from collections.abc import Callable

import pytest

from app.schemas.engineering import EngineeringQuantity
from app.schemas.review import (
    ControllerReviewInput,
    LLCProjectReviewInput,
    MOSFETReviewInput,
    ResonantCapacitorReviewInput,
    ReviewContext,
    ReviewParameterName,
    ReviewRequests,
    ReviewSettings,
)


def q(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


@pytest.fixture
def normal_review_context() -> ReviewContext:
    return ReviewContext(
        project=LLCProjectReviewInput(
            vin_min=q(300, "V"),
            vin_nom=q(360, "V"),
            vin_max=q(420, "V"),
            vout=q(48, "V"),
            pout=q(500, "W"),
            iout=q(500 / 48, "A"),
            lr=q(45, "uH"),
            lm=q(300, "uH"),
            cr=q(47, "nF"),
            fsw_min=q(60, "kHz"),
            fsw_max=q(150, "kHz"),
            transformer_ratio=q(4, "dimensionless"),
            dead_time=q(300, "ns"),
        ),
        mosfet=MOSFETReviewInput(
            vds_rating=q(650, "V"),
            measured_vds_peak=q(500, "V"),
            current_rating=q(20, "A"),
            measured_peak_current=q(10, "A"),
            current_temperature_condition="Measured and rating conditions documented by the project engineer.",
        ),
        resonant_capacitor=ResonantCapacitorReviewInput(
            voltage_rating=q(1000, "V"),
            voltage_stress=q(500, "V"),
            rms_current_rating=q(12, "A"),
            rms_current_stress=q(8, "A"),
        ),
        controller=ControllerReviewInput(
            frequency_min=q(40, "kHz"),
            frequency_max=q(500, "kHz"),
        ),
        requests=ReviewRequests(
            zvs_analysis_requested=True,
            full_gain_review_requested=True,
        ),
        settings=ReviewSettings(
            output_power_relative_tolerance=0.01,
            measured_vds_required_margin_ratio=0.20,
            gain_review_required_parameters=(
                ReviewParameterName.VIN_MIN,
                ReviewParameterName.VIN_MAX,
                ReviewParameterName.VOUT,
                ReviewParameterName.POUT,
                ReviewParameterName.LR,
                ReviewParameterName.LM,
                ReviewParameterName.CR,
                ReviewParameterName.FSW_MIN,
                ReviewParameterName.FSW_MAX,
                ReviewParameterName.TRANSFORMER_RATIO,
            ),
        ),
    )


@pytest.fixture
def incomplete_review_context() -> ReviewContext:
    return ReviewContext(
        requests=ReviewRequests(
            zvs_analysis_requested=True,
            full_gain_review_requested=True,
        )
    )


@pytest.fixture
def invalid_review_context(normal_review_context: ReviewContext) -> ReviewContext:
    invalid_project = normal_review_context.project.model_copy(
        update={
            "vin_min": q(420, "V"),
            "vin_nom": q(360, "V"),
            "vin_max": q(300, "V"),
            "vout": q(-48, "V"),
            "lr": q(-45, "uH"),
            "fsw_min": q(150, "kHz"),
            "fsw_max": q(60, "kHz"),
        }
    )
    return normal_review_context.model_copy(update={"project": invalid_project})


@pytest.fixture
def update_review_context() -> Callable[..., ReviewContext]:
    def update(
        context: ReviewContext,
        section: str,
        **changes: object,
    ) -> ReviewContext:
        section_model = getattr(context, section)
        updated_section = section_model.model_copy(update=changes)
        return context.model_copy(update={section: updated_section})

    return update

