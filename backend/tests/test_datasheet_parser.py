import pytest

from app.datasheet.parser import parse_mosfet_datasheet
from app.schemas.datasheet import DatasheetParameterName, DatasheetValueType


def test_parse_mosfet_datasheet_preserves_identity_and_normalizes_units() -> None:
    pages = [
        """
        Manufacturer: Example Semi
        Part Number: TEST650
        VDS (Drain-Source Voltage) 650 V maximum
        ID Continuous Drain Current 20 A typical
        RDS(on) 80 mΩ typical
        Qg 120 nC typical
        Coss 200 pF
        Eoss 30 uJ
        RthJC 1.2 °C/W
        Tj Max 150 °C
        Package: TO-247
        """
    ]

    candidates, identity = parse_mosfet_datasheet(pages)
    by_name = {candidate.parameter_name: candidate for candidate in candidates}

    assert identity == {"manufacturer": "Example Semi", "part_number": "TEST650"}
    assert by_name[DatasheetParameterName.VDS].value == 650
    assert by_name[DatasheetParameterName.VDS].unit == "V"
    assert by_name[DatasheetParameterName.VDS].value_type == DatasheetValueType.MAXIMUM
    assert by_name[DatasheetParameterName.RDS_ON].value == 0.08
    assert by_name[DatasheetParameterName.QG].value == pytest.approx(120e-9)
    assert by_name[DatasheetParameterName.PACKAGE].value == "TO-247"
    assert by_name[DatasheetParameterName.PACKAGE].unit == "text"
    assert by_name[DatasheetParameterName.VDS].source_page == 1
    assert by_name[DatasheetParameterName.VDS].test_condition["source_line"]


def test_parse_mosfet_datasheet_does_not_guess_missing_parameters() -> None:
    candidates, identity = parse_mosfet_datasheet(["Manufacturer: Example Semi"])

    assert candidates == []
    assert identity == {"manufacturer": "Example Semi", "part_number": None}
