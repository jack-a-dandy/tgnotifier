from tgnotifier.db.models import db, Channel, Term, IncludeTerm, ExcludeTerm, UnseenVideo
from tgnotifier.utils.youtube import ( 
	getUploadsIdByLink, getUploadsIdAndTitleByLink
)
from playhouse.shortcuts import model_to_dict

def create_channel_with_link(link, name=None):
	if name:
		return Channel.create(name=name, link=link[24:], list_id=getUploadsIdByLink(link))
	else:
		list_id, name = getUploadsIdAndTitleByLink(link)
		return Channel.create(name=name, link=link[24:], list_id=list_id)

def update_channel_with_link(o, link, with_name=False):
	if link != "https://www.youtube.com/"+o.link:
		if not with_name:
			o.list_id = getUploadsIdByLink(link)
		else:
			list_id, name = getUploadsIdAndTitleByLink(link)
			o.name = name
			o.list_id = list_id
		o.link = link[24:]
		o.save()

def update_channel(o, name='', link=None):
	if name == '':
		if link:
			update_channel_with_link(o, link)
	else:
		if name:
			o.name = name
			if link:
				update_channel_with_link(o, link)
			else:
				o.save()
		else:
			if link:
				update_channel_with_link(o, link, with_name=True)
	return o


def add_include_term(cid, value):
	return IncludeTerm.create(channel=cid, term=Term.get_or_create(value=value)[0].id)

def add_exclude_term(cid, value):
	return ExcludeTerm.create(channel=cid, term=Term.get_or_create(value=value)[0].id)

def get_include_terms(cid):
	return (IncludeTerm
		.select(IncludeTerm.id, Term.value)
		.join(Term, on=Term.id==IncludeTerm.term)
		.where(IncludeTerm.channel==cid)
		.order_by(Term.value))

def get_exclude_terms(cid):
	return (ExcludeTerm
		.select(ExcludeTerm.id, Term.value)
		.join(Term, on=Term.id==ExcludeTerm.term)
		.where(ExcludeTerm.channel==cid)
		.order_by(Term.value))

def get_channel_dict_with_backrefs(c):
	c = model_to_dict(c)
	c['link'] = "https://www.youtube.com/"+c['link']
	c['include'] = list(get_include_terms(c['id']).dicts())
	c['exclude'] = list(get_exclude_terms(c['id']).dicts())
	#c['unseen'] = list(UnseenVideo.select(UnseenVideo.id, UnseenVideo.value)
		#.where(UnseenVideo.channel==c['id']).dicts())
	return c

def get_channels_include(tid):
	return (IncludeTerm
		.select(IncludeTerm.id, Channel.name)
		.join(Channel, on=Channel.id==IncludeTerm.channel)
		.where(IncludeTerm.term==tid)
		.order_by(Channel.name))

def get_channels_exclude(tid):
	return (ExcludeTerm
		.select(ExcludeTerm.id, Channel.name)
		.join(Channel, on=Channel.id==ExcludeTerm.channel)
		.where(ExcludeTerm.term==tid)
		.order_by(Channel.name))

def get_term_dict_with_backrefs(t):
	t = model_to_dict(t)
	t['include'] = get_channels_include(t['id'].dicts())
	t['exclude'] = get_channels_exclude(t['id'].dicts())
	return t
