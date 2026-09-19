"""NoneBot 钩子：连接事件监听与账号状态轮询的编排。

按 NoneBot 文档「钩子函数」：

- ``driver.on_bot_connect`` —— Bot 连接至 NoneBot（LLBot 服务恢复）；
- ``driver.on_bot_disconnect`` —— Bot 断开连接（LLBot 服务异常）。

"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from nonebot import get_driver, logger

from .alerter import AlertCenter
from .core import plugin_config
from .monitor import poll_loop

if TYPE_CHECKING:
    from nonebot.adapters import Bot

driver = get_driver()


class _PollingState:
    """轮询任务与停止信号的持有者（避免模块级 ``global`` 赋值）。"""

    def __init__(self) -> None:
        self.center: AlertCenter | None = None
        self.stop: asyncio.Event | None = None
        self.task: asyncio.Task[None] | None = None


_state = _PollingState()


def get_center() -> AlertCenter:
    """返回全局告警中心（懒加载单例）。"""
    if _state.center is None:
        _state.center = AlertCenter(plugin_config)
    return _state.center


def is_watched(bot: Bot) -> bool:
    """该 Bot 是否在监控范围内（``LLBOT_ALERT_ACCOUNTS`` 为空表示全部）。"""
    watched = plugin_config.llbot_alert_accounts
    if not watched:
        return True
    try:
        return int(getattr(bot, "self_id", 0) or 0) in watched
    except (TypeError, ValueError):
        return False


@driver.on_startup
async def start_account_polling() -> None:
    """插件启动时开始轮询账号状态（已在运行时忽略重复启动）。"""
    if not plugin_config.llbot_alert_enabled:
        logger.info("llbot-alert 已停用（LLBOT_ALERT_ENABLED=false），不轮询账号状态")
        return
    if _state.task is not None and not _state.task.done():
        return
    _state.stop = asyncio.Event()
    _state.task = asyncio.create_task(poll_loop(get_center(), _state.stop))


@driver.on_shutdown
async def stop_account_polling() -> None:
    """插件停止时结束轮询任务。"""
    if _state.stop is not None:
        _state.stop.set()
    task = _state.task
    if task is not None:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        _state.task = None


@driver.on_bot_connect
async def on_llbot_connected(bot: Bot) -> None:
    """Bot 连接：LLBot 服务恢复（若此前告警则发送恢复通知）。"""
    if not plugin_config.llbot_alert_enabled or not is_watched(bot):
        return
    self_id = str(getattr(bot, "self_id", "") or "")
    logger.info("LLBot 连接建立（账号 {}）", self_id or "-")
    await get_center().report_service(self_id=self_id, healthy=True)


@driver.on_bot_disconnect
async def on_llbot_disconnected(bot: Bot) -> None:
    """Bot 断开：LLBot 服务异常（进程崩溃、网络中断等）。"""
    if not plugin_config.llbot_alert_enabled or not is_watched(bot):
        return
    self_id = str(getattr(bot, "self_id", "") or "")
    logger.warning("LLBot 连接断开（账号 {}），判定为服务异常", self_id or "-")
    await get_center().report_service(
        self_id=self_id,
        healthy=False,
        reason="OneBot 连接断开（LLBot 进程异常、崩溃或网络中断）",
    )
