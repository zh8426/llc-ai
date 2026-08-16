import re
from dataclasses import dataclass
from io import BytesIO
from typing import Final

from app.engine.units import normalize_quantity
from app.schemas.datasheet import DatasheetParameterName, DatasheetValueType
from app.schemas.engineering import EngineeringQuantity


class DatasheetExtractionError(ValueError):
    """Raised when a PDF cannot provide text for conservative extraction."""


@dataclass(frozen=True)
class DatasheetCandidate:
    parameter_name: DatasheetParameterName
    value: float | str
    unit: str
    value_type: DatasheetValueType
    test_condition: dict[str, str]
    source_page: int
    confidence: float


_NUMBER: Final[str] = r"(?P<value>\d+(?:[.,]\d+)?)"
_UNIT: Final[str] = r"(?P<unit>[A-Za-zµμΩ°/()]+)"
_PARAMETER_PATTERNS: Final[tuple[tuple[DatasheetParameterName, str, str], ...]] = (
    (
        DatasheetParameterName.VDS,
        rf"(?:VDS|Drain[- ]Source Voltage|Drain Source Voltage)\D{{0,60}}{_NUMBER}\s*{_UNIT}",
        "V",
    ),
    (
        DatasheetParameterName.ID,
        rf"(?:\bID\b|Drain Current|Continuous Drain Current)\D{{0,60}}{_NUMBER}\s*{_UNIT}",
        "A",
    ),
    (
        DatasheetParameterName.RDS_ON,
        rf"(?:RDS\s*\(?ON\)?|Drain[- ]Source On[- ]Resistance)\D{{0,60}}{_NUMBER}\s*{_UNIT}",
        "ohm",
    ),
    (
        DatasheetParameterName.QG,
        rf"(?:\bQg\b|Gate Charge)\D{{0,60}}{_NUMBER}\s*{_UNIT}",
        "coulomb",
    ),
    (
        DatasheetParameterName.COSS,
        rf"(?:\bCoss\b|Output Capacitance)\D{{0,60}}{_NUMBER}\s*{_UNIT}",
        "farad",
    ),
    (
        DatasheetParameterName.EOSS,
        rf"(?:\bEoss\b|Output Energy)\D{{0,60}}{_NUMBER}\s*{_UNIT}",
        "joule",
    ),
    (
        DatasheetParameterName.RTHJC,
        rf"(?:R(?:th|θ)JC|Thermal Resistance Junction[- ]to[- ]Case)\D{{0,60}}{_NUMBER}\s*{_UNIT}",
        "kelvin / watt",
    ),
    (
        DatasheetParameterName.TJ_MAX,
        rf"(?:Tj\s*Max|Junction Temperature)\D{{0,60}}{_NUMBER}\s*{_UNIT}",
        "degC",
    ),
)

_PACKAGE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:Package|Package Type)\s*[:\-]\s*(?P<value>[^,;]+)", re.IGNORECASE
)
_MANUFACTURER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:Manufacturer|Brand)\s*[:\-]\s*(?P<value>[^\r\n]+)", re.IGNORECASE
)
_PART_NUMBER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:Part Number|Part No\.?|Ordering Code)\s*[:\-]\s*(?P<value>[^\r\n]+)",
    re.IGNORECASE,
)


def extract_pdf_pages(pdf_bytes: bytes) -> list[str]:
    """Extract text page-by-page; scanned PDFs require a later OCR extension."""

    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(pdf_bytes))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except Exception as error:  # pypdf exposes several parser-specific exceptions.
        raise DatasheetExtractionError("PDF 无法读取或不包含可提取文本。") from error

    if not pages or not any(page.strip() for page in pages):
        raise DatasheetExtractionError("PDF 无法提取文本；扫描版 PDF 需要后续 OCR 支持。")
    return pages


def parse_mosfet_datasheet(pages: list[str]) -> tuple[list[DatasheetCandidate], dict[str, str | None]]:
    """Extract explicitly labeled MOSFET candidates without inventing missing values."""

    candidates: list[DatasheetCandidate] = []
    identity: dict[str, str | None] = {"manufacturer": None, "part_number": None}
    for page_number, page_text in enumerate(pages, start=1):
        for line in page_text.splitlines():
            normalized_line = " ".join(line.split())
            if not normalized_line:
                continue
            if identity["manufacturer"] is None:
                identity_match = _MANUFACTURER_PATTERN.search(normalized_line)
                if identity_match:
                    identity["manufacturer"] = identity_match.group("value").strip()
            if identity["part_number"] is None:
                part_match = _PART_NUMBER_PATTERN.search(normalized_line)
                if part_match:
                    identity["part_number"] = part_match.group("value").strip()

            package_match = _PACKAGE_PATTERN.search(normalized_line)
            if package_match:
                candidates.append(
                    DatasheetCandidate(
                        parameter_name=DatasheetParameterName.PACKAGE,
                        value=package_match.group("value").strip(),
                        unit="text",
                        value_type=_value_type(normalized_line),
                        test_condition={"source_line": normalized_line},
                        source_page=page_number,
                        confidence=0.6,
                    )
                )

            for parameter_name, pattern, target_unit in _PARAMETER_PATTERNS:
                match = re.search(pattern, normalized_line, re.IGNORECASE)
                if match is None:
                    continue
                try:
                    raw_value = float(match.group("value").replace(",", "."))
                    normalized = normalize_quantity(
                        name=parameter_name.value,
                        quantity=EngineeringQuantity(
                            value=raw_value,
                            unit=_normalize_unit(match.group("unit")),
                        ),
                        target_unit=target_unit,
                    )
                except (TypeError, ValueError):
                    continue
                candidates.append(
                    DatasheetCandidate(
                        parameter_name=parameter_name,
                        value=normalized.value,
                        unit=normalized.unit,
                        value_type=_value_type(normalized_line),
                        test_condition={"source_line": normalized_line},
                        source_page=page_number,
                        confidence=0.8,
                    )
                )
    return candidates, identity


def _value_type(line: str) -> DatasheetValueType:
    lowered = line.lower()
    if any(marker in lowered for marker in ("maximum", " max", "max.")):
        return DatasheetValueType.MAXIMUM
    if any(marker in lowered for marker in ("minimum", " min", "min.")):
        return DatasheetValueType.MINIMUM
    if any(marker in lowered for marker in ("typical", " typ", "typ.")):
        return DatasheetValueType.TYPICAL
    return DatasheetValueType.UNKNOWN


def _normalize_unit(unit: str) -> str:
    return (
        unit.strip()
        .replace("μ", "u")
        .replace("µ", "u")
        .replace("Ω", "ohm")
        .replace("°", "deg")
    )
