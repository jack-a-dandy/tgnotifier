import time
from .helpers.scraper import OrderedAutoScraper
import requests
from bs4 import BeautifulSoup
from tgnotifier.core.settings import settings
import validators
from urllib.parse import urlparse

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

def get_posts_by_stacks(url, stacks):
    scraper = OrderedAutoScraper()
    scraper.loadFromStr(stacks)
    scraper.reconnect_attempts = settings.SCRAPER_ATTEMPTS
    scraper.reconnect_interval = settings.SCRAPER_INTERVAL
    return scraper.get_result_similar(url)

def make_stacks_by_posts(url, wanted_posts):
    scraper = OrderedAutoScraper()
    scraper.reconnect_attempts = settings.SCRAPER_ATTEMPTS
    scraper.reconnect_interval = settings.SCRAPER_INTERVAL
    res = scraper.build(wanted_posts, url)
    return (res, scraper)

def get_title_by_url(url):
    for i in range(settings.SCRAPER_ATTEMPTS):
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                return BeautifulSoup(res.text, 'lxml').title.string
            else:
                time.sleep(settings.SCRAPER_INTERVAL)
        except:
            time.sleep(settings.SCRAPER_INTERVAL)
    return None

def clear_ads(url, posts):
    #return [p for p in posts if p.startswith(url)]
    domain = urlparse(url).netloc
    return [p for p in posts if urlparse(p).netloc == domain]

def filter_new_posts(last, new):
    res = []
    for p in new:
        if p[0] in last:
            break
        else:
            res.append(p)
    return (res, new)

def is_valid_url(url):
    return validators.url(url)