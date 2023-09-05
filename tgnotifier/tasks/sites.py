from tgnotifier.utils.log import log
from .base import (
	with_db, with_default_exception_handler, with_clients, 
	send_messages_to_client_list
)
from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from tgnotifier.db.models import (
	db, Site, SiteLastPost, SiteUnseenPost,
)
from tgnotifier.utils.sites import (
	get_posts_by_stacks, get_title_by_url, clear_ads, filter_new_posts
	)

@with_default_exception_handler
@with_db
@with_clients
async def getNewPostsJob(clients):
	log("Retreiving new Posts.", error=False)
	for st in Site.select().iterator():
		new_posts = get_posts_by_stacks(st.url, st.stack)
		if st.same_domain:
			new_posts = clear_ads(st.url, new_posts)
		new_posts = [(p, get_title_by_url(p)) for p in new_posts]
		last_posts = [x.url for x in SiteLastPost.select(SiteLastPost.url).where(SiteLastPost.site==st).objects().iterator()]
		ft = bool(last_posts)
		messages = []
		new_posts, last_posts = filter_new_posts(last_posts, new_posts)
		with db.atomic() as trans:
			last_posts.reverse()
			SiteLastPost.delete().where(SiteLastPost.site==st.id).execute()
			SiteLastPost.insert_many([(st.id, p[0], p[1]) for p in last_posts],fields=[SiteLastPost.site, SiteLastPost.url, SiteLastPost.title]).execute()
			if ft:
				new_posts.reverse()
				for p in new_posts:
					up, created = SiteUnseenPost.get_or_create(site=st.id, url=p[0], title=p[1])
					if created:
						keyboard=InlineKeyboardMarkup(2)
						keyboard.add(InlineKeyboardButton('Seen', 
											callback_data=f"SEEN;{up.id}"),
							InlineKeyboardButton('x', callback_data="R"))
						messages.append((f"<a href='{p[0]}'>{p[1]}</a><b> - {st.name}</b>",
							keyboard))
		if messages:
			await send_messages_to_client_list(messages, list(clients), f'[{st.name}] post')

    