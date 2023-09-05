from tgnotifier.utils.log import log
from tgnotifier.db.models import (
	db, Channel, LastVideo, UnseenVideo,
	Term, IncludeTerm, ExcludeTerm,
	SearchQuery, QueryLastVideo, QueryUnseenVideo, moscowtz
)
from datetime import datetime
from tgnotifier.utils.youtube import getNewVideosFromPlaylist, getNewVideosFromSearchQuery
from .base import (
	with_db, with_default_exception_handler, with_clients, send_messages_to_client_list
)
from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup

@with_default_exception_handler
@with_db
@with_clients
async def getVideosFromChannelsJob(clients):
	log("Catching new videos from channels.", error=False)
	for ch in Channel.select().iterator():
		lastvideos = [i.value for i in LastVideo.select(LastVideo.value).where(LastVideo.channel==ch).iterator()]
		l = bool(lastvideos)
		incterms = [i.value for i in IncludeTerm.select(Term.value).join(Term).where(IncludeTerm.channel==ch).objects().iterator()]
		exterms = [i.value for i in ExcludeTerm.select(Term.value).join(Term).where(ExcludeTerm.channel==ch).objects().iterator()]
		lastvideos, videos = getNewVideosFromPlaylist(ch.list_id, lastvideos, incterms, exterms)
		messages = []
		with db.atomic() as trans:
			LastVideo.delete().where(LastVideo.channel==ch.id).execute()
			LastVideo.insert_many([(ch.id, v) for v in lastvideos],fields=[LastVideo.channel, LastVideo.value]).execute()
			if l:
				for v in videos:
					uv, created = UnseenVideo.get_or_create(value=v[1], channel=ch.id)
					if created:
						keyboard=InlineKeyboardMarkup(2)
						keyboard.add(InlineKeyboardButton('Seen', 
											callback_data=f"YSEEN;{uv.id}"),
							InlineKeyboardButton('x', callback_data="R"))
						messages.append((f"<b>[{ch.name}] </b><a href='https://youtube.com/watch?v={v[1]}'>{v[0]}</a>",
							keyboard))
		videos = messages
		if videos:
			await send_messages_to_client_list(videos, list(clients), f'[{ch.name}] channel video')


@with_default_exception_handler
@with_db
@with_clients
async def getVideosByQueryJob(clients):
	log("Catching new videos from queries.", error=False)
	for q in SearchQuery.select().iterator():
		lastvideos = [i.value for i in QueryLastVideo.select(QueryLastVideo.value)
				.where(QueryLastVideo.query==q)
				.order_by(QueryLastVideo.current_timestamp.desc()).iterator()]
		l = bool(lastvideos)
		lastvideos, videos = getNewVideosFromSearchQuery(q.value,lastvideos)
		messages = []
		with db.atomic() as trans:
			lastvideos.reverse()
			for v in lastvideos:
				lv, created = QueryLastVideo.get_or_create(query=q.id, value=v)
				if not created:
					lv.current_timestamp=datetime.now(tz=moscowtz)
					lv.save()
			if l:
				videos.reverse()
				for v in videos:
					uv, created = QueryUnseenVideo.get_or_create(value=v[0], query=q.id)
					if created:
						keyboard=InlineKeyboardMarkup(2)
						keyboard.add(InlineKeyboardButton('Seen', 
											callback_data=f"QSEEN;{uv.id}"),
							InlineKeyboardButton('x', callback_data="R"))
						messages.append((f"<b>({q.name}) </b><a href='https://youtube.com/watch?v={v[0]}'>{v[1]}</a>",
							keyboard))
			QueryLastVideo.delete().where(QueryLastVideo.id.in_(
				QueryLastVideo.select(QueryLastVideo.id).where(QueryLastVideo.query==q.id)
				.order_by(QueryLastVideo.current_timestamp.desc()).offset(20)
			))
		videos = messages
		if videos:
			await send_messages_to_client_list(videos, list(clients), f'({q.name}) query video')