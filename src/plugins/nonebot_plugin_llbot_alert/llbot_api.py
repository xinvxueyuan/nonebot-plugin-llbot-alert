"""调用 LLBot 的 ``/get_status`` 接口获取账号状态。

接口形态（见 LLBot 接口文档「bot状态」）::

    POST /get_status
    Authorization: Bearer <token>

    {"status": "...", "retcode": 0,
     "data": {"online": true, "good": true,
              "stat": {"message_received": 0, "message_sent": 0,
                       "last_message_time": 0, "startup_time": 0}},
     "message": "...", "wording": "..."}

``data.online`` 与 ``data.good`` 共同反映账号是否正常，任一为 ``False`` 即视为
**账号异常（账号下线）**。

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
from nonebot import logger

from .models import BotStatus

if TYPE_CHECKING:
    from .config import Config

_HTTP_OK = 200


async def fetch_status(config: Config) -> BotStatus | None:
    """请求 LLBot 的 ``/get_status`` 并解析账号状态。

    仅当接口正常应答（HTTP 200 且响应可解析）时返回状态；网络异常、非 200
    或响应结构不符时返回 ``None``——此时无法判定账号是否异常，交由「服务异常」
    检测（OneBot 连接断开）覆盖，避免误报账号下线。

    Args:
        config: 插件配置（提供接口地址、Token 与超时）。

    Returns:
        解析出的账号状态；无法获取时返回 ``None``。

    """
    headers = {"Authorization": f"Bearer {config.llbot_alert_api_token}"}
    if not config.llbot_alert_api_token:
        headers.pop("Authorization")
    try:
        async with httpx.AsyncClient(timeout=config.llbot_alert_api_timeout) as client:
            response = await client.post(config.llbot_alert_api_url, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("LLBot 状态接口请求失败: {}", exc)
        return None
    if response.status_code != _HTTP_OK:
        logger.warning("LLBot 状态接口返回 HTTP {}", response.status_code)
        return None
    try:
        payload = response.json()
    except ValueError:
        logger.warning("LLBot 状态接口响应不是合法 JSON")
        return None
    status = parse_status(payload)
    if status is None:
        logger.warning("LLBot 状态接口响应结构无法解析: {}", payload)
    return status


def _as_bool(value: Any) -> bool | None:
    """把响应字段宽松地转为布尔值；无法解释时返回 ``None``。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no", ""):
            return False
    return None


def _as_text(value: Any) -> str | None:
    """把响应字段转为可读文本；空值返回 ``None``。"""
    if isinstance(value, str):
        return value.strip() or None
    if value is None:
        return None
    return str(value)


def parse_status(payload: Any) -> BotStatus | None:
    """把 ``/get_status`` 的响应解析为 :class:`BotStatus`。

    Args:
        payload: 接口返回的 JSON 对象。

    Returns:
        解析结果；``data`` 缺失或 ``online``/``good`` 无法解释时返回 ``None``。

    """
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    online = _as_bool(data.get("online"))
    good = _as_bool(data.get("good"))
    if online is None and good is None:
        return None
    retcode = payload.get("retcode")
    return BotStatus(
        online=bool(online),
        good=bool(good),
        retcode=retcode if isinstance(retcode, int) else None,
        message=_as_text(payload.get("message")),
        wording=_as_text(payload.get("wording")),
    )
