"""邮件构造与发送守卫测试。"""

from __future__ import annotations

import pytest

from src.plugins.nonebot_plugin_llbot_alert.config import Config
from src.plugins.nonebot_plugin_llbot_alert.mailer import (
    build_message,
    resolve_recipients,
    send_alert_mail,
)


def test_resolve_recipients_sorted_and_filtered() -> None:
    """收件人排序输出，过滤空白项。"""
    config = Config(llbot_alert_to={"b@test.invalid", "a@test.invalid", "  "})
    assert resolve_recipients(config) == ["a@test.invalid", "b@test.invalid"]


def test_build_message_headers() -> None:
    """邮件头包含发件人、收件人与主题，正文写入内容。"""
    config = Config(
        llbot_alert_mail_from="alert@hikarilink.org",
        llbot_alert_mail_from_name="LLBot Alert",
        llbot_alert_smtp_user="relay@hikarilink.org",
    )
    message = build_message(
        config,
        recipients=["me@test.invalid"],
        subject="【LLBot 告警】服务异常",
        body="正文内容",
    )
    assert "LLBot Alert" in str(message["From"])
    assert "alert@hikarilink.org" in str(message["From"])
    assert str(message["To"]) == "me@test.invalid"
    assert str(message["Subject"]) == "【LLBot 告警】服务异常"
    assert "正文内容" in message.get_content()


def test_build_message_falls_back_to_smtp_user_as_sender() -> None:
    """未配置发件人地址时回退到 SMTP 用户名。"""
    config = Config(llbot_alert_smtp_user="relay@hikarilink.org")
    message = build_message(
        config,
        recipients=["me@test.invalid"],
        subject="s",
        body="b",
    )
    assert "relay@hikarilink.org" in str(message["From"])


@pytest.mark.asyncio
async def test_send_skips_without_recipients() -> None:
    """未配置收件人时跳过发送且不报错。"""
    config = Config(llbot_alert_smtp_host="smtp.test.invalid")
    assert await send_alert_mail(config, subject="s", body="b") is False


@pytest.mark.asyncio
async def test_send_skips_without_smtp_host() -> None:
    """未配置 SMTP 服务器时跳过发送且不报错。"""
    config = Config(llbot_alert_to={"me@test.invalid"})
    assert await send_alert_mail(config, subject="s", body="b") is False
