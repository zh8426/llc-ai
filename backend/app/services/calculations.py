from collections.abc import Callable
from datetime import UTC, datetime

from app.engine import (
    calculate_equivalent_load,
    calculate_fp,
    calculate_fr,
    calculate_gain_curve,
    calculate_input_power,
    calculate_lm_lr_ratio,
    calculate_output_current,
    calculate_zr,
)
from app.engine.exceptions import EngineeringCalculationError
from app.models.project import Project
from app.schemas.engineering import CalculationResult, EngineeringQuantity
from app.schemas.project import ProjectCalculationResponse, ProjectGainCurveResponse
from app.services.projects import project_quantity

CalculationFunction = Callable[..., CalculationResult]
CALCULATION_ENGINE_VERSION = "LLC-CALCULATION-ENGINE-V1"


class ProjectGainCurveMissingDataError(ValueError):
    """Raised when a project cannot provide the gain-curve input contract."""

    def __init__(self, missing_information: tuple[str, ...]) -> None:
        self.missing_information = missing_information
        super().__init__(", ".join(missing_information))


def calculate_project(project: Project) -> ProjectCalculationResponse:
    specifications: tuple[
        tuple[str, CalculationFunction, tuple[tuple[str, str], ...]], ...
    ] = (
        ("resonant_frequency", calculate_fr, (("lr", "lr"), ("cr", "cr"))),
        (
            "lower_resonant_frequency",
            calculate_fp,
            (("lr", "lr"), ("lm", "lm"), ("cr", "cr")),
        ),
        (
            "characteristic_impedance",
            calculate_zr,
            (("lr", "lr"), ("cr", "cr")),
        ),
        (
            "inductance_ratio",
            calculate_lm_lr_ratio,
            (("lr", "lr"), ("lm", "lm")),
        ),
        (
            "output_current",
            calculate_output_current,
            (("pout", "pout"), ("vout", "vout")),
        ),
        (
            "input_power",
            calculate_input_power,
            (("pout", "pout"), ("efficiency", "target_efficiency")),
        ),
    )

    calculations: list[CalculationResult] = []
    missing: set[str] = set()
    errors: dict[str, str] = {}
    for result_name, function, arguments in specifications:
        values: dict[str, EngineeringQuantity] = {}
        result_missing: list[str] = []
        for argument_name, project_field in arguments:
            value = project_quantity(project, project_field)
            if value is None:
                result_missing.append(project_field)
            else:
                values[argument_name] = value
        if result_missing:
            missing.update(result_missing)
            continue
        try:
            calculations.append(function(**values))
        except EngineeringCalculationError as error:
            errors[result_name] = str(error)

    return ProjectCalculationResponse(
        project_id=project.id,
        calculated_at=datetime.now(UTC),
        engine_version=CALCULATION_ENGINE_VERSION,
        calculations=tuple(calculations),
        missing_information=tuple(sorted(missing)),
        errors=errors,
    )


def calculate_project_gain_curve(
    project: Project, *, point_count: int
) -> ProjectGainCurveResponse:
    """Generate an FHA gain curve from one persisted project's explicit data."""

    required_fields = (
        "lr",
        "lm",
        "cr",
        "vout",
        "pout",
        "transformer_ratio",
        "fsw_min",
        "fsw_max",
    )
    quantities = {
        field_name: project_quantity(project, field_name)
        for field_name in required_fields
    }
    missing_information = tuple(
        field_name for field_name, value in quantities.items() if value is None
    )
    if missing_information:
        raise ProjectGainCurveMissingDataError(missing_information)

    # The missing-data guard above makes these assertions true while keeping
    # the persisted-project boundary explicit to type checkers.
    lr = quantities["lr"]
    lm = quantities["lm"]
    cr = quantities["cr"]
    vout = quantities["vout"]
    pout = quantities["pout"]
    transformer_ratio = quantities["transformer_ratio"]
    frequency_min = quantities["fsw_min"]
    frequency_max = quantities["fsw_max"]
    assert lr is not None
    assert lm is not None
    assert cr is not None
    assert vout is not None
    assert pout is not None
    assert transformer_ratio is not None
    assert frequency_min is not None
    assert frequency_max is not None

    equivalent_load = calculate_equivalent_load(
        pout=pout,
        vout=vout,
        transformer_ratio=transformer_ratio,
    )
    curve = calculate_gain_curve(
        lr=lr,
        lm=lm,
        cr=cr,
        equivalent_load=EngineeringQuantity(
            value=equivalent_load.value, unit=equivalent_load.unit
        ),
        frequency_min=frequency_min,
        frequency_max=frequency_max,
        point_count=point_count,
    )
    return ProjectGainCurveResponse(
        project_id=project.id,
        **curve.model_dump(exclude={"equivalent_load"}),
        equivalent_load=equivalent_load,
    )
