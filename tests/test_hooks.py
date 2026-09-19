"""连接事件监控范围与轮询编排测试。"""

from __future__ import annotations

from typing import Any

import pytest

from src.plugins.nonebot_plugin_llbot_alert import hooks


class _FakeBot:
    """仅携带 self_id 的假 Bot。"""

    def __init__(self, self_id: str) -> None:
        self.self_id = self_id


@pytest.fixture(autouse=True)
def _reset_center(monkeypatch: pytest.MonkeyPatch) -> None:
    """每个测试重置全局告警中心，避免状态串扰。"""
    monkeypatch.setattr(hooks._state, "center", None)


def test_monitors_all_accounts_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """未配置账号白名单时监控全部。"""
    monkeypatch.setattr(hooks.plugin_config, "llbot_alert_accounts", set())
    assert hooks.is_watched(_FakeBot("123")) is True  # type: ignore[arg-type]


def test_filters_by_configured_accounts(monkeypatch: pytest.MonkeyPatch) -> None:
    """配置账号白名单后只监控名单内账号。"""
    monkeypatch.setattr(hooks.plugin_config, "llbot_alert_accounts", {123})
    assert hooks.is_watched(_FakeBot("123")) is True  # type: ignore[arg-type]
    assert hooks.is_watched(_FakeBot("456")) is False  # type: ignore[arg-type]


def test_unparsable_self_id_is_not_watched(monkeypatch: pytest.MonkeyPatch) -> None:
    """self_id 无法解析时不监控。"""
    monkeypatch.setattr(hooks.plugin_config, "llbot_alert_accounts", {123})
    assert hooks.is_watched(_FakeBot("not-a-number")) is False  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_disconnect_triggers_service_alert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bot 断开触发服务异常上报。"""
    monkeypatch.setattr(hooks.plugin_config, "llbot_alert_enabled", True)
    monkeypatch.setattr(hooks.plugin_config, "llbot_alert_accounts", set())
    recorded: list[dict[str, Any]] = []

    async def fake_report(**kwargs: Any) -> bool:
        recorded.append(kwargs)
        return True

    monkeypatch.setattr(hooks.get_center(), "report_service", fake_report)

    await hooks.on_llbot_disconnected(_FakeBot("123"))  # type: ignore[arg-type]

    assert recorded and recorded[0]["healthy"] is False
    assert recorded[0]["self_id"] == "123"


@pytest.mark.asyncio
async def test_connect_triggers_service_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bot 连接触发服务恢复上报。"""
    monkeypatch.setattr(hooks.plugin_config, "llbot_alert_enabled", True)
    monkeypatch.setattr(hooks.plugin_config, "llbot_alert_accounts", set())
    recorded: list[dict[str, Any]] = []

    async def fake_report(**kwargs: Any) -> bool:
        recorded.append(kwargs)
        return True

    monkeypatch.setattr(hooks.get_center(), "report_service", fake_report)

    await hooks.on_llbot_connected(_FakeBot("123"))  # type: ignore[arg-type]

    assert recorded and recorded[0]["healthy"] is True


@pytest.mark.asyncio
async def test_disabled_plugin_ignores_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """总开关关闭时不处理连接事件。"""
    monkeypatch.setattr(hooks.plugin_config, "llbot_alert_enabled", False)
    recorded: list[dict[str, Any]] = []

    async def fake_report(**kwargs: Any) -> bool:
        recorded.append(kwargs)
        return True

    monkeypatch.setattr(hooks.get_center(), "report_service", fake_report)

    await hooks.on_llbot_disconnected(_FakeBot("123"))  # type: ignore[arg-type]

    assert recorded == []
