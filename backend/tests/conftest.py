from collections.abc import Callable, Iterator

import httpx
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_session
from app.engine import (
    calculate_fp,
    calculate_fr,
    calculate_input_power,
    calculate_lm_lr_ratio,
    calculate_output_current,
    calculate_zr,
)
from app.main import app
from app.models import Base
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
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def api_session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    yield testing_session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
async def api_client(
    api_session_factory: sessionmaker[Session],
) -> httpx.AsyncClient:

    def override_get_session():
        with api_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def api_project_payload() -> dict[str, object]:
    return {
        "name": "500 W / 48 V API fixture",
        "vin_min": {"value": 300, "unit": "V"},
        "vin_nom": {"value": 360, "unit": "V"},
        "vin_max": {"value": 420, "unit": "V"},
        "vout": {"value": 48, "unit": "V"},
        "iout": {"value": 500 / 48, "unit": "A"},
        "pout": {"value": 500, "unit": "W"},
        "target_efficiency": {"value": 94, "unit": "percent"},
        "lr": {"value": 45, "unit": "uH"},
        "lm": {"value": 300, "unit": "uH"},
        "cr": {"value": 47, "unit": "nF"},
        "fsw_min": {"value": 60, "unit": "kHz"},
        "fsw_nom": {"value": 100, "unit": "kHz"},
        "fsw_max": {"value": 150, "unit": "kHz"},
        "transformer_ratio": {"value": 4, "unit": "dimensionless"},
        "dead_time": {"value": 300, "unit": "ns"},
        "primary_switch": {
            "manufacturer": "Fixture Semiconductor",
            "part_number": "TEST-650V",
            "vds_rating": {"value": 650, "unit": "V"},
            "measured_vds_peak": {"value": 500, "unit": "V"},
            "current_rating": {"value": 20, "unit": "A"},
            "measured_peak_current": {"value": 10, "unit": "A"},
            "current_temperature_condition": "Test fixture condition",
        },
        "resonant_capacitor": {
            "voltage_rating": {"value": 1000, "unit": "V"},
            "voltage_stress": {"value": 500, "unit": "V"},
            "rms_current_rating": {"value": 12, "unit": "A"},
            "rms_current_stress": {"value": 8, "unit": "A"},
        },
        "controller": {
            "model": "Fixture Controller",
            "frequency_min": {"value": 40, "unit": "kHz"},
            "frequency_max": {"value": 500, "unit": "kHz"},
        },
        "review_requests": {
            "zvs_analysis_requested": True,
            "full_gain_review_requested": True,
        },
        "review_settings": {
            "output_power_relative_tolerance": 0.01,
            "measured_vds_required_margin_ratio": 0.20,
            "gain_review_required_parameters": [
                "vin_min",
                "vin_max",
                "vout",
                "pout",
                "lr",
                "lm",
                "cr",
                "fsw_min",
                "fsw_max",
                "transformer_ratio",
            ],
        },
    }


@pytest.fixture
def normal_review_context() -> ReviewContext:
    context = ReviewContext(
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
    project = context.project
    calculations = (
        calculate_fr(lr=project.lr, cr=project.cr),
        calculate_fp(lr=project.lr, lm=project.lm, cr=project.cr),
        calculate_zr(lr=project.lr, cr=project.cr),
        calculate_lm_lr_ratio(lr=project.lr, lm=project.lm),
        calculate_output_current(pout=project.pout, vout=project.vout),
        calculate_input_power(pout=project.pout, efficiency=q(0.94, "dimensionless")),
    )
    return context.model_copy(
        update={
            "calculated_inputs": {result.name: result for result in calculations}
        }
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
