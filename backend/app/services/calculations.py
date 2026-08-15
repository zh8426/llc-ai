from collections.abc import Callable
from datetime import UTC, datetime

from app.engine import (
    calculate_fp,
    calculate_fr,
    calculate_input_power,
    calculate_lm_lr_ratio,
    calculate_output_current,
    calculate_zr,
)
from app.engine.exceptions import EngineeringCalculationError
from app.models.project import Project
from app.schemas.engineering import CalculationResult, EngineeringQuantity
from app.schemas.project import ProjectCalculationResponse
from app.services.projects import project_quantity

CalculationFunction = Callable[..., CalculationResult]
CALCULATION_ENGINE_VERSION = "LLC-CALCULATION-ENGINE-V1"


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
