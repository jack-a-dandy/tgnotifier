from aiogram import Bot
from ..core.settings import settings

bot = Bot(token=settings.TELEGRAM_BOT_API_KEY.get_secret_value())
Bot.set_current(bot)
