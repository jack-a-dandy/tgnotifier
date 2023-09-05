from peewee import (Model, FloatField, CharField,
 ForeignKeyField, IntegerField, BooleanField, UUIDField, DateTimeField, TextField)
from .session import db
from passlib.hash import bcrypt
import uuid
from datetime import datetime
import pytz

moscowtz = pytz.timezone("Europe/Moscow")

class BaseModel(Model):
	class Meta:
		database=db
		order_by = []

	@classmethod
	def select(cls, *fields):
		order_by = []

		for field_name in cls._meta.order_by:
			if field_name.startswith('-'):
				order_by.append(getattr(cls, field_name[1:]).desc())
			else:
				order_by.append(getattr(cls, field_name))

		return super(BaseModel, cls).select(*fields).order_by(*order_by)


class Client(BaseModel):
	name = CharField(unique=True)
	chat_id = IntegerField(unique=True, null=True)

	class Meta:
		db_table = "clients"
		order_by = ['name']


class Term(BaseModel):
	value = CharField(unique=True)

	class Meta:
		db_table = "terms"
		order_by = ['value']

	def __str__(self):
		return self.value


class SearchQuery(BaseModel):
	name = CharField(unique=True)
	value = CharField(unique=True)

	class Meta:
		db_table = 'searchqueries'
		order_by = ['name']

class QueryLastVideo(BaseModel):
	id = UUIDField(primary_key=True, default=uuid.uuid4)
	value = CharField()
	query = ForeignKeyField(SearchQuery, backref="last", on_delete='CASCADE', on_update='CASCADE')
	current_timestamp = DateTimeField(index=True, default=lambda: datetime.now(tz=moscowtz))

	class Meta:
		db_table = "querylastvideos"
		indexes = (
			(("value", "query_id"), True),
		)
		order_by = ['-current_timestamp']


class QueryUnseenVideo(BaseModel):
	value = CharField()
	query = ForeignKeyField(SearchQuery, backref="unseen", on_delete='CASCADE', on_update='CASCADE')

	class Meta:
		db_table = "queryunseenvideos"
		indexes = (
			(("value", "query_id"), True),
		)
		order_by = ['-id']


class Site(BaseModel):
	name = CharField(unique=True)
	url = CharField(unique=True)
	stack = TextField()
	same_domain = BooleanField(default=True)

	class Meta:
		db_table = "sites"
		order_by = ['name']


class SiteLastPost(BaseModel):
	id = UUIDField(primary_key=True, default=uuid.uuid4)
	site = ForeignKeyField(Site, backref="last", on_delete='CASCADE', on_update='CASCADE')
	url = CharField()
	title = CharField(null=True)
	current_timestamp = DateTimeField(index=True, default=lambda: datetime.now(tz=moscowtz))

	class Meta:
		db_table = "sitelastposts"
		indexes = (
			(("site_id", "url"), True),
		)
		order_by = ['-current_timestamp']

class SiteUnseenPost(BaseModel):
	id = UUIDField(primary_key=True, default=uuid.uuid4)
	site = ForeignKeyField(Site, backref="unseen", on_delete='CASCADE', on_update='CASCADE')
	url = CharField()
	title = CharField(null=True)
	current_timestamp = DateTimeField(index=True, default=lambda: datetime.now(tz=moscowtz))

	class Meta:
		db_table = "siteunseenposts"
		indexes = (
			(("site_id", "url"), True),
		)
		order_by = ['-current_timestamp']

class Channel(BaseModel):
	name = CharField(unique=True)
	link = CharField(unique=True)
	list_id = CharField(unique=True)
	class Meta:
		db_table = "channels"
		order_by = ['name']

	def __str__(self):
		return self.name


class ExcludeTerm(BaseModel):
	channel = ForeignKeyField(Channel, backref="exclude", on_delete='CASCADE', on_update='CASCADE')
	term = ForeignKeyField(Term, backref="exclude", on_delete='CASCADE', on_update='CASCADE')
	class Meta:
		db_table = "excludeterms"
		indexes = (
		(("channel_id", "term_id"), True),
	)


class IncludeTerm(BaseModel):
	channel = ForeignKeyField(Channel, backref="include", on_delete='CASCADE', on_update='CASCADE')
	term = ForeignKeyField(Term, backref="include", on_delete='CASCADE', on_update='CASCADE')
	class Meta:
		db_table = "includeterms"
		indexes = (
		(("channel_id", "term_id"), True),
	)


class LastVideo(BaseModel):
	id = UUIDField(primary_key=True, default=uuid.uuid4)
	value = CharField(unique=True)
	channel = ForeignKeyField(Channel, backref="last", on_delete='CASCADE', on_update='CASCADE')

	class Meta:
		db_table = "lastvideos"

	def __str__(self):
		return self.value


class UnseenVideo(BaseModel):
	value = CharField(unique=True)
	channel = ForeignKeyField(Channel, backref="unseen", on_delete='CASCADE', on_update='CASCADE')
	
	class Meta:
		db_table = "unseenvideos"
		order_by = ['-id']

	def __str__(self):
		return self.value


MODELS = (Client,
		Term, LastVideo, UnseenVideo, Channel, ExcludeTerm, IncludeTerm, 
		SearchQuery, QueryLastVideo, QueryUnseenVideo,
		SiteLastPost, SiteUnseenPost, Site
	)
