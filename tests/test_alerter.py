"""告警状态机测试（核心逻辑）。"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from src.plugins.nonebot_plugin_llbot_alert.alerter import AlertCenter
from src.plugins.nonebot_plugin_llbot_alert.config import Config
from src.plugins.nonebot_plugin_llbot_alert.models import BotStatus


class _Recorder:
    """记录被发送的邮件（替代真实 SMTP）。"""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    async def __call__(self, config: Any, *, subject: str, body: str) -> bool:
        _ = config
        self.sent.append({"subject": subject, "body": body})
        return True


def _center(**kwargs: Any) -> tuple[AlertCenter, _Recorder]:
    """构造带记录器的告警中心。"""
    recorder = _Recorder()
    config = Config(llbot_alert_to={"alerts@test.invalid"}, **kwargs)
    return AlertCenter(config, sender=recorder), recorder


@pytest.mark.asyncio
async def test_service_down_alerts_once() -> None:
    """服务异常首次上报即告警，冷却期内重复上报不再发。"""
    center, recorder = _center()

    assert (
        await center.report_service(self_id="123", healthy=False, reason="断连") is True
    )
    assert len(recorder.sent) == 1
    assert "服务异常" in recorder.sent[0]["subject"]
    assert "断连" in recorder.sent[0]["body"]

    assert await center.report_service(self_id="123", healthy=False) is False
    assert len(recorder.sent) == 1


@pytest.mark.asyncio
async def test_recovery_sends_notice() -> None:
    """故障恢复时补发恢复通知。"""
    center, recorder = _center()

    await center.report_service(self_id="123", healthy=False)
    assert await center.report_service(self_id="123", healthy=True) is True

    assert len(recorder.sent) == 2
    assert "恢复" in recorder.sent[1]["subject"]


@pytest.mark.asyncio
async def test_recovery_notice_can_be_disabled() -> None:
    """关闭恢复通知后不再发送恢复邮件。"""
    center, recorder = _center(llbot_alert_notify_recovery=False)

    await center.report_service(self_id="123", healthy=False)
    assert await center.report_service(self_id="123", healthy=True) is False

    assert len(recorder.sent) == 1


@pytest.mark.asyncio
async def test_healthy_without_prior_alert_is_silent() -> None:
    """从未告警时上报健康不产生邮件。"""
    center, recorder = _center()

    assert await center.report_service(self_id="123", healthy=True) is False

    assert recorder.sent == []


@pytest.mark.asyncio
async def test_account_offline_alert() -> None:
    """账号异常上报发送含原因的告警邮件。"""
    center, recorder = _center()
    status = BotStatus(online=False, good=False, message="账号已离线")

    assert await center.report_account(status=status) is True

    assert "账号异常" in recorder.sent[0]["subject"]
    assert "账号已离线" in recorder.sent[0]["body"]


@pytest.mark.asyncio
async def test_healthy_account_sends_nothing() -> None:
    """账号健康时不发邮件。"""
    center, recorder = _center()

    assert (
        await center.report_account(status=BotStatus(online=True, good=True)) is False
    )
    assert recorder.sent == []


@pytest.mark.asyncio
async def test_cooldown_zero_disables_resend() -> None:
    """冷却期为 0 时，持续异常只在首次发送。"""
    center, recorder = _center(llbot_alert_cooldown=0)

    await center.report_service(self_id="1", healthy=False)
    await center.report_service(self_id="1", healthy=False)

    assert len(recorder.sent) == 1


@pytest.mark.asyncio
async def test_cooldown_elapsed_resends_with_marker() -> None:
    """超过冷却期仍异常时重发提醒（主题标注「持续异常」）。"""
    center, recorder = _center(llbot_alert_cooldown=600)
    await center.report_service(self_id="1", healthy=False)

    state = center.state_of("service:1")
    assert state.last_alert_at is not None
    state.last_alert_at -= timedelta(seconds=1000)

    assert await center.report_service(self_id="1", healthy=False) is True
    assert len(recorder.sent) == 2
    assert "持续异常" in recorder.sent[1]["subject"]


@pytest.mark.asyncio
async def test_service_and_account_states_are_independent() -> None:
    """服务异常与账号异常分别维护状态（互不影响）。"""
    center, recorder = _center()

    await center.report_service(self_id="123", healthy=False)
    await center.report_account(status=BotStatus(online=False, good=False))

    assert len(recorder.sent) == 2
    assert "服务异常" in recorder.sent[0]["subject"]
    assert "账号异常" in recorder.sent[1]["subject"]

    # 服务恢复不影响账号异常的持续状态
    await center.report_service(self_id="123", healthy=True)
    assert center.state_of("account").alerting is True


@pytest.mark.asyncio
async def test_different_accounts_are_tracked_separately() -> None:
    """不同账号的服务状态互不干扰。"""
    center, recorder = _center()

    await center.report_service(self_id="111", healthy=False)
    assert await center.report_service(self_id="222", healthy=False) is True

    assert len(recorder.sent) == 2
