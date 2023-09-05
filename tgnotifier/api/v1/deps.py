from aiogram import (
    Dispatcher,
    Bot,
)
from tgnotifier.telegram.dispatcher import dispatcher
from tgnotifier.db.session import db, db_state_default
from fastapi import Depends, HTTPException, status
from typing import Optional
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from tgnotifier.core.settings import settings


def get_dispatcher() -> Dispatcher:
    """
    Set context manually for properly processing webhook updates.
    Source: https://t.me/aiogram_ru/167051
    """
    Bot.set_current(dispatcher.bot)
    Dispatcher.set_current(dispatcher)
    return dispatcher


def get_bot() -> Bot:
    return dispatcher.bot

   
async def reset_db_state():
    db._state._state.set(db_state_default.copy())
    db._state.reset()


def get_db(db_state=Depends(reset_db_state)):
    try:
        db.connect()
        yield
    finally:
        if not db.is_closed():
            db.close()
