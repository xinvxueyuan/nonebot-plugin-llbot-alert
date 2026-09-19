"""账号状态轮询：定时调用 LLBot 的 ``/get_status`` 判断账号是否异常。

服务异常（OneBot 连接断开）由 NoneBot 的 ``on_bot_disconnect`` 钩子捕获；
本模块只负责**账号异常**——即连接仍在、但账号已下线（被踢下线、登录失效
或被冻结）的情形。

"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from nonebot import logger

from .core import plugin_config
from .llbot_api import fetch_status

if TYPE_CHECKING:
    from .alerter import AlertCenter

_MIN_INTERVAL = 5


def poll_interval() -> int:
    """返回实际使用的轮询间隔（秒，下限 5 秒）。"""
    return max(_MIN_INTERVAL, plugin_config.llbot_alert_poll_interval)


async def poll_once(center: AlertCenter) -> bool:
    """执行一次账号状态检测并上报结果。

    Args:
        center: 告警中心。

    Returns:
        是否因状态变化而发送了邮件。

    """
    status = await fetch_status(plugin_config)
    if status is None:
        logger.debug("未取到 LLBot 账号状态，本次跳过（服务异常由连接事件覆盖）")
        return False
    if not status.healthy:
        logger.warning(
            "检测到 LLBot 账号异常: online={} good={} reason={}",
            status.online,
            status.good,
            status.reason or "-",
        )
    return await center.report_account(status=status)


async def poll_loop(center: AlertCenter, stop: asyncio.Event) -> None:
    """按配置间隔持续检测账号状态，直到 ``stop`` 被置位。

    Args:
        center: 告警中心。
        stop: 停止信号。

    """
    interval = poll_interval()
    logger.info("LLBot 账号状态轮询已启动（间隔 {}s）", interval)
    while not stop.is_set():
        try:
            await poll_once(center)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - 单次检测失败不应终止轮询
            logger.exception("账号状态检测出现未预期异常")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            continue
    logger.info("LLBot 账号状态轮询已停止")
