from googleapiclient.discovery import build as build_google_api
from tgnotifier.core.settings import settings
from tgnotifier.utils.log import log
import time
import re
import requests as req

youtube = build_google_api("youtube", "v3", 
	developerKey=settings.YOUTUBE_API_KEY.get_secret_value())

def parse_link(link):
	a = link[24:].split("/")
	if len(a)==1:
		return (a[0][1:], True)
	else:
		return (a[1], len(a[0])!=7)

def getUploadsIdAndTitleByLink(link):
	ident, isUsername = parse_link(link)
	data = None
	if isUsername:
		data = youtube.channels().list(
                part="contentDetails,snippet",
                forUsername=ident
            ).execute()
		if 'items' not in data:
			ch_id = youtube.search().list(
              part='id',
              q=ident, type='channel',
            ).execute()['items'][0]['id']['channelId']
			data = youtube.channels().list(
              part="contentDetails,snippet",
              id=ch_id
              ).execute()['items'][0]
		else:
			data = data['items'][0]
	else:
		data = youtube.channels().list(
                part="contentDetails,snippet",
                id=ident
            ).execute()['items'][0]
	return (data['contentDetails']['relatedPlaylists']['uploads'], 
				data['snippet']['title'])

def getUploadsIdByLink(link):
	ident, isUsername = parse_link(link)
	if isUsername:
		data = youtube.channels().list(
                part="contentDetails",
                forUsername=ident
            ).execute()
		if 'items' not in data:
			ch_id = youtube.search().list(
              part='id',
              q=ident, type='channel',
            ).execute()['items'][0]['id']['channelId']
			data = youtube.channels().list(
              part="contentDetails,snippet",
              id=ch_id
              ).execute()
		return data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
	else:
		return youtube.channels().list(
                part="contentDetails",
                id=ident
            ).execute()['items'][0]['contentDetails']['relatedPlaylists']['uploads']

def checkTerm(text, term):
	return re.search(term, text, re.IGNORECASE)

def isTitleValid(text, include, exclude):
	for t in exclude:
		if checkTerm(text, t):
			return False
	if include:
		for t in include:
			if checkTerm(text, t):
				return True
	else:
		return True
	return False

def getNewVideosFromPlaylist(id, last, include, exclude):
	allv = None
	for i in range(3):
		try:
			allv = youtube.playlistItems().list(
		playlistId=id,
		part="snippet",
		maxResults=5,
		pageToken=None
	).execute()
			break
		except:
			time.sleep(1)
			log("getvideos failed due error")
	videos = []
	newlast=[v['snippet']['resourceId']['videoId'] for v in allv['items']]
	for v in allv['items']:
		data = (v['snippet']['title'], v['snippet']
					['resourceId']['videoId'])
		if data[1] in last:
			break
		else:
			if isTitleValid(data[0], include, exclude):
				videos.append(data)
	newlast.reverse()
	videos.reverse()
	return (newlast,videos)

def parseYoutubeQueryPage(html):
    match = re.search(r'var ytInitialData\s=\s(.*);</script><script', html)
    if match:
    	r = match.group(1)
    	return [(x.group(1),x.group(4)) for x in re.finditer(r'"videoId":"([-_A-Za-z0-9]+)","thumbnail":{"thumbnails":\[({"url":"[^"]+"(,"width":[0-9]+,"height":[0-9]+)?},?)+\]},"title":{"runs":\[{"text":"(.*?)"}\],"accessibility"',r)][:10]
    else:
    	return None

def getNewVideosFromSearchQuery(q, lastvideos):
	r=None
	for i in range(settings.SCRAPER_ATTEMPTS):
		try:
			r = req.get("https://www.youtube.com/results",params={'search_query':q, 'sp':"CAISAhAB"})
			if r.status_code==200:
				break
			else:
				time.sleep(settings.SCRAPER_INTERVAL)
				log("getvideosbyquery failed due response")
		except:
			time.sleep(settings.SCRAPER_INTERVAL)
			log("getvideosbyquery failed due error")
	if r and r.status_code == 200:
		videos = parseYoutubeQueryPage(r.text)
		if videos:
		    l=[]
		    for v in videos:
			    if v[0] in lastvideos:
				    break
			    else:
				    l.append(v)
		    return ([x[0] for x in videos],l)
	return (lastvideos,[])