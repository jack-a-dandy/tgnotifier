"""
Module with message handlers and FSM-schemas.
Example: https://github.com/aiogram/aiogram/blob/dev-2.x/examples/finite_state_machine_example.py
Documentation: https://aiogram.readthedocs.io/en/latest/dispatcher/fsm.html
NOTE: This module should be manually imported somewhere for being reachable.
In aiogram v3 it can be changed: https://t.me/aiogram_ru/167702
"""
from aiogram import types
from .dispatcher import dispatcher
from aiogram.dispatcher import FSMContext
from tgnotifier.db.models import (
	Client, Channel, LastVideo, UnseenVideo,
	SearchQuery, QueryLastVideo, QueryUnseenVideo,
	Site, SiteLastPost, SiteUnseenPost,
	Term, IncludeTerm, ExcludeTerm,
	db
)
from tgnotifier.crud.youtube import (
	create_channel_with_link,
	get_include_terms, get_exclude_terms
)
from tgnotifier.crud.base import select_with_count_of_backref
from tgnotifier.utils.log import log
from tgnotifier.utils.sites import (
	is_valid_url, make_stacks_by_posts, get_title_by_url, clear_ads
	)
import re
import urllib.parse
from peewee import JOIN, IntegrityError
from .commands import commands_dict

def with_client_check(f):
	async def wrapper(message: types.Message):
		user = Client.get_or_none(name=message.chat.username)
		if user:
			await f(message)
		else:
			await dispatcher.bot.send_message(
				message.chat.id, "Denied.")
	return wrapper

def with_client_check_and_get(f):
	async def wrapper(message: types.Message):
		user = Client.get_or_none(name=message.chat.username)
		if user:
			await f(message, user)
		else:
			await dispatcher.bot.send_message(
				message.chat.id, "Denied.")
	return wrapper

def with_client_check_and_state(f):
	async def wrapper(message: types.Message, state: FSMContext):
		user = Client.get_or_none(name=message.chat.username)
		if user:
			await f(message, state)
		else:
			await dispatcher.bot.send_message(
				message.chat.id, "Denied.")
	return wrapper

@dispatcher.message_handler(commands=['start'])
async def start_chat(message: types.Message) -> None:
	user = Client.get_or_none(name=message.chat.username)
	if user:
		if user.chat_id != message.chat.id:
			user.chat_id = message.chat.id
			user.save()
		await dispatcher.bot.send_message(
			message.chat.id, "Started.")
	else:
		await dispatcher.bot.send_message(
			message.chat.id, "Denied.")

def yes_no_markup(callback_data):
	return types.inline_keyboard.InlineKeyboardMarkup(2, 
		[[types.inline_keyboard.InlineKeyboardButton('Yes', callback_data=f'{callback_data}1'),
		types.inline_keyboard.InlineKeyboardButton('No', callback_data=f'{callback_data}0')]])

async def post_items_menu_paged(chat, select_query, title, call_name, page, 
	to_str=lambda o: o.name, parse_mode=None, with_page=False, message=None):
	items = []
	keyboard = types.inline_keyboard.InlineKeyboardMarkup(5)
	row = []
	offs = 10*(page-1) 
	for i, c in enumerate(select_query.offset(offs).limit(10).iterator(), start=offs+1):
		items.append(f'{i}. {to_str(c)}')
		row.append(types.inline_keyboard.InlineKeyboardButton(i, 
			callback_data=f"{call_name}{','+str(page) if with_page else ''};{c.id}"))
	keyboard.add(*row)
	row = []
	if page > 1:
		row.append(types.inline_keyboard.InlineKeyboardButton('<', callback_data=f"{call_name},{page-1}"))
	row.append(types.inline_keyboard.InlineKeyboardButton('x', callback_data="R"))
	if select_query.count() > offs+10:
		row.append(types.inline_keyboard.InlineKeyboardButton('>', callback_data=f"{call_name},{page+1}"))
	keyboard.row(*row)
	if message:
		await dispatcher.bot.edit_message_text(f"{title} - {page}\n"+'\n'.join(items), chat, message, 
			reply_markup=keyboard, 
			parse_mode=parse_mode, disable_web_page_preview=True)
	else:
		await dispatcher.bot.send_message(chat, f"{title} - {page}\n"+'\n'.join(items), 
			reply_markup=keyboard, 
			parse_mode=parse_mode, disable_web_page_preview=True)

async def post_items_list_paged(chat, select_query, title, call_name, page, to_str=lambda o: o.name, parse_mode=None, message=None):
	items = []
	offs = 10*(page-1) 
	for i, c in enumerate(select_query.offset(offs).limit(10).iterator(), start=offs+1):
		items.append(f'{i}. {to_str(c)}')
	nav = []
	if page > 1:
		nav.append(types.inline_keyboard.InlineKeyboardButton('<', callback_data=f"{call_name},{page-1}"))
	nav.append(types.inline_keyboard.InlineKeyboardButton('x', callback_data="R"))
	if select_query.count() > offs+10:
		nav.append(types.inline_keyboard.InlineKeyboardButton('>', callback_data=f"{call_name},{page+1}"))
	if message:
		await dispatcher.bot.edit_message_text(f"{title} - {page}\n"+'\n'.join(items), chat, message, 
			reply_markup=types.inline_keyboard.InlineKeyboardMarkup(3,[nav]), 
			parse_mode=parse_mode, disable_web_page_preview=True)
	else:
		await dispatcher.bot.send_message(
			chat, f"{title} - {page}\n"+'\n'.join(items), 
			reply_markup=types.inline_keyboard.InlineKeyboardMarkup(3,[nav]), 
			parse_mode=parse_mode, disable_web_page_preview=True)

async def post_items_menu(chat, select_query, title, call_name, to_str=lambda o: o.name, parse_mode=None, message=None):
	items = []
	keyboard = types.inline_keyboard.InlineKeyboardMarkup(5)
	row = [] 
	for i, c in enumerate(select_query.iterator(), start=1):
		items.append(f'{i}. {to_str(c)}')
		row.append(types.inline_keyboard.InlineKeyboardButton(i, callback_data=f"{call_name}.{c.id}"))
	keyboard.add(*row)
	keyboard.row(types.inline_keyboard.InlineKeyboardButton('x', callback_data="R"))
	if message:
		await dispatcher.bot.edit_message_text(f"{title}\n"+'\n'.join(items), chat, message, 
			reply_markup=keyboard, 
			parse_mode=parse_mode, disable_web_page_preview=True)
	else:
		await dispatcher.bot.send_message(
			chat, f"{title}\n"+'\n'.join(items), 
			reply_markup=keyboard, 
			parse_mode=parse_mode, disable_web_page_preview=True)

