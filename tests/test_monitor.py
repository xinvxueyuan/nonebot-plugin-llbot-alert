"""账号状态轮询测试。"""

from __future__ import annotations

from typing import Any

import pytest

from src.plugins.nonebot_plugin_llbot_alert import monitor
from src.plugins.nonebot_plugin_llbot_alert.models import BotStatus


class _RecordingCenter:
    """记录上报内容的假告警中心。"""

    def __init__(self) -> None:
        self.reported: list[BotStatus] = []

    async def report_account(self, *, status: BotStatus, self_id: str = "") -> bool:
        _ = self_id
        self.reported.append(status)
        return True


@pytest.mark.asyncio
async def test_poll_once_skips_when_status_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """取不到账号状态时不上报（交由服务异常检测覆盖，避免误报）。"""

    async def fake_fetch(_config: Any) -> None:
        return None

    monkeypatch.setattr(monitor, "fetch_status", fake_fetch)
    center = _RecordingCenter()

    assert await monitor.poll_once(center) is False  # type: ignore[arg-type]
    assert center.reported == []


@pytest.mark.asyncio
async def test_poll_once_reports_offline_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """账号异常时把状态上报给告警中心。"""

    async def fake_fetch(_config: Any) -> BotStatus:
        return BotStatus(online=False, good=False, message="账号已离线")

    monkeypatch.setattr(monitor, "fetch_status", fake_fetch)
    center = _RecordingCenter()

    assert await monitor.poll_once(center) is True  # type: ignore[arg-type]
    assert len(center.reported) == 1
    assert center.reported[0].online is False


@pytest.mark.asyncio
async def test_poll_once_reports_healthy_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """账号健康时同样上报（用于触发恢复通知）。"""

    async def fake_fetch(_config: Any) -> BotStatus:
        return BotStatus(online=True, good=True)

    monkeypatch.setattr(monitor, "fetch_status", fake_fetch)
    center = _RecordingCenter()

    await monitor.poll_once(center)  # type: ignore[arg-type]

    assert len(center.reported) == 1
    assert center.reported[0].healthy is True


def test_poll_interval_has_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    """轮询间隔设有下限，避免配置成 0 造成空转。"""
    monkeypatch.setattr(monitor.plugin_config, "llbot_alert_poll_interval", 0)
    assert monitor.poll_interval() == 5

    monkeypatch.setattr(monitor.plugin_config, "llbot_alert_poll_interval", 120)
    assert monitor.poll_interval() == 120
