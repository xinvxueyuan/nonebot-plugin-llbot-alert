"""/get_status 响应解析测试。"""

from __future__ import annotations

from typing import Any

import pytest

from src.plugins.nonebot_plugin_llbot_alert.config import Config
from src.plugins.nonebot_plugin_llbot_alert.llbot_api import fetch_status, parse_status


def _payload(**data: Any) -> dict[str, Any]:
    """构造一份符合文档结构的响应。"""
    base = {"online": True, "good": True}
    base.update(data)
    return {
        "status": "ok",
        "retcode": 0,
        "data": base,
        "message": "",
        "wording": "",
    }


def test_parse_status_healthy() -> None:
    """Online 与 good 均为真时判定健康。"""
    status = parse_status(_payload())
    assert status is not None
    assert status.healthy is True


def test_parse_status_offline() -> None:
    """Online 为假时判定账号异常。"""
    status = parse_status(_payload(online=False))
    assert status is not None
    assert status.healthy is False


def test_parse_status_not_good() -> None:
    """Good 为假时判定账号异常。"""
    status = parse_status(_payload(good=False))
    assert status is not None
    assert status.healthy is False


def test_parse_status_reads_reason_fields() -> None:
    """解析 message / wording 作为异常原因。"""
    payload = _payload(online=False)
    payload["message"] = "账号已离线"
    payload["wording"] = "在另一台设备登录"
    status = parse_status(payload)
    assert status is not None
    assert status.reason == "账号已离线 / 在另一台设备登录"


def test_parse_status_tolerates_string_booleans() -> None:
    """字段以字符串表达时也能解析。"""
    payload = _payload()
    payload["data"] = {"online": "false", "good": "true"}
    status = parse_status(payload)
    assert status is not None
    assert status.online is False
    assert status.healthy is False


def test_parse_status_rejects_bad_payload() -> None:
    """结构不符时返回 None，避免误判。"""
    assert parse_status("not-a-dict") is None
    assert parse_status({}) is None
    assert parse_status({"data": {}}) is None
    assert parse_status({"data": "nope"}) is None


@pytest.mark.asyncio
async def test_fetch_status_parses_response(respx_mock: Any) -> None:
    """接口正常应答时返回解析后的状态。"""
    respx_mock.post("http://127.0.0.1:3000/get_status").respond(
        json=_payload(online=False, message="账号已离线")
    )
    config = Config(llbot_alert_api_url="http://127.0.0.1:3000/get_status")

    status = await fetch_status(config)

    assert status is not None
    assert status.online is False


@pytest.mark.asyncio
async def test_fetch_status_returns_none_on_http_error(respx_mock: Any) -> None:
    """HTTP 非 200 时返回 None（不判定为账号异常）。"""
    respx_mock.post("http://127.0.0.1:3000/get_status").respond(status_code=502)
    config = Config(llbot_alert_api_url="http://127.0.0.1:3000/get_status")

    assert await fetch_status(config) is None


@pytest.mark.asyncio
async def test_fetch_status_returns_none_on_network_error(respx_mock: Any) -> None:
    """网络异常时返回 None。"""
    import httpx

    respx_mock.post("http://127.0.0.1:3000/get_status").mock(
        side_effect=httpx.ConnectError("boom")
    )
    config = Config(llbot_alert_api_url="http://127.0.0.1:3000/get_status")

    assert await fetch_status(config) is None


@pytest.mark.asyncio
async def test_fetch_status_sends_bearer_token(respx_mock: Any) -> None:
    """配置了 Token 时带上 Bearer 认证头。"""
    route = respx_mock.post("http://127.0.0.1:3000/get_status").respond(json=_payload())
    config = Config(
        llbot_alert_api_url="http://127.0.0.1:3000/get_status",
        llbot_alert_api_token="secret-token",
    )

    await fetch_status(config)

    assert route.calls[0].request.headers["Authorization"] == "Bearer secret-token"