async def post_items_list(chat, select_query, title, to_str=lambda o: o.name, parse_mode=None):
	items = []
	for i, c in enumerate(select_query.iterator(), start=1):
		items.append(f'{i}. {to_str(c)}')
	nav = [types.inline_keyboard.InlineKeyboardButton('x', callback_data="R")]
	await dispatcher.bot.send_message(
			chat, f"{title}\n"+'\n'.join(items), 
			reply_markup=types.inline_keyboard.InlineKeyboardMarkup(1,[nav]), 
			parse_mode=parse_mode, disable_web_page_preview=True)

@dispatcher.callback_query_handler(lambda callback_query: callback_query.data=='R', state='*')
async def remove_message(callback_query: types.callback_query.CallbackQuery) -> None:
	await dispatcher.bot.delete_message(callback_query.message.chat.id, 
		callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.message_handler(state='*', commands=['cancel'])
async def cancel_handler(message: types.Message, state: FSMContext):

	current_state = await state.get_state()
	if current_state is None:
		return
		 
	await state.finish()

	await dispatcher.bot.send_message(message.chat.id, 'Cancelled.', 
		reply_markup=types.ReplyKeyboardRemove())

@dispatcher.message_handler(commands=['add_client'])
@with_client_check_and_state
async def add_client_request(message: types.Message, state: FSMContext) -> None:
	await state.set_state('adding_client')
	await dispatcher.bot.send_message(message.chat.id, 'Input the nickname:')

@dispatcher.message_handler(state='adding_client')
async def add_client(message: types.Message, state: FSMContext) -> None:
	try:
		user = Client.get_or_none(name=message.text)
		if user:
			await dispatcher.bot.send_message(message.chat.id, "Client has already been added.")
		else:
			Client.insert(name=message.text).execute()
			await dispatcher.bot.send_message(message.chat.id, f'Client added.')
	except Exception as e:
		await dispatcher.bot.send_message(message.chat.id, str(e))
	finally:
		await state.finish()

@dispatcher.message_handler(commands=['remove_client'])
@with_client_check
async def get_clients_list_for_removing(message: types.Message) -> None:
	await post_items_menu(message.chat.id, Client.select(Client.id, Client.name), 
		'Clients', 'RCL', to_str=lambda o: f'@{o.name}')

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RCL\.\d+$',callback_query.data))
async def remove_client(callback_query: types.callback_query.CallbackQuery) -> None:
	cid = int(callback_query.data.split(".")[1])
	await dispatcher.bot.answer_callback_query(callback_query.id)
	try:
		if Client.select(Client.id).count() > 1:
			user = Client.get(id=cid)
			user.delete_instance()
			await post_items_menu(callback_query.message.chat.id, Client.select(Client.id, Client.name), 
				'Clients', 'RCL', to_str=lambda o: f'@{o.name}', message=callback_query.message.message_id)
		else:
			dispatcher.bot.send_message(callback_query.message.chat.id, "Unable to remove last available client. Add another one.")
	except Exception as e:
		await dispatcher.bot.send_message(callback_query.message.chat.id, str(e))

@dispatcher.message_handler(commands=['help'], state='*')
async def help_command(message: types.Message) -> None:
    await dispatcher.bot.send_message(message.chat.id,
        "Instructions:\n \
        1. Use '/cancel' command to cancel any current input and command dialog.\n \
        2. If layouts of site's posts are different input multiple links when adding site.\n  \
        \nCommands:\n" +
    	"\n".join([f"/{x} - {y}" for x,y in commands_dict.items()]),
    	reply_markup=types.inline_keyboard.InlineKeyboardMarkup(1, [[
    		types.inline_keyboard.InlineKeyboardButton('x', callback_data='R')]]))

# Channels

#Last videos

@dispatcher.message_handler(commands=['ylast'])
@with_client_check
async def get_channels_list_for_lastvideos(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, Channel.select(Channel.id, Channel.name), 
		'Last videos', 'YLAST', 1)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^YLAST;\d+$',callback_query.data))
async def get_lastvideos_of_channel(callback_query: types.callback_query.CallbackQuery) -> None:
	cid = int(callback_query.data.split(";")[1])
	for v in LastVideo.select(LastVideo.value).where(LastVideo.channel==cid).iterator():
		await dispatcher.bot.send_message(callback_query.message.chat.id, "https://youtube.com/watch?v="+v.value)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^YLAST,\d+$',callback_query.data), state='*')
async def get_channels_list_for_lastvideos_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, Channel.select(Channel.id, Channel.name),
			'Last videos', 'YLAST', page, message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)


#Unseen videos

@dispatcher.message_handler(commands=['yunseen'])
@with_client_check
async def get_channels_list_for_unseen(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, select_with_count_of_backref(Channel, UnseenVideo), 
		'Unseen videos', 'YUNSEEN', 1,
		to_str=lambda o: f'{o.name} ({o.count})')

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^YUNSEEN,\d+$',callback_query.data), state='*')
async def get_channels_list_for_unseen_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, select_with_count_of_backref(Channel, UnseenVideo),
			'Unseen videos', 'YUNSEEN', page,
			to_str=lambda o: f'{o.name} ({o.count})',
			message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^YUNSEEN;\d+$',callback_query.data))
async def get_unseenvideos_of_channel(callback_query: types.callback_query.CallbackQuery) -> None:
	cid = int(callback_query.data.split(";")[1])
	await dispatcher.bot.answer_callback_query(callback_query.id)
	for v in UnseenVideo.select(UnseenVideo.id, UnseenVideo.value).where(UnseenVideo.channel==cid).order_by(UnseenVideo.id.asc()).iterator():
		keyboard=types.inline_keyboard.InlineKeyboardMarkup(2)
		keyboard.add(types.inline_keyboard.InlineKeyboardButton('Seen', 
											callback_data=f"YSEEN;{v.id}"),
			types.inline_keyboard.InlineKeyboardButton('x', callback_data="R"))
		await dispatcher.bot.send_message(callback_query.message.chat.id, 
			"https://youtube.com/watch?v="+v.value,
			reply_markup=keyboard)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^YSEEN;\d+$',callback_query.data), state='*')
