"""心跳事件抽取与静默守护测试。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from src.plugins.nonebot_plugin_llbot_alert import heartbeat as hb


class _FakeBot:
    """仅携带 self_id 的假 Bot。"""

    def __init__(self, self_id: str) -> None:
        self.self_id = self_id


def _event(*, online: bool = True, good: bool = True, self_id: int = 123) -> Any:
    """构造一份 OneBot 心跳事件。"""
    from nonebot.adapters.onebot.v11.event import HeartbeatMetaEvent, Status

    return HeartbeatMetaEvent(
        time=int(datetime.now(UTC).timestamp()),
        self_id=self_id,
        post_type="meta_event",
        meta_event_type="heartbeat",
        status=Status(online=online, good=good),
        interval=6000,
    )


def test_status_from_healthy_heartbeat() -> None:
    """Online 与 good 均为真时账号健康。"""
    status = hb.status_from_event(_event())
    assert status.online is True
    assert status.good is True
    assert status.healthy is True


def test_status_from_offline_heartbeat() -> None:
    """Online 为假时判定账号异常（账号下线）。"""
    status = hb.status_from_event(_event(online=False))
    assert status.healthy is False


def test_status_from_not_good_heartbeat() -> None:
    """Good 为假时判定账号异常。"""
    status = hb.status_from_event(_event(good=False))
    assert status.healthy is False


def test_status_missing_status_field_is_unhealthy() -> None:
    """心跳缺少 status 字段时按不健康处理（宁可告警不可漏报）。"""

    class _NoStatus:
        pass

    status = hb.status_from_event(_NoStatus())  # type: ignore[arg-type]
    assert status.healthy is False
    assert "status" in status.reason


def test_watchdog_touch_and_last_seen() -> None:
    """Touch 记录最后心跳时间。"""
    watchdog = hb.HeartbeatWatchdog.__new__(hb.HeartbeatWatchdog)
    watchdog._last_seen = {}
    assert watchdog.last_seen("123") is None

    watchdog.touch("123")
    assert watchdog.last_seen("123") is not None


def test_watchdog_detects_silent_account() -> None:
    """超过超时未收到心跳的账号被判定为静默。"""
    watchdog = hb.HeartbeatWatchdog.__new__(hb.HeartbeatWatchdog)
    watchdog._last_seen = {}
    watchdog.touch("123")
    watchdog._last_seen["123"] = datetime.now(UTC) - timedelta(seconds=100)

    now = datetime.now(UTC)
    assert watchdog.silent_accounts(timeout=60, now=now) == ["123"]
    assert watchdog.silent_accounts(timeout=200, now=now) == []


def test_watchdog_forget_clears_account() -> None:
    """Forget 清除某账号的心跳记录（断开后由连接事件接管）。"""
    watchdog = hb.HeartbeatWatchdog.__new__(hb.HeartbeatWatchdog)
    watchdog._last_seen = {}
    watchdog.touch("123")

    watchdog.forget("123")

    assert watchdog.last_seen("123") is None


@pytest.mark.asyncio
async def test_watchdog_check_reports_silent_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """静默超时后上报服务异常，并清除该账号记录防重复告警。"""
    reported: list[dict[str, Any]] = []

    class _Center:
        async def report_service(self, **kwargs: Any) -> bool:
            reported.append(kwargs)
            return True

    monkeypatch.setattr(hb.plugin_config, "llbot_alert_heartbeat_timeout", 60)
    watchdog = hb.HeartbeatWatchdog(_Center())  # type: ignore[arg-type]
    watchdog.touch("123")
    watchdog._last_seen["123"] = datetime.now(UTC) - timedelta(seconds=100)

    await watchdog.check_once()

    assert reported and reported[0]["healthy"] is False
    assert reported[0]["self_id"] == "123"
    assert watchdog.last_seen("123") is None  # 已清除
    await watchdog.check_once()
    assert len(reported) == 1  # 不重复上报


@pytest.mark.asyncio
async def test_watchdog_check_disabled_when_timeout_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """超时配置为 0 时不检测静默。"""
    reported: list[dict[str, Any]] = []

    class _Center:
        async def report_service(self, **kwargs: Any) -> bool:
            reported.append(kwargs)
            return True

    monkeypatch.setattr(hb.plugin_config, "llbot_alert_heartbeat_timeout", 0)
    watchdog = hb.HeartbeatWatchdog(_Center())  # type: ignore[arg-type]
    watchdog.touch("123")
    watchdog._last_seen["123"] = datetime.now(UTC) - timedelta(seconds=9999)

    await watchdog.check_once()

    assert reported == []


@pytest.mark.asyncio
async def test_heartbeat_handler_reports_account_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """心跳处理器上报账号状态并刷新静默计时。"""
    from src.plugins.nonebot_plugin_llbot_alert import hooks as hk

    reported: list[Any] = []
    touched: list[str] = []

    class _Center:
        async def report_account(self, *, status: Any, self_id: str = "") -> bool:
            reported.append((status, self_id))
            return True

    class _Watchdog:
        def touch(self, self_id: str) -> None:
            touched.append(self_id)

    monkeypatch.setattr(hk, "get_center", _Center)
    monkeypatch.setattr(hk, "get_watchdog", _Watchdog)
    monkeypatch.setattr(hk.plugin_config, "llbot_alert_enabled", True)
    monkeypatch.setattr(hk.plugin_config, "llbot_alert_accounts", set())

    await hb.on_heartbeat(_FakeBot("123"), _event(online=False, good=False))  # type: ignore[arg-type]

    assert reported and reported[0][0].healthy is False
    assert reported[0][1] == "123"
    assert touched == ["123"]


@pytest.mark.asyncio
async def test_heartbeat_handler_ignores_unwatched_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """不在监控名单内的账号不处理。"""
    from src.plugins.nonebot_plugin_llbot_alert import hooks as hk

    reported: list[Any] = []

    class _Center:
        async def report_account(self, *, status: Any, self_id: str = "") -> bool:
            reported.append(status)
            return True

    monkeypatch.setattr(hk, "get_center", _Center)
    monkeypatch.setattr(hk.plugin_config, "llbot_alert_enabled", True)
    monkeypatch.setattr(hk.plugin_config, "llbot_alert_accounts", {999})

    await hb.on_heartbeat(_FakeBot("123"), _event())  # type: ignore[arg-type]

    assert reported == []


@pytest.mark.asyncio
async def test_heartbeat_handler_respects_disable_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """总开关关闭时不处理心跳。"""
    from src.plugins.nonebot_plugin_llbot_alert import hooks as hk

    reported: list[Any] = []

    class _Center:
        async def report_account(self, *, status: Any, self_id: str = "") -> bool:
            reported.append(status)
            return True

    monkeypatch.setattr(hk, "get_center", _Center)
    monkeypatch.setattr(hk.plugin_config, "llbot_alert_enabled", False)

    await hb.on_heartbeat(_FakeBot("123"), _event())  # type: ignore[arg-type]

    assert reported == []
