"""状态模型测试。"""

from __future__ import annotations

from src.plugins.nonebot_plugin_llbot_alert.models import (
    AlertKind,
    AlertState,
    BotStatus,
)


def test_bot_status_healthy_requires_online_and_good() -> None:
    """Online 与 good 同时为真才算健康。"""
    assert BotStatus(online=True, good=True).healthy is True
    assert BotStatus(online=True, good=False).healthy is False
    assert BotStatus(online=False, good=True).healthy is False
    assert BotStatus(online=False, good=False).healthy is False


def test_bot_status_unhealthy_on_nonzero_retcode() -> None:
    """Retcode 非 0 视为异常。"""
    assert BotStatus(online=True, good=True, retcode=0).healthy is True
    assert BotStatus(online=True, good=True, retcode=100).healthy is False
    assert BotStatus(online=True, good=True, retcode=None).healthy is True


def test_bot_status_reason_joins_message_and_wording() -> None:
    """异常原因合并 message 与 wording，忽略空值。"""
    assert BotStatus(online=False, good=False).reason == ""
    assert (
        BotStatus(online=False, good=False, message="账号已离线").reason == "账号已离线"
    )
    assert (
        BotStatus(
            online=False, good=False, message="账号已离线", wording="被踢下线"
        ).reason
        == "账号已离线 / 被踢下线"
    )


def test_alert_kind_labels() -> None:
    """两类异常各有中文标签与说明。"""
    assert AlertKind.SERVICE_DOWN.label == "服务异常"
    assert AlertKind.ACCOUNT_OFFLINE.label == "账号异常"
    assert "连接断开" in AlertKind.SERVICE_DOWN.detail
    assert "账号" in AlertKind.ACCOUNT_OFFLINE.detail


def test_alert_state_defaults() -> None:
    """状态默认健康且未告警。"""
    state = AlertState()
    assert state.healthy is True
    assert state.alerting is False
    assert state.last_alert_at is None