async def remove_seen_video(callback_query: types.callback_query.CallbackQuery) -> None:
	vid = int(callback_query.data.split(";")[1])
	UnseenVideo.delete().where(UnseenVideo.id==vid).execute()
	await dispatcher.bot.delete_message(callback_query.message.chat.id, 
		callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.message_handler(commands=['clear_unseen_videos'])
@with_client_check
async def clear_unseen_videos_command(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, 
		select_with_count_of_backref(Channel, UnseenVideo), 
		"Clear unseen channel's videos", 'CCU', 1,
		to_str=lambda o: f'{o.name} ({o.count})',
		with_page=True)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^CCU,\d+$',callback_query.data), state='*')
async def clear_unseen_videos_callback(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, 
			select_with_count_of_backref(Channel, UnseenVideo),
			"Clear unseen channel's videos", 'CCU', page,
			to_str=lambda o: f'{o.name} ({o.count})',
			message=callback_query.message.message_id,
			with_page=True)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^CCU,\d+;\d+$',callback_query.data), state='*')
async def clear_unseen_videos(callback_query: types.callback_query.CallbackQuery) -> None:
	page, chid = callback_query.data.split(";")
	page = int(page.split(',')[1])
	chid = int(chid)
	if page > 0:
		UnseenVideo.delete().where(UnseenVideo.channel==chid).execute()
		await post_items_menu_paged(callback_query.message.chat.id, 
			select_with_count_of_backref(Channel, UnseenVideo),
			"Clear unseen channel's videos", 'CCU', page,
			to_str=lambda o: f'{o.name} ({o.count})',
			message=callback_query.message.message_id,
			with_page=True)
	await dispatcher.bot.answer_callback_query(callback_query.id)


#Add channel

@dispatcher.message_handler(commands=['add_channel'])
@with_client_check_and_state
async def add_channel_command(message: types.Message, state: FSMContext) -> None:
	await state.set_state('channel_url_input')
	await dispatcher.bot.send_message(message.chat.id, "Input channel's url:")

@dispatcher.message_handler(state='channel_url_input')
async def addchannel(message: types.Message, state: FSMContext) -> None:
	try:
		if re.match(r'^https://www.youtube.com/@?(channel|user)?/?[-_a-zA-Z0-9]+/?$', message.text):
		    ch = create_channel_with_link(message.text.rstrip("/"))
		    await state.finish()
		    await dispatcher.bot.send_message(message.chat.id, f"{ch.name} added.")
		else:
			await dispatcher.bot.send_message(message.chat.id, "Invalid channel's url. Input again.")
	except IntegrityError:
		await dispatcher.bot.send_message(message.chat.id, 'Channel already added.')
		await state.finish()
	except Exception as e:
		se = str(e)
		if se == "'items'":
			await dispatcher.bot.send_message(message.chat.id, "Cannot get channel's data from API.")
		else:
		    await dispatcher.bot.send_message(message.chat.id, se)


#Remove channel

@dispatcher.message_handler(commands=['remove_channel'])
@with_client_check
async def remove_channel_command(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, Channel.select(Channel.id, Channel.name, Channel.link), 
		'Remove Channel', 'RMCH', 1, to_str=lambda o: f'<a href="https://www.youtube.com/{o.link}">{o.name}</a>',
		parse_mode='HTML', with_page=True)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RMCH,\d+$',callback_query.data), state='*')
async def get_channels_list_for_removing(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id,
		    Channel.select(Channel.id, Channel.name, Channel.link), 
			'Remove Channel', 'RMCH', page,
			to_str=lambda o: f'<a href="https://www.youtube.com/{o.link}">{o.name}</a>',
			message=callback_query.message.message_id, parse_mode='HTML',
			with_page=True)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RMCH,\d+;\d+$',callback_query.data), state='*')
async def remove_channel(callback_query: types.callback_query.CallbackQuery) -> None:
	page, chid = callback_query.data.split(";")
	page = int(page.split(',')[1])
	chid = int(chid)
	await dispatcher.bot.answer_callback_query(callback_query.id)
	try:
		ch = Channel.get(id=chid)
		ch.delete_instance()
		await post_items_menu_paged(callback_query.message.chat.id, 
			  Channel.select(Channel.id, Channel.name, Channel.link), 
			'Remove Channel', 'RMCH', page,
			to_str=lambda o: f'<a href="https://www.youtube.com/{o.link}">{o.name}</a>',
			message=callback_query.message.message_id, parse_mode='HTML',
			with_page=True)
	except Exception as e:
		await dispatcher.bot.send_message(callback_query.message.chat.id, str(e))


#Channel terms list

@dispatcher.message_handler(commands=['chterms'])
@with_client_check
async def get_channels_list_for_terms(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, Channel.select(Channel.id, Channel.name), 
		'Channel terms', 'CHTERMS', 1)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^CHTERMS,\d+$',callback_query.data), state='*')
async def get_channels_list_for_terms_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, Channel.select(Channel.id, Channel.name),
			'Channel terms', 'CHTERMS', page, message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^CHTERMS;\d+$',callback_query.data))
async def post_terms_of_channel(callback_query: types.callback_query.CallbackQuery) -> None:
	cid = int(callback_query.data.split(";")[1])
	await dispatcher.bot.send_message(callback_query.message.chat.id, 
		f"""Include: {'; '.join([x.term.value for x in get_include_terms(cid).iterator()])}
		Exclude: {'; '.join([x.term.value for x in get_exclude_terms(cid).iterator()])}""")
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.message_handler(commands=['channels'])
@with_client_check
async def get_channels_list(message: types.Message) -> None:
	await post_items_list_paged(message.chat.id, Channel.select(Channel.id, Channel.name, Channel.link), 
		'Channels', 'CHL', 1, to_str=lambda o: f'<a href="https://www.youtube.com/{o.link}">{o.name}</a>',
		parse_mode='HTML')

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^CHL,\d+$',callback_query.data), state='*')
async def get_channels_list_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_list_paged(callback_query.message.chat.id, Channel.select(Channel.id, Channel.name, Channel.link), 
		'Channels', 'CHL', page, to_str=lambda o: f'<a href="https://www.youtube.com/{o.link}">{o.name}</a>',
		parse_mode='HTML',
		message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)


#Add channel term

@dispatcher.message_handler(commands=['ait'])
@with_client_check
async def get_channels_list_for_adding_include_term(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, Channel.select(Channel.id, Channel.name), 
		'Add include', 'AIT', 1)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^AIT,\d+$',callback_query.data))
async def get_channels_list_for_adding_include_term_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, Channel.select(Channel.id, Channel.name), 
			'Add include', 'AIT', page, message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^AIT;\d+$',callback_query.data))
async def ask_include_term_for_channel(callback_query: types.callback_query.CallbackQuery, state: FSMContext) -> None:
	cid = int(callback_query.data.split(";")[1])
	await state.set_state('include_term')
	await state.set_data({'cid':cid})
	await dispatcher.bot.answer_callback_query(callback_query.id)
	await dispatcher.bot.send_message(callback_query.message.chat.id, 
		'Input include term:')

@dispatcher.message_handler(state='include_term')
async def add_include_term_to_channel(message: types.Message, state: FSMContext) -> None:
	try:
		cid = (await state.get_data())['cid']
		ch = Channel.get(id=cid)
		term, _ = Term.get_or_create(value=message.text)
		IncludeTerm.insert(term=term.id, channel=cid).execute()
		await dispatcher.bot.send_message(message.chat.id, f'Term added to {ch.name}.')
	except IntegrityError:
		await dispatcher.bot.send_message(message.chat.id, 'Error. This term already exists.')
	except Exception as e:
		await dispatcher.bot.send_message(message.chat.id, str(e))
	finally:
		await state.finish()

@dispatcher.message_handler(commands=['rit'])
@with_client_check
async def get_channels_list_for_removing_include_term(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, select_with_count_of_backref(Channel, IncludeTerm), 
		'Remove include', 'RIT', 1,
		to_str=lambda o: f'{o.name} ({o.count})')

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RIT,\d+$',callback_query.data))
async def get_channels_list_for_removing_include_term_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, select_with_count_of_backref(Channel, IncludeTerm), 
			'Remove include', 'RIT', page,
			to_str=lambda o: f'{o.name} ({o.count})',
			message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RIT;\d+$',callback_query.data))
async def get_include_term_list_for_remove(callback_query: types.callback_query.CallbackQuery) -> None:
	cid = int(callback_query.data.split(";")[1])
	await dispatcher.bot.answer_callback_query(callback_query.id)
	try:
		ch = Channel.get(id=cid)
		await post_items_menu(callback_query.message.chat.id, 
			  get_include_terms(cid), 
			f'Remove include for {ch.name}', 'RIT',
			to_str=lambda o: o.term.value)
	except Exception as e:
		await dispatcher.bot.send_message(callback_query.message.chat.id, str(e))
		

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RIT\.\d+$',callback_query.data))
async def remove_include_term(callback_query: types.callback_query.CallbackQuery) -> None:
	tid = int(callback_query.data.split(".")[1])
	await dispatcher.bot.answer_callback_query(callback_query.id)
	try:
		with db.atomic():
			term = IncludeTerm.get(id=tid)
			tv = term.term
			ch = Channel.get(id=term.channel)
			term.delete_instance()
			if ExcludeTerm.select().where(ExcludeTerm.term==tv).count() == 0 and \
			   IncludeTerm.select().where(IncludeTerm.term==tv).count() == 0:
			   Term.delete().where(Term.id==tv).execute()
			await post_items_menu(callback_query.message.chat.id, 
				  get_include_terms(ch.id), 
				f'Remove include for {ch.name}', 'RIT',
				to_str=lambda o: o.term.value,
				message=callback_query.message.message_id)
	except Exception as e:
		await dispatcher.bot.send_message(callback_query.message.chat.id, str(e))




@dispatcher.message_handler(commands=['aet'])
@with_client_check
async def get_channels_list_for_adding_exclude_term(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, Channel.select(Channel.id, Channel.name), 
		'Add exclude', 'AET', 1)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^AET,\d+$',callback_query.data))
async def get_channels_list_for_adding_exclude_term_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, Channel.select(Channel.id, Channel.name), 
			'Add exclude', 'AET', page, message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^AET;\d+$',callback_query.data))
async def ask_exclude_term_for_channel(callback_query: types.callback_query.CallbackQuery, state: FSMContext) -> None:
	cid = int(callback_query.data.split(";")[1])
	await state.set_state('exclude_term')
	await state.set_data({'cid':cid})
	await dispatcher.bot.answer_callback_query(callback_query.id)
	await dispatcher.bot.send_message(callback_query.message.chat.id, 
		'Input exclude term:')

@dispatcher.message_handler(state='exclude_term')
async def add_exclude_term_to_channel(message: types.Message, state: FSMContext) -> None:
	try:
		cid = (await state.get_data())['cid']
		ch = Channel.get(id=cid)
		term, _ = Term.get_or_create(value=message.text)
		ExcludeTerm.insert(term=term.id, channel=cid).execute()
		await dispatcher.bot.send_message(message.chat.id, f'Term added to {ch.name}.')
	except IntegrityError:
		await dispatcher.bot.send_message(message.chat.id, 'Error. This term already exists.')
	except Exception as e:
		await dispatcher.bot.send_message(message.chat.id, str(e))
	finally:
		await state.finish()

@dispatcher.message_handler(commands=['ret'])
@with_client_check
async def get_channels_list_for_removing_exclude_term(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, select_with_count_of_backref(Channel, ExcludeTerm), 
		'Remove exclude', 'RET', 1,
		to_str=lambda o: f'{o.name} ({o.count})')

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RET,\d+$',callback_query.data))
async def get_channels_list_for_removing_exclude_term_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, select_with_count_of_backref(Channel, ExcludeTerm), 
			'Remove exclude', 'RET', page,
			to_str=lambda o: f'{o.name} ({o.count})',
			message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RET;\d+$',callback_query.data))
async def get_exclude_term_list_for_remove(callback_query: types.callback_query.CallbackQuery) -> None:
	cid = int(callback_query.data.split(";")[1])
	await dispatcher.bot.answer_callback_query(callback_query.id)
	try:
		ch = Channel.get(id=cid)
		await post_items_menu(callback_query.message.chat.id, 
			  get_exclude_terms(cid), 
			f'Remove exclude for {ch.name}', 'RET',
			to_str=lambda o: o.term.value)
	except Exception as e:
		await dispatcher.bot.send_message(callback_query.message.chat.id, str(e))
		

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RET\.\d+$',callback_query.data))
async def remove_exclude_term(callback_query: types.callback_query.CallbackQuery) -> None:
	tid = int(callback_query.data.split(".")[1])
	await dispatcher.bot.answer_callback_query(callback_query.id)
	try:
		with db.atomic():
			term = ExcludeTerm.get(id=tid)
			tv = term.term
			ch = Channel.get(id=term.channel)
			term.delete_instance()
			if ExcludeTerm.select().where(ExcludeTerm.term==tv).count() == 0 and \
			   IncludeTerm.select().where(IncludeTerm.term==tv).count() == 0:
			   Term.delete().where(Term.id==tv).execute()
			await post_items_menu(callback_query.message.chat.id, 
				  get_exclude_terms(ch.id), 
				f'Remove exclude for {ch.name}', 'RET',
				to_str=lambda o: o.term.value,
				message=callback_query.message.message_id)
	except Exception as e:
		await dispatcher.bot.send_message(callback_query.message.chat.id, str(e))





# Sites

@dispatcher.message_handler(commands=['last'])
@with_client_check
async def get_sites_list_for_last(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, Site.select(Site.id, Site.name, Site.url), 
		'Last site posts', 'LAST', 1, to_str=lambda o: f'<a href="{o.url}">{o.name}</a>',
		parse_mode='HTML')

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^LAST,\d+$',callback_query.data), state='*')
async def get_sites_list_for_last_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, Site.select(Site.id, Site.name, Site.url),
			'Last site posts', 'LAST', page, message=callback_query.message.message_id,
			to_str=lambda o: f'<a href="{o.url}">{o.name}</a>',
		parse_mode='HTML')
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^LAST;\d+$',callback_query.data), state='*')
async def get_lastposts_of_site(callback_query: types.callback_query.CallbackQuery) -> None:
	sid = int(callback_query.data.split(";")[1])
	so = Site.select(Site.url, Site.name).where(Site.id == sid).first()
	if so:
	#for s in SiteLastPost.select(SiteLastPost.url, SiteLastPost.title).where(SiteLastPost.site==sid).order_by(SiteLastPost.current_timestamp.asc()).iterator():
	#	if s.title: 
	#		await dispatcher.bot.send_message(callback_query.message.chat.id, 
	#			f'<a href="{prefix}/{s.url}">{s.title}</a>', 
	#			parse_mode="HTML")
	#	else:
	#		await dispatcher.bot.send_message(callback_query.message.chat.id, 
	#			f'<a href="{prefix}/{s.url}">{prefix}/{s.url}</a>')
	    await dispatcher.bot.send_message(callback_query.message.chat.id, 
		    f'{so.name}\n' + 
		    "\n".join([f'{i}. <a href="{p.url}">{p.title if p.title else p.url}</a>'
		    	for i, p in enumerate(SiteLastPost.select(SiteLastPost.url, SiteLastPost.title).where(SiteLastPost.site==sid).order_by(SiteLastPost.current_timestamp.asc()).iterator(), start=1)]),
		    parse_mode="HTML",
		    disable_web_page_preview=True,
		    reply_markup=types.inline_keyboard.InlineKeyboardMarkup(1, 
			    [[types.inline_keyboard.InlineKeyboardButton('x', callback_data="R")]]))
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.message_handler(commands=['unseen'])
@with_client_check
async def get_sites_list_for_unseen(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, 
		select_with_count_of_backref(Site, SiteUnseenPost, fields=[Site.id, Site.url, Site.name]), 
		'Unseen site posts', 'UNSEEN', 1,
		to_str=lambda o: f'<a href="{o.url}">{o.name}</a> ({o.count})',
		parse_mode="HTML")

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^UNSEEN,\d+$',callback_query.data), state='*')
async def get_sites_list_for_unseen_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, 
			select_with_count_of_backref(Site, SiteUnseenPost, fields=[Site.id, Site.url, Site.name]),
			'Unseen site posts', 'UNSEEN', page,
			to_str=lambda o: f'<a href="{o.url}">{o.name}</a> ({o.count})',
			parse_mode="HTML",
			message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^UNSEEN;\d+$',callback_query.data), state='*')
