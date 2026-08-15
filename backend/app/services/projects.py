from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.units import normalize_quantity
from app.models.project import Project, utc_now
from app.schemas.engineering import EngineeringQuantity
from app.schemas.project import (
    ControllerInput,
    PrimarySwitchInput,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ResonantCapacitorInput,
)
from app.schemas.review import ReviewParameterName, ReviewRequests, ReviewSettings


@dataclass(frozen=True)
class QuantityField:
    model_attribute: str
    storage_unit: str
    api_unit: str


PROJECT_QUANTITIES: dict[str, QuantityField] = {
    "vin_min": QuantityField("vin_min_v", "V", "V"),
    "vin_nom": QuantityField("vin_nom_v", "V", "V"),
    "vin_max": QuantityField("vin_max_v", "V", "V"),
    "vout": QuantityField("vout_v", "V", "V"),
    "iout": QuantityField("iout_a", "A", "A"),
    "pout": QuantityField("pout_w", "W", "W"),
    "target_efficiency": QuantityField(
        "target_efficiency", "dimensionless", "dimensionless"
    ),
    "lr": QuantityField("lr_h", "H", "uH"),
    "lm": QuantityField("lm_h", "H", "uH"),
    "cr": QuantityField("cr_f", "F", "nF"),
    "fsw_min": QuantityField("fsw_min_hz", "Hz", "kHz"),
    "fsw_nom": QuantityField("fsw_nom_hz", "Hz", "kHz"),
    "fsw_max": QuantityField("fsw_max_hz", "Hz", "kHz"),
    "transformer_ratio": QuantityField(
        "transformer_ratio", "dimensionless", "dimensionless"
    ),
    "dead_time": QuantityField("dead_time_s", "s", "ns"),
}

PRIMARY_SWITCH_QUANTITIES: dict[str, QuantityField] = {
    "vds_rating": QuantityField("primary_switch_vds_rating_v", "V", "V"),
    "measured_vds_peak": QuantityField(
        "primary_switch_measured_vds_peak_v", "V", "V"
    ),
    "current_rating": QuantityField(
        "primary_switch_current_rating_a", "A", "A"
    ),
    "measured_peak_current": QuantityField(
        "primary_switch_measured_peak_current_a", "A", "A"
    ),
}

RESONANT_CAPACITOR_QUANTITIES: dict[str, QuantityField] = {
    "voltage_rating": QuantityField(
        "resonant_capacitor_voltage_rating_v", "V", "V"
    ),
    "voltage_stress": QuantityField(
        "resonant_capacitor_voltage_stress_v", "V", "V"
    ),
    "rms_current_rating": QuantityField(
        "resonant_capacitor_rms_current_rating_a", "A", "A"
    ),
    "rms_current_stress": QuantityField(
        "resonant_capacitor_rms_current_stress_a", "A", "A"
    ),
}

CONTROLLER_QUANTITIES: dict[str, QuantityField] = {
    "frequency_min": QuantityField(
        "controller_frequency_min_hz", "Hz", "kHz"
    ),
    "frequency_max": QuantityField(
        "controller_frequency_max_hz", "Hz", "kHz"
    ),
}


def _to_storage(
    field_name: str,
    quantity: EngineeringQuantity | None,
    specification: QuantityField,
) -> float | None:
    if quantity is None:
        return None
    return normalize_quantity(
        name=field_name,
        quantity=quantity,
        target_unit=specification.storage_unit,
    ).value


def _from_storage(
    field_name: str,
    value: float | None,
    specification: QuantityField,
) -> EngineeringQuantity | None:
    if value is None:
        return None
    return normalize_quantity(
        name=field_name,
        quantity=EngineeringQuantity(value=value, unit=specification.storage_unit),
        target_unit=specification.api_unit,
    )


def _set_quantities(
    project: Project,
    source: object,
    specifications: dict[str, QuantityField],
    fields: set[str] | None = None,
) -> None:
    selected = specifications.keys() if fields is None else specifications.keys() & fields
    for field_name in selected:
        specification = specifications[field_name]
        setattr(
            project,
            specification.model_attribute,
            _to_storage(field_name, getattr(source, field_name), specification),
        )


def _clear_quantities(
    project: Project, specifications: dict[str, QuantityField]
) -> None:
    for specification in specifications.values():
        setattr(project, specification.model_attribute, None)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def create_project(session: Session, payload: ProjectCreate) -> Project:
    project = Project(
        name=payload.name,
        topology=payload.topology,
        rectification_type=payload.rectification_type,
    )
    _set_quantities(project, payload, PROJECT_QUANTITIES)
    _apply_primary_switch(project, payload.primary_switch)
    _apply_resonant_capacitor(project, payload.resonant_capacitor)
    _apply_controller(project, payload.controller)
    _apply_review_requests(project, payload.review_requests)
    _apply_review_settings(project, payload.review_settings)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def list_projects(session: Session) -> tuple[Project, ...]:
    statement = select(Project).order_by(Project.updated_at.desc(), Project.name)
    return tuple(session.scalars(statement))


def get_project(session: Session, project_id: str) -> Project | None:
    return session.get(Project, project_id)


