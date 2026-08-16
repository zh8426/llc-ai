import httpx
import pytest

from app.datasheet.parser import DatasheetExtractionError


@pytest.mark.anyio
async def test_datasheet_upload_persists_candidates_and_human_verification(
    api_client: httpx.AsyncClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.api.datasheets.extract_pdf_pages",
        lambda _pdf_bytes: [
            "Manufacturer: Example Semi\n"
            "Part Number: TEST650\n"
            "VDS 650 V maximum\n"
            "Package: TO-247"
        ],
    )

    response = await api_client.post(
        "/datasheets",
        files={"file": ("test650.pdf", b"not-a-real-pdf", "application/pdf")},
        data={"manufacturer": "Override Semi"},
    )

    assert response.status_code == 201
    document = response.json()
    assert document["manufacturer"] == "Override Semi"
    assert document["part_number"] == "TEST650"
    assert document["parser_status"] == "NEEDS_HUMAN_REVIEW"
    assert {item["parameter_name"] for item in document["parameters"]} == {
        "VDS",
        "Package",
    }
    vds = next(item for item in document["parameters"] if item["parameter_name"] == "VDS")
    assert vds["value"] == 650
    assert vds["human_verified"] is False

    verify_response = await api_client.patch(
        f"/datasheets/{document['id']}/parameters/{vds['id']}",
        json={"human_verified": True},
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["parser_status"] == "NEEDS_HUMAN_REVIEW"
    verified_vds = next(
        item
        for item in verify_response.json()["parameters"]
        if item["parameter_name"] == "VDS"
    )
    assert verified_vds["human_verified"] is True


@pytest.mark.anyio
async def test_datasheet_invalid_pdf_uses_structured_error(
    api_client: httpx.AsyncClient,
    monkeypatch,
) -> None:
    def reject_pdf(_pdf_bytes: bytes) -> list[str]:
        raise DatasheetExtractionError("fixture cannot be parsed")

    monkeypatch.setattr("app.api.datasheets.extract_pdf_pages", reject_pdf)

    response = await api_client.post(
        "/datasheets",
        files={"file": ("broken.pdf", b"broken", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "DATASHEET_PDF_INVALID"
    assert "detail" not in response.json()


@pytest.mark.anyio
async def test_datasheet_not_found_uses_structured_error(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.get("/datasheets/not-present")

    assert response.status_code == 404
    assert response.json()["code"] == "DATASHEET_NOT_FOUND"
