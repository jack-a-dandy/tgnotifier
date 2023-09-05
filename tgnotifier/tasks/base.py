from tgnotifier.api.v1.deps import reset_db_state
from tgnotifier.db.session import db
from tgnotifier.db.models import Client
from tgnotifier.utils.log import log
from tgnotifier.telegram.dispatcher import dispatcher
import time
import traceback

def with_db(f):
	async def wrapper(*args, **kwargs):
		await reset_db_state()
		try:
			db.connect()
			return await f(*args, **kwargs)
		finally:
			if not db.is_closed():
				db.close()
	return wrapper

def with_clients(f):
	async def wrapper(*args, **kwargs):
		kwargs['clients']=Client.select(Client.name, Client.chat_id).where(Client.chat_id!=None)
		return await f(*args, **kwargs)
	return wrapper

def with_default_exception_handler(f):
	async def wrapper(*args, **kwargs):
		try:
			return await f(*args, **kwargs)
		except Exception as e:
			log(str(e))
			traceback.print_exc()
	return wrapper

async def send_messages_to_client_list(messages, clients, mes_type='message', parse_mode='HTML'):
	for m in messages:
		for i in clients:
			for j in range(3):
				try:
					await dispatcher.bot.send_message(i.chat_id, 
										m[0], 
										parse_mode=parse_mode,
										reply_markup=m[1])
					break
				except Exception as e:
					log(f"Failed to send {mes_type} to {i.name}: {m[1]}:\n{e}")
					time.sleep(2)