def update_project(
    session: Session, project: Project, payload: ProjectUpdate
) -> Project:
    fields = payload.model_fields_set
    if "name" in fields:
        if payload.name is None:
            raise ValueError("name cannot be null")
        project.name = payload.name
    _set_quantities(project, payload, PROJECT_QUANTITIES, fields)

    if "primary_switch" in fields:
        if payload.primary_switch is None:
            _clear_primary_switch(project)
        else:
            _apply_primary_switch(
                project,
                payload.primary_switch,
                payload.primary_switch.model_fields_set,
            )
    if "resonant_capacitor" in fields:
        if payload.resonant_capacitor is None:
            _clear_quantities(project, RESONANT_CAPACITOR_QUANTITIES)
        else:
            _apply_resonant_capacitor(
                project,
                payload.resonant_capacitor,
                payload.resonant_capacitor.model_fields_set,
            )
    if "controller" in fields:
        if payload.controller is None:
            project.controller_model = None
            _clear_quantities(project, CONTROLLER_QUANTITIES)
        else:
            _apply_controller(
                project,
                payload.controller,
                payload.controller.model_fields_set,
            )
    if "review_requests" in fields:
        _apply_review_requests(project, payload.review_requests or ReviewRequests())
    if "review_settings" in fields:
        _apply_review_settings(project, payload.review_settings or ReviewSettings())

    project.updated_at = utc_now()
    session.commit()
    session.refresh(project)
    return project


def _apply_primary_switch(
    project: Project,
    source: PrimarySwitchInput,
    fields: set[str] | None = None,
) -> None:
    selected = set(type(source).model_fields) if fields is None else fields
    if "manufacturer" in selected:
        project.primary_switch_manufacturer = source.manufacturer
    if "part_number" in selected:
        project.primary_switch_part_number = source.part_number
    if "current_temperature_condition" in selected:
        project.primary_switch_current_temperature_condition = (
            source.current_temperature_condition
        )
    _set_quantities(project, source, PRIMARY_SWITCH_QUANTITIES, selected)


def _clear_primary_switch(project: Project) -> None:
    project.primary_switch_manufacturer = None
    project.primary_switch_part_number = None
    project.primary_switch_current_temperature_condition = None
    _clear_quantities(project, PRIMARY_SWITCH_QUANTITIES)


def _apply_resonant_capacitor(
    project: Project,
    source: ResonantCapacitorInput,
    fields: set[str] | None = None,
) -> None:
    _set_quantities(project, source, RESONANT_CAPACITOR_QUANTITIES, fields)


def _apply_controller(
    project: Project,
    source: ControllerInput,
    fields: set[str] | None = None,
) -> None:
    selected = set(type(source).model_fields) if fields is None else fields
    if "model" in selected:
        project.controller_model = source.model
    _set_quantities(project, source, CONTROLLER_QUANTITIES, selected)


def _apply_review_requests(project: Project, source: ReviewRequests) -> None:
    project.zvs_analysis_requested = source.zvs_analysis_requested
    project.full_gain_review_requested = source.full_gain_review_requested


def _apply_review_settings(project: Project, source: ReviewSettings) -> None:
    project.output_power_relative_tolerance = source.output_power_relative_tolerance
    project.measured_vds_required_margin_ratio = (
        source.measured_vds_required_margin_ratio
    )
    project.gain_review_required_parameters = (
        [value.value for value in source.gain_review_required_parameters]
        if source.gain_review_required_parameters is not None
        else None
    )


def project_to_response(project: Project) -> ProjectResponse:
    project_values = {
        field_name: _from_storage(
            field_name,
            getattr(project, specification.model_attribute),
            specification,
        )
        for field_name, specification in PROJECT_QUANTITIES.items()
    }
    primary_switch = PrimarySwitchInput(
        manufacturer=project.primary_switch_manufacturer,
        part_number=project.primary_switch_part_number,
        current_temperature_condition=(
            project.primary_switch_current_temperature_condition
        ),
        **{
            field_name: _from_storage(
                field_name,
                getattr(project, specification.model_attribute),
                specification,
            )
            for field_name, specification in PRIMARY_SWITCH_QUANTITIES.items()
        },
    )
    resonant_capacitor = ResonantCapacitorInput(
        **{
            field_name: _from_storage(
                field_name,
                getattr(project, specification.model_attribute),
                specification,
            )
            for field_name, specification in RESONANT_CAPACITOR_QUANTITIES.items()
        }
    )
    controller = ControllerInput(
        model=project.controller_model,
        **{
            field_name: _from_storage(
                field_name,
                getattr(project, specification.model_attribute),
                specification,
            )
            for field_name, specification in CONTROLLER_QUANTITIES.items()
        },
    )
    return ProjectResponse(
        id=project.id,
        name=project.name,
        topology="Half-Bridge LLC",
        rectification_type="Diode Rectification",
        primary_switch=primary_switch,
        resonant_capacitor=resonant_capacitor,
        controller=controller,
        review_requests=ReviewRequests(
            zvs_analysis_requested=project.zvs_analysis_requested,
            full_gain_review_requested=project.full_gain_review_requested,
        ),
        review_settings=ReviewSettings(
            output_power_relative_tolerance=project.output_power_relative_tolerance,
            measured_vds_required_margin_ratio=(
                project.measured_vds_required_margin_ratio
            ),
            gain_review_required_parameters=(
                tuple(
                    ReviewParameterName(value)
                    for value in project.gain_review_required_parameters
                )
                if project.gain_review_required_parameters is not None
                else None
            ),
        ),
        created_at=_as_utc(project.created_at),
        updated_at=_as_utc(project.updated_at),
        **project_values,
    )


def project_quantity(
    project: Project, field_name: str
) -> EngineeringQuantity | None:
    specification = PROJECT_QUANTITIES[field_name]
    value = getattr(project, specification.model_attribute)
    if value is None:
        return None
    return EngineeringQuantity(value=value, unit=specification.storage_unit)


def nested_quantity(
    project: Project,
    field_name: str,
    specifications: dict[str, QuantityField],
) -> EngineeringQuantity | None:
    specification = specifications[field_name]
    value = getattr(project, specification.model_attribute)
    if value is None:
        return None
    return EngineeringQuantity(value=value, unit=specification.storage_unit)