async def get_unseenposts_of_site(callback_query: types.callback_query.CallbackQuery) -> None:
	sid = int(callback_query.data.split(";")[1])
	await dispatcher.bot.answer_callback_query(callback_query.id)
	for s in SiteUnseenPost.select(SiteUnseenPost.id, SiteUnseenPost.url, SiteUnseenPost.title).where(SiteUnseenPost.site==sid).order_by(SiteUnseenPost.id.asc()).iterator():
		keyboard=types.inline_keyboard.InlineKeyboardMarkup(2)
		keyboard.add(types.inline_keyboard.InlineKeyboardButton('Seen', 
											callback_data=f"SEEN;{s.id}"),
			types.inline_keyboard.InlineKeyboardButton('x', callback_data="R"))
		await dispatcher.bot.send_message(callback_query.message.chat.id, 
			f'<a href="{s.url}">{s.title}</a>', parse_mode="HTML", 
			reply_markup=keyboard)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^SEEN;',callback_query.data), state='*')
async def remove_seen_post(callback_query: types.callback_query.CallbackQuery) -> None:
	pid = callback_query.data.split(";")[1]
	SiteUnseenPost.delete().where(SiteUnseenPost.id==pid).execute()
	await dispatcher.bot.delete_message(callback_query.message.chat.id, 
		callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.message_handler(commands=['sites'])
@with_client_check
async def get_sites_list(message: types.Message) -> None:
	await post_items_list_paged(message.chat.id, Site.select(Site.id, Site.name, Site.url), 
		'Sites', 'SL', 1, to_str=lambda o: f'<a href="{o.url}">{o.name}</a>',
		parse_mode='HTML')

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^SL,\d+$',callback_query.data), state='*')
async def get_sites_list_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_list_paged(callback_query.message.chat.id, Site.select(Site.id, Site.name, Site.url), 
		'Sites', 'SL', page, to_str=lambda o: f'<a href="{o.url}">{o.name}</a>',
		parse_mode='HTML',
		message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.message_handler(commands=['clear_unseen_posts'])
@with_client_check
async def clear_unseen_posts_command(message: types.Message) -> None:
    await post_items_menu_paged(message.chat.id, 
    	select_with_count_of_backref(Site, SiteUnseenPost, fields=[Site.id, Site.url, Site.name]), 
		'Clear all unseen posts for site', 'CSU', 1, 
		to_str=lambda o: f'<a href="{o.url}">{o.name}</a> ({o.count})',
		with_page=True,
		parse_mode='HTML')

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^CSU,\d+$',callback_query.data), state='*')
async def clear_unseen_posts_callback(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, 
			select_with_count_of_backref(Site, SiteUnseenPost, fields=[Site.id, Site.url, Site.name]),
			'Clear all unseen posts for site', 'CSU', page, 
			message=callback_query.message.message_id,
			to_str=lambda o: f'<a href="{o.url}">{o.name}</a> ({o.count})',
			with_page=True,
		parse_mode='HTML')
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^CSU,\d+;\d+$',callback_query.data), state='*')
async def clear_unseen_posts(callback_query: types.callback_query.CallbackQuery) -> None:
	pid, sid = callback_query.data.split(";")
	pid = int(pid.split(',')[1])
	sid = int(sid)
	SiteUnseenPost.delete().where(SiteUnseenPost.site==sid).execute()
	await post_items_menu_paged(callback_query.message.chat.id, 
		select_with_count_of_backref(Site, SiteUnseenPost, fields=[Site.id, Site.url, Site.name]),
			'Clear all unseen posts for site', 'CSU', pid, 
			message=callback_query.message.message_id,
			to_str=lambda o: f'<a href="{o.url}">{o.name}</a> ({o.count})',
			with_page=True,
		parse_mode='HTML')
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.message_handler(commands=['add_site'])
@with_client_check_and_state
async def add_site_command(message: types.Message, state: FSMContext) -> None:
	await state.set_state('site_url_input')
	await dispatcher.bot.send_message(message.chat.id, "Input site's url:")

@dispatcher.callback_query_handler(lambda callback_query: callback_query.data=='SSDI1', state='site_post_input')
async def set_site_same_domain(callback_query: types.callback_query.CallbackQuery, state: FSMContext) -> None:
	try:
		await dispatcher.bot.delete_message(callback_query.message.chat.id, 
		    callback_query.message.message_id)
		await dispatcher.bot.send_message(callback_query.message.chat.id,
			'Preparing results. Please wait.'
			)
		await state.update_data(same_domain=True)
		s = (await state.get_data())
		results, scraper = make_stacks_by_posts(s['url'], s['posts'])
		if not results:
			await state.finish()
			await dispatcher.bot.send_message(callback_query.message.chat.id, 
				"Error. Results not found.")
		else:
			results = clear_ads(s['url'], results)
			results = [(p, get_title_by_url(p)) for p in results]
			await state.update_data(stacks=scraper.dumpToStr(), posts=results)
			await dispatcher.bot.send_message(callback_query.message.chat.id, 
			'Here your results. Choose "Yes" to add this parser or "No" to cancel operation.\n\n' + 
			"\n".join([f'{i}. <a href="{x[0]}">{x[1] if x[1] else x[0]}</a>' for i, x in enumerate(results, start=1)]),
			reply_markup=yes_no_markup('SSS'),
			parse_mode="HTML",
			disable_web_page_preview=True)
	except Exception as e:
		await dispatcher.bot.send_message(callback_query.message.chat.id, str(e))
	finally:
		await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: callback_query.data=='SSDI0', state='site_post_input')
async def set_site_not_same_domain(callback_query: types.callback_query.CallbackQuery, state: FSMContext) -> None:
	try:
		await dispatcher.bot.delete_message(callback_query.message.chat.id, 
		    callback_query.message.message_id)
		await dispatcher.bot.send_message(callback_query.message.chat.id,
			'Preparing results. Please wait.'
			)
		await state.update_data(same_domain=False)
		s = (await state.get_data())
		results, scraper = make_stacks_by_posts(s['url'], s['posts'])
		if not results:
			await state.finish()
			await dispatcher.bot.send_message(callback_query.message.chat.id, 
				"Error. Results not found.")
		else:
			results = [(p, get_title_by_url(p)) for p in results]
			await state.update_data(stacks=scraper.dumpToStr(), posts=results)
			await dispatcher.bot.send_message(callback_query.message.chat.id, 
			'Here your results. Choose "Yes" to add this parser or "No" to cancel operation.\n\n' + 
			"\n".join([f'{i}. <a href="{x[0]}">{x[1] if x[1] else x[0]}</a>' for i, x in enumerate(results, start=1)]),
			reply_markup=yes_no_markup('SSS'),
			parse_mode="HTML",
			disable_web_page_preview=True)
	except Exception as e:
		await dispatcher.bot.send_message(callback_query.message.chat.id, str(e))
	finally:
		await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: callback_query.data=='SSS0',state='site_post_input')
