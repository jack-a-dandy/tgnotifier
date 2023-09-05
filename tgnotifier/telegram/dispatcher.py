from aiogram import Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from .bot import bot
from tgnotifier.core.settings import settings

storage = RedisStorage2(host=settings.REDISHOST, port=settings.REDISPORT, 
	password=settings.REDISPASSWORD.get_secret_value())

dispatcher = Dispatcher(bot, storage=storage)
dispatcher.middleware.setup(LoggingMiddleware())
