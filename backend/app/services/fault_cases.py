import re
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.units import normalize_quantity
from app.models.fault_case import FaultCase
from app.schemas.engineering import EngineeringQuantity
from app.schemas.fault_case import FaultCaseCreate, FaultCaseUpdate, FaultSymptom

_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


def create_fault_case(session: Session, payload: FaultCaseCreate) -> FaultCase:
    case = FaultCase(
        topology=payload.topology,
        power_w=_to_storage("power", payload.power, "W"),
        vin_v=_to_storage("vin", payload.vin, "V"),
        vout_v=_to_storage("vout", payload.vout, "V"),
        load_description=payload.load,
        symptom=payload.symptom.value,
        observed_features=list(payload.observed_features),
        root_cause=payload.root_cause,
        verification_steps=list(payload.verification_steps),
        fix=list(payload.fix),
        waveform_before=payload.waveform_before,
        waveform_after=payload.waveform_after,
        engineer_verified=payload.engineer_verified,
        verification_notes=payload.verification_notes,
    )
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


def list_fault_cases(session: Session) -> list[FaultCase]:
    return list(
        session.scalars(
            select(FaultCase).order_by(FaultCase.created_at.desc(), FaultCase.case_id)
        ).all()
    )


def get_fault_case(session: Session, case_id: str) -> FaultCase | None:
    return session.get(FaultCase, case_id)


def update_fault_case(
    session: Session, case: FaultCase, payload: FaultCaseUpdate
) -> FaultCase:
    fields = payload.model_fields_set
    if "topology" in fields:
        case.topology = payload.topology or "Half-Bridge LLC"
    if "power" in fields:
        case.power_w = _to_storage("power", payload.power, "W")
    if "vin" in fields:
        case.vin_v = _to_storage("vin", payload.vin, "V")
    if "vout" in fields:
        case.vout_v = _to_storage("vout", payload.vout, "V")
    if "load" in fields:
        case.load_description = payload.load
    if "symptom" in fields and payload.symptom is not None:
        case.symptom = payload.symptom.value
    if "observed_features" in fields and payload.observed_features is not None:
        case.observed_features = list(payload.observed_features)
    if "root_cause" in fields and payload.root_cause is not None:
        case.root_cause = payload.root_cause
    if "verification_steps" in fields and payload.verification_steps is not None:
        case.verification_steps = list(payload.verification_steps)
    if "fix" in fields and payload.fix is not None:
        case.fix = list(payload.fix)
    if "waveform_before" in fields:
        case.waveform_before = payload.waveform_before
    if "waveform_after" in fields:
        case.waveform_after = payload.waveform_after
    if "engineer_verified" in fields and payload.engineer_verified is not None:
        case.engineer_verified = payload.engineer_verified
    if "verification_notes" in fields:
        case.verification_notes = payload.verification_notes
    session.commit()
    session.refresh(case)
    return case


def search_fault_cases(
    session: Session,
    *,
    query: str | None = None,
    symptom: FaultSymptom | None = None,
    engineer_verified: bool | None = None,
    limit: int = 50,
) -> list[tuple[FaultCase, float | None]]:
    cases = list_fault_cases(session)
    filtered = [
        case
        for case in cases
        if (symptom is None or case.symptom == symptom.value)
        and (
            engineer_verified is None
            or case.engineer_verified is engineer_verified
        )
    ]
    query_tokens = _tokens(query or "")
    scored = [
        (case, _similarity(query_tokens, _case_tokens(case)) if query_tokens else None)
        for case in filtered
    ]
    if query_tokens:
        scored = [(case, score) for case, score in scored if score and score > 0]
        scored.sort(key=lambda item: item[0].created_at, reverse=True)
        scored.sort(key=lambda item: float(item[1] or 0), reverse=True)
    return scored[:limit]


def _to_storage(
    name: str, quantity: EngineeringQuantity | None, target_unit: str
) -> float | None:
    if quantity is None:
        return None
    return normalize_quantity(name=name, quantity=quantity, target_unit=target_unit).value


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN_PATTERN.findall(value)}


def _case_tokens(case: FaultCase) -> set[str]:
    fields: Iterable[str] = (
        case.symptom,
        case.root_cause,
        case.load_description or "",
        *case.observed_features,
        *case.verification_steps,
        *case.fix,
    )
    return _tokens(" ".join(fields))


def _similarity(query_tokens: set[str], case_tokens: set[str]) -> float:
    if not query_tokens or not case_tokens:
        return 0.0
    return len(query_tokens & case_tokens) / len(query_tokens | case_tokens)