async def cancel_site_addition(callback_query: types.callback_query.CallbackQuery, state: FSMContext) -> None:
	try:
		await dispatcher.bot.delete_message(callback_query.message.chat.id, 
		    callback_query.message.message_id)
		await state.finish()
		await dispatcher.bot.send_message(callback_query.message.chat.id, "Cancelled.")
	except Exception as e:
	    await dispatcher.bot.send_message(callback_query.message.chat.id, str(e))
	finally:
		await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: callback_query.data=='SSS1', state='site_post_input')
async def write_site_name_prompt(callback_query: types.callback_query.CallbackQuery, state: FSMContext) -> None:
	try:
		await dispatcher.bot.delete_message(callback_query.message.chat.id, 
		    callback_query.message.message_id)
		await state.set_state('site_name_input')
		await dispatcher.bot.send_message(callback_query.message.chat.id, "Input site's short name:")
	except Exception as e:
	    await dispatcher.bot.send_message(callback_query.message.chat.id, str(e))
	finally:
		await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.message_handler(state='site_url_input')
async def site_name_input_handler(message: types.Message, state: FSMContext) -> None:
	try:
		if is_valid_url(message.text):
			if Site.select().where(Site.url==message.text).exists():
				await dispatcher.bot.send_message(message.chat.id, "This site already exists. Input another or /cancel:")
			else:
				await state.set_state('site_post_input')
				await state.update_data(url=message.text)
				await dispatcher.bot.send_message(message.chat.id, "Input post's link(s):")
		else:
			await dispatcher.bot.send_message(message.chat.id, "Invalid url. Input again:")
	except Exception as e:
		await dispatcher.bot.send_message(message.chat.id, str(e))

