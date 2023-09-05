import pytest
from .base import getAbsPath
from tgnotifier.utils.youtube import parseYoutubeQueryPage

class TestParseYoutubeQueryPage:

    def test_page_with_results(self):
        res = None
        with open(getAbsPath('youtube_query1.txt')) as f:
            res = f.read()
        assert parseYoutubeQueryPage(res) == [('yW9whD04TG0', 'Boogeyman | Short Horror Film'), 
    ('X0xwp6h0gxE', 'मंकी किंग की अधूरी दास्तान | movie explained in Hindi | short horror storyq #short #trending #viral'),
    ('fz6-Yh5lzgQ', 'Monster | movie explained in hindi | short horror story | #movieexplanation'),
    ('vJwxGyGvRes', 'DARK RED - Horror Short Film - Music Composed by Juno Reactor'), 
    ('xcZAMPqqHnQ', 'एक कार जो पीती है खून ⛽ | movie explained in Hindi | short horror story #shorts'), 
    ('31vXosWO5pc', '#free fire #viral #trending #short #video'), 
    ('0mpX5preJ3o', 'The Baby In Yellow #short #gameplay #games#horrorgaming'), 
    ('nTDq6nHoeAM', 'Top 10 horror movie in bengali #trendingshorts #youtubeshorts #whatsapp_status #short #horrorstory'), 
    ('n-__znlJTFo', 'free fire 🎮 now short  🔥video 🎥 capcut editing📱💯 #shorts #trnding #short now short video ||'),
    ('1VfR0-td1ng', '𝐀𝐧𝐢𝐦𝐚𝐭𝐞𝐝 𝐇𝐨𝐫𝐫𝐨𝐫 𝐒𝐭𝐨𝐫𝐲 𝐨𝐟 𝐍𝐢𝐠𝐡𝐭 𝐖𝐚𝐭𝐜𝐡𝐦𝐚𝐧 | 𝐒𝐡𝐨𝐫𝐭 𝐇𝐨𝐫𝐫𝐨𝐫 𝐅𝐢𝐥𝐦 | #horrorshorts')]

    def test_invalid_param(self):
        assert parseYoutubeQueryPage('hfhfhffhf') == None

    def test_page_with_no_results(self):
        res = None
        with open(getAbsPath('youtube_query2.txt')) as f:
            res = f.read()
        assert parseYoutubeQueryPage(res) == []