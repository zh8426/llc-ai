import httpx
import pytest


@pytest.mark.anyio
async def test_request_validation_uses_structured_error(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.post("/projects", json={})

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "INVALID_REQUEST"
    assert payload["message"]
    assert payload["details"]["errors"]
    assert "detail" not in payload


@pytest.mark.anyio
async def test_unknown_route_uses_structured_error(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.get("/not-a-real-route")

    assert response.status_code == 404
    assert response.json() == {
        "code": "RESOURCE_NOT_FOUND",
        "message": "请求的资源不存在。",
        "details": None,
    }


@pytest.mark.anyio
async def test_method_not_allowed_uses_structured_error(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.put("/health")

    assert response.status_code == 405
    assert response.json() == {
        "code": "METHOD_NOT_ALLOWED",
        "message": "请求方法不被允许。",
        "details": None,
    }