@dispatcher.message_handler(state='site_post_input')
async def site_post_input_handler(message: types.Message, state: FSMContext) -> None:
	try:
		links = message.text.strip('\n').split('\n')
		all_valid = True
		for l in links:
			if not is_valid_url(l):
				all_valid = False
				break
		if not all_valid:
		    await dispatcher.bot.send_message(message.chat.id, "Invalid urls. Input again:")
		else:
			await state.update_data(posts=links)
			await dispatcher.bot.send_message(message.chat.id, "Filter links to other domains?",
				reply_markup=yes_no_markup('SSDI'))
	except Exception as e:
		await dispatcher.bot.send_message(message.chat.id, str(e))

@dispatcher.message_handler(state='site_name_input')
async def site_input_name_handler(message: types.Message, state: FSMContext) -> None:
	try:
		name = message.text.strip()
		if not name.strip():
			await dispatcher.bot.send_message(message.chat.id, "Input valid site's name:")
		else:
			st = (await state.get_data())
			s = Site.create(url=st['url'], stack=st['stacks'], 
				name=name, same_domain=st['same_domain'])
			st['posts'].reverse()
			SiteLastPost.insert_many([(s.id, p[0], p[1]) for p in st['posts']],fields=[SiteLastPost.site, SiteLastPost.url, SiteLastPost.title]).execute()
			await state.finish()
			await dispatcher.bot.send_message(message.chat.id, 
					f'Parser for site <a href="{s.url}">{s.name}</a> added.',
			        parse_mode="HTML",
			        disable_web_page_preview=True)
	except IntegrityError:
		await dispatcher.bot.send_message(message.chat.id, 
					"Site with this name already exists. Input again or print '/cancel' to cancel:")
	except Exception as e:
		await dispatcher.bot.send_message(message.chat.id, str(e))

