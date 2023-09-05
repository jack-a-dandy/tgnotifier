import pytz
from datetime import datetime

moscowtz = pytz.timezone("Europe/Moscow")

def log(s, error=True):
	print(f'{"ERROR" if error else "NOTICE"}: {datetime.now(tz=moscowtz).strftime("%H:%M:%S")} {s}')