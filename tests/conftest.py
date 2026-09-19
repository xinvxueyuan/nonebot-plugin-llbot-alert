"""pytest 配置与 NoneBot 初始化。"""

from __future__ import annotations

import os
from pathlib import Path

import nonebot
from nonebug import NONEBOT_START_LIFESPAN

_PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def pytest_configure(config: object) -> None:
    """在收集测试之前初始化 NoneBot 驱动（插件配置依赖它）。"""
    os.environ.setdefault("ENVIRONMENT", "test")
    # 测试环境固定使用假 SMTP / 收件人，避免误发真实邮件。
    os.environ.setdefault("LLBOT_ALERT_SMTP_HOST", "smtp.test.invalid")
    os.environ.setdefault("LLBOT_ALERT_TO", '["alerts@test.invalid"]')
    os.environ.setdefault("LLBOT_ALERT_API_URL", "http://127.0.0.1:3000/get_status")
    config.stash[NONEBOT_START_LIFESPAN] = True  # type: ignore[attr-defined]

    try:
        nonebot.get_driver()
    except ValueError:
        nonebot.init(driver="~fastapi+~httpx+~websockets")
    else:
        return


def pytest_unconfigure() -> None:
    """清理 NoneBot 驱动状态。"""
    try:
        nonebot.get_driver()
    except ValueError:
        return
    nonebot._driver = None