@dispatcher.message_handler(commands=['remove_site'])
@with_client_check
async def remove_site_command(message: types.Message):
	await post_items_menu_paged(message.chat.id, Site.select(Site.id, Site.name, Site.url), 
		'Remove site', 'RS', 1, to_str=lambda o: f'<a href="{o.url}">{o.name}</a>',
		parse_mode='HTML', with_page=True)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RS,\d+$',callback_query.data), state='*')
async def remove_site_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, Site.select(Site.id, Site.name, Site.url),
			'Remove site', 'RS', page, message=callback_query.message.message_id,
			to_str=lambda o: f'<a href="{o.url}">{o.name}</a>',
		parse_mode='HTML', with_page=True)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RS,\d+;\d+$',callback_query.data), state='*')
async def remove_site(callback_query: types.callback_query.CallbackQuery) -> None:
	pid, sid = callback_query.data.split(";")
	pid = int(pid.split(',')[1])
	sid = int(sid)
	Site.delete().where(Site.id==sid).execute()
	await post_items_menu_paged(callback_query.message.chat.id, Site.select(Site.id, Site.name, Site.url),
			'Sites', 'RS', pid, message=callback_query.message.message_id,
			to_str=lambda o: f'<a href="{o.url}">{o.name}</a>',
		parse_mode='HTML', with_page=True)
	await dispatcher.bot.answer_callback_query(callback_query.id)




# Youtube Queries

@dispatcher.message_handler(commands=['add_youtube_query'])
@with_client_check_and_state
async def add_youtube_query_command(message: types.Message, state: FSMContext):
    await dispatcher.bot.send_message(message.chat.id, 'Input youtube query:')
    await state.set_state('input_ytquery')

@dispatcher.message_handler(state='input_ytquery')
async def add_youtube_query(message: types.Message, state: FSMContext):
    yquery = message.text.strip('\n')
    if SearchQuery.select().where(SearchQuery.value==yquery).exists():
    	await dispatcher.bot.send_message(message.chat.id, 
    		'This query already exists. Input another or print "/cancel" to cancel:')
    else:
        await state.update_data(query=yquery)
        await state.set_state('input_ytquery_name')
        await dispatcher.bot.send_message(message.chat.id, 'Input query name:')

@dispatcher.message_handler(state='input_ytquery_name')
async def add_youtube_query_name_input(message: types.Message, state: FSMContext):
	try:
		name = message.text.strip('\n')
		yquery = (await state.get_data())['query']
		yqo, cr = SearchQuery.get_or_create(name=name, value=yquery)
		if cr:
			await dispatcher.bot.send_message(message.chat.id, 'Query added.')
			await state.finish()
		else:
			await dispatcher.bot.send_message(message.chat.id, 'Error. Query with such name and params already exists.')
	except IntegrityError:
		await dispatcher.bot.send_message(message.chat.id, 
			'Error. Query with such name already exists. Input again:')
	except Exception as e:
		await dispatcher.bot.send_message(message.chat.id, str(e))

@dispatcher.message_handler(commands=['rm_youtube_query'])
@with_client_check
async def rm_youtube_query_command(message: types.Message):
    await post_items_menu_paged(message.chat.id, SearchQuery.select(SearchQuery.id, SearchQuery.name),
		'Remove query', 'RYQ', 1, with_page=True)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RYQ,\d+$',callback_query.data), state='*')
