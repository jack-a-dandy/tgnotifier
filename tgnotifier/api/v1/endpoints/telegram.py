from typing import (
    Dict,
    Any,
)

from aiogram import Dispatcher
from aiogram.types import Update
from aiogram.types.bot_command import BotCommand
from fastapi import (
    APIRouter,
    Depends,
    Body,
)
from fastapi_security_telegram_webhook import OnlyTelegramNetworkWithSecret
from starlette.responses import Response
from starlette.status import HTTP_200_OK
from tgnotifier.core.settings import settings
from ..deps import get_bot, get_dispatcher
from tgnotifier.telegram.commands import commands_dict
from tgnotifier.telegram.fsm import *
from tgnotifier.utils.log import log
import traceback

router = APIRouter()

telegram_webhook_security = OnlyTelegramNetworkWithSecret(
    real_secret=settings.TELEGRAM_BOT_WEBHOOK_SECRET.get_secret_value()
)

@router.on_event("startup")
async def set_webhook() -> None:
    """
    Tell Telegram API about new webhook on app startup.
    We need to check current webhook url first, because Telegram API has
    strong rate limit for `set_webhook` method.
    """
    bot = get_bot()
    url = "{endpoint}/{secret}".format(
        endpoint=settings.TELEGRAM_BOT_WEBHOOK_ENDPOINT.rstrip("/"),
        secret=settings.TELEGRAM_BOT_WEBHOOK_SECRET.get_secret_value(),
    )
    current_url = (await bot.get_webhook_info())["url"]
    if current_url != url:
        await bot.set_webhook(url=url)


@router.on_event("startup")
async def set_commands() -> None:
    bot = get_bot()
    await bot.set_my_commands(commands=[BotCommand(k, v) for k,v in commands_dict.items()])


@router.on_event("shutdown")
async def disconnect_storage() -> None:
    """
    Close connection to storage.
    """
    dispatcher = get_dispatcher()
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


@router.post("/webhook/{secret}", dependencies=[Depends(telegram_webhook_security)])
async def telegram_webhook(
    update_raw: Dict[str, Any] = Body(...), dp: Dispatcher = Depends(get_dispatcher),
) -> Response:
    """
    Pass the new update (event from telegram) to bot dispatcher for processing.
    """
    telegram_update = Update(**update_raw)
    try:
        await dp.process_update(telegram_update)
        return Response(status_code=HTTP_200_OK)
    except Exception as e:
        log(str(e))
        traceback.print_exc()
        return Response(status_code=HTTP_200_OK)