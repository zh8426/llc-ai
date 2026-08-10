import pytest
from pydantic import ValidationError

from app.schemas.engineering import EngineeringQuantity
from app.schemas.project import LLCCoreProjectInput


def quantity(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def valid_project_payload() -> dict[str, EngineeringQuantity]:
    return {
        "lr": quantity(45, "uH"),
        "lm": quantity(300, "uH"),
        "cr": quantity(47, "nF"),
        "vout": quantity(48, "V"),
        "pout": quantity(500, "W"),
        "efficiency": quantity(94, "percent"),
    }


def test_core_project_input_accepts_all_required_quantities() -> None:
    project_input = LLCCoreProjectInput.model_validate(valid_project_payload())

    assert project_input.lr == quantity(45, "uH")
    assert project_input.efficiency == quantity(94, "percent")


@pytest.mark.parametrize(
    "missing_field",
    ["lr", "lm", "cr", "vout", "pout", "efficiency"],
)
def test_core_project_input_rejects_each_missing_required_field(
    missing_field: str,
) -> None:
    payload = valid_project_payload()
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        LLCCoreProjectInput.model_validate(payload)


def test_core_project_input_rejects_undeclared_fields() -> None:
    payload: dict[str, object] = valid_project_payload()
    payload["assumed_dead_time"] = quantity(500, "ns")

    with pytest.raises(ValidationError):
        LLCCoreProjectInput.model_validate(payload)