async def rm_youtube_query_list(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, 
			SearchQuery.select(SearchQuery.id, SearchQuery.name),
		   'Remove query', 'RYQ', page, with_page=True, message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^RYQ,\d+;\d+$',callback_query.data), state='*')
async def rm_youtube_query(callback_query: types.callback_query.CallbackQuery) -> None:
	pid, qid = callback_query.data.split(";")
	pid = int(pid.split(',')[1])
	qid = int(qid)
	SearchQuery.delete().where(SearchQuery.id==qid).execute()
	await post_items_menu_paged(callback_query.message.chat.id, 
		SearchQuery.select(SearchQuery.id, SearchQuery.name),
		   'Remove query', 'RYQ', pid, with_page=True, message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^QSEEN;\d+$',callback_query.data), state='*')
async def remove_query_seen_video(callback_query: types.callback_query.CallbackQuery) -> None:
	vid = int(callback_query.data.split(";")[1])
	QueryUnseenVideo.delete().where(QueryUnseenVideo.id==vid).execute()
	await dispatcher.bot.delete_message(callback_query.message.chat.id, 
		callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.message_handler(commands=['qunseen'])
@with_client_check
async def get_youtube_queries_list_for_unseen(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, select_with_count_of_backref(SearchQuery, QueryUnseenVideo), 
		'Query Unseen videos', 'QUNSEEN', 1,
		to_str=lambda o: f'{o.name} ({o.count})')

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^QUNSEEN,\d+$',callback_query.data), state='*')
async def get_youtube_queries_for_unseen_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, select_with_count_of_backref(SearchQuery, QueryUnseenVideo),
			'Query Unseen videos', 'QUNSEEN', page,
			to_str=lambda o: f'{o.name} ({o.count})', 
			message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^QUNSEEN;\d+$',callback_query.data), state='*')
async def get_unseenvideos_of_query(callback_query: types.callback_query.CallbackQuery) -> None:
	qid = int(callback_query.data.split(";")[1])
	await dispatcher.bot.answer_callback_query(callback_query.id)
	for v in QueryUnseenVideo.select(QueryUnseenVideo.id, QueryUnseenVideo.value).where(QueryUnseenVideo.query==qid).order_by(QueryUnseenVideo.id.asc()).iterator():
		keyboard=types.inline_keyboard.InlineKeyboardMarkup(2)
		keyboard.add(types.inline_keyboard.InlineKeyboardButton('Seen', 
											callback_data=f"QSEEN;{v.id}"),
			types.inline_keyboard.InlineKeyboardButton('x', callback_data="R"))
		await dispatcher.bot.send_message(callback_query.message.chat.id, 
			"https://youtube.com/watch?v="+v.value,
			reply_markup=keyboard)

@dispatcher.message_handler(commands=['clear_unseen_q_videos'])
@with_client_check
async def clear_unseen_query_videos_command(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, 
		select_with_count_of_backref(SearchQuery, QueryUnseenVideo), 
		"Clear unseen query videos", 'CQU', 1,
		to_str=lambda o: f'{o.name} ({o.count})',
		with_page=True)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^CQU,\d+$',callback_query.data), state='*')
async def clear_unseen_query_videos_callback(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, 
			select_with_count_of_backref(SearchQuery, QueryUnseenVideo),
			"Clear unseen query videos", 'CQU', page,
			to_str=lambda o: f'{o.name} ({o.count})',
			message=callback_query.message.message_id,
			with_page=True)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^CQU,\d+;\d+$',callback_query.data), state='*')
async def clear_unseen_query_videos(callback_query: types.callback_query.CallbackQuery) -> None:
	page, qid = callback_query.data.split(";")
	page = int(page.split(',')[1])
	qid = int(qid)
	if page > 0:
		QueryUnseenVideo.delete().where(QueryUnseenVideo.query==qid).execute()
		await post_items_menu_paged(callback_query.message.chat.id, 
			select_with_count_of_backref(SearchQuery, QueryUnseenVideo),
			"Clear unseen query videos", 'CQU', page,
			to_str=lambda o: f'{o.name} ({o.count})',
			message=callback_query.message.message_id,
			with_page=True)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.message_handler(commands=['qlast'])
@with_client_check
async def get_youtube_queries_list_for_lastvideos(message: types.Message) -> None:
	await post_items_menu_paged(message.chat.id, SearchQuery.select(SearchQuery.id, SearchQuery.name), 
		'Query Last videos', 'QLAST', 1)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^QLAST;\d+$',callback_query.data), state='*')
async def get_lastvideos_of_query(callback_query: types.callback_query.CallbackQuery) -> None:
	qid = int(callback_query.data.split(";")[1])
	for v in QueryLastVideo.select(QueryLastVideo.value).where(QueryLastVideo.query==qid).order_by(QueryLastVideo.current_timestamp.asc()).iterator():
		await dispatcher.bot.send_message(callback_query.message.chat.id, "https://youtube.com/watch?v="+v.value)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^QLAST,\d+$',callback_query.data), state='*')
async def get_youtube_queries_list_for_lastvideos_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_menu_paged(callback_query.message.chat.id, SearchQuery.select(SearchQuery.id, SearchQuery.name),
			'Query Last videos', 'QLAST', page, message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)

@dispatcher.message_handler(commands=['yqueries'])
@with_client_check
async def get_youtube_queries_list(message: types.Message) -> None:
	await post_items_list_paged(message.chat.id, SearchQuery.select(SearchQuery.id, SearchQuery.name, SearchQuery.value), 
		'Youtube Queries', 'YQL', 1, 
		to_str=lambda o: f'<a href="https://www.youtube.com/results?search_query={urllib.parse.quote_plus(o.value)}&sp=CAISAhAB">{o.name}</a>',
		parse_mode='HTML')

@dispatcher.callback_query_handler(lambda callback_query: re.match(r'^YQL,\d+$',callback_query.data), state='*')
async def get_youtube_queries_list_by_page(callback_query: types.callback_query.CallbackQuery) -> None:
	page = int(callback_query.data.split(",")[1])
	if page > 0:
		await post_items_list_paged(callback_query.message.chat.id, 
			SearchQuery.select(SearchQuery.id, SearchQuery.name, SearchQuery.value), 
		'Youtube Queries', 'YQL', page, 
		to_str=lambda o: f'<a href="https://www.youtube.com/results?search_query={urllib.parse.quote_plus(o.value)}&sp=CAISAhAB">{o.name}</a>',
		parse_mode='HTML',
		message=callback_query.message.message_id)
	await dispatcher.bot.answer_callback_query(callback_query.id)