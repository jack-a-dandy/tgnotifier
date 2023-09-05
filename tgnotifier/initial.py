from .db.models import Client
from .core.settings import settings
#from peewee import OperationalError

def create_client():
	if settings.FIRST_CLIENT:
		Client.get_or_create(name=settings.FIRST_CLIENT)

def initialize_db():
	create_client()
