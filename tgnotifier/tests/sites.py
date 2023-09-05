import pytest
from .base import getAbsPath
from tgnotifier.utils.helpers.scraper import OrderedAutoScraper
from tgnotifier.utils.sites import clear_ads

class TestBuild:
    scraper = OrderedAutoScraper()

    def test_one_post(self):
        html = None
        with open(getAbsPath('site2.txt'), 'r') as f:
            html = f.read()
        results = self.scraper.build(['https://thehackernews.com/2023/06/new-linux-ransomware-strain-blacksuit.html'], 
            'https://thehackernews.com/', html=html)
        assert results == ['https://thehackernews.com/2023/06/new-linux-ransomware-strain-blacksuit.html',
 'https://thehackernews.com/2023/06/cloud-security-tops-concerns-for.html',
 'https://thn.news/wing-newsfeed-5',
 'https://thehackernews.com/2023/06/ftc-slams-amazon-with-308m-fine-for.html',
 'https://thehackernews.com/2023/06/new-botnet-malware-horabot-targets.html',
 'https://thehackernews.com/2023/06/the-importance-of-managing-your-data.html',
 'https://thehackernews.com/2023/06/camaro-dragon-strikes-with-new-tinynote.html',
 'https://thehackernews.com/2023/06/north-koreas-kimsuky-group-mimics-key.html',
 'https://thehackernews.com/2023/06/moveit-transfer-under-attack-zero-day.html',
 'https://thehackernews.com/2023/06/evasive-qbot-malware-leverages-short.html']

    def test_invalid_page(self):
        results = self.scraper.build(['https://thehackernews.com/2023/06/new-linux-ransomware-strain-blacksuit.html'], 
                'https://thehackernews.com/', html='hffhfhfhfhfhfhhfh')
        assert results == []
        results = self.scraper.build(['https://thehackernews.com/2023/06/new-linux-ransomware-strain-blacksuit.html'], 
                'https://thehackernews.com/', html='<body><a><b/body>')
        assert results == []

    def test_invalid_posts(self):
        html = None
        with open(getAbsPath('site2.txt'), 'r') as f:
            html = f.read()
        results = self.scraper.build(['https://xakep.ru/2023/06/02/triangle_check/'], 
            'https://thehackernews.com/', html=html)
        assert results == []

    def test_multiple_posts(self):
        posts = ['https://xakep.ru/2023/06/02/triangle_check/', 'https://xakep.ru/2023/06/02/flipper-zero-review/']
        html = None
        with open(getAbsPath('site1.txt'), 'r') as f:
            html = f.read()
        results = self.scraper.build(posts, 'https://xakep.ru/', html=html)
        assert results == ['https://xakep.ru/2023/06/02/triangle_check/',
 'https://xakep.ru/2023/06/02/renessans-leak/',
 'https://xakep.ru/2023/06/02/web-store-adware/',
 'https://xakep.ru/2023/06/02/toyota-one-more-leak/',
 'https://xakep.ru/2023/06/02/terminator/',
 'https://xakep.ru/2023/06/02/zyxel-mirai/',
 'https://xakep.ru/2023/06/02/flipper-zero-review/',
 'https://xakep.ru/2023/06/02/ai-drone/',
 'https://xakep.ru/2023/06/01/operation-triangulation/',
 'https://xakep.ru/2023/06/01/gigabyte-backdoor/',
 'https://xakep.ru/2023/06/01/kali-linux-2023-2/',
 'https://xakep.ru/2023/06/01/network-visualization/',
 'https://xakep.ru/2023/06/01/medium-block/',
 'https://xakep.ru/2023/06/01/jetpack-update/',
 'https://xakep.ru/2023/06/01/rarbg-rip/',
 'https://xakep.ru/2023/06/01/it-is-conf/',
 'https://xakep.ru/2023/05/31/surface-camera-bug/',
 'https://xakep.ru/2023/05/31/openvpn-block/',
 'https://xakep.ru/2023/05/31/meganews-290/',
 'https://xakep.ru/2023/05/31/confiscation-of-property/',
 'https://xakep.ru/2023/05/31/migraine/',
 'https://xakep.ru/2023/05/31/android-spy-spinok/',
 'https://xakep.ru/2023/05/31/codeby-summer/',
 'https://xakep.ru/2023/05/30/python-camera/',
 'https://xakep.ru/2023/05/31/captcha-solvers/',
 'https://xakep.ru/2023/05/30/wikimedia-foundation/',
 'https://xakep.ru/2023/05/30/raidforums-leak/',
 'https://xakep.ru/2023/05/30/my-business-leak/',
 'https://xakep.ru/2023/05/30/hacking-smartphone/',
 'https://xakep.ru/2023/05/30/sk-breach/',
 'https://xakep.ru/2023/05/30/super-vpn/',
 'https://xakep.ru/2023/05/29/pypi-2fa-2/',
 'https://xakep.ru/2023/05/29/file-archivers-in-the-browser/',
 'https://xakep.ru/2023/05/29/htb-absolute/',
 'https://xakep.ru/2023/05/29/rasket/',
 'https://xakep.ru/2023/05/29/windows-xp-activation/',
 'https://xakep.ru/2023/05/29/vkusno-i-tochka-leak/',
 'https://xakep.ru/2023/05/28/microcontroller-webinar/',
 'https://xakep.ru/2023/05/26/fintoch-exit-sacm/',
 'https://xakep.ru/2023/05/26/zyxel-rce-2/']

    def test_empty_posts_list(self):
        html = None
        with open(getAbsPath('site2.txt'), 'r') as f:
            html = f.read()
        results = self.scraper.build([], 
            'https://thehackernews.com/', html=html)
        assert results == []


class TestGetResults:
    scraper = OrderedAutoScraper()

    def test_valid_page(self):
        html = None
        with open(getAbsPath('site2.txt'), 'r') as f:
            html = f.read()
        self.scraper.loadFromFile(getAbsPath('stack2.txt'))
        results = self.scraper.get_result_similar('https://thehackernews.com/', html=html)
        assert results == ['https://thehackernews.com/2023/06/new-linux-ransomware-strain-blacksuit.html',
 'https://thehackernews.com/2023/06/cloud-security-tops-concerns-for.html',
 'https://thn.news/wing-newsfeed-5',
 'https://thehackernews.com/2023/06/ftc-slams-amazon-with-308m-fine-for.html',
 'https://thehackernews.com/2023/06/new-botnet-malware-horabot-targets.html',
 'https://thehackernews.com/2023/06/the-importance-of-managing-your-data.html',
 'https://thehackernews.com/2023/06/camaro-dragon-strikes-with-new-tinynote.html',
 'https://thehackernews.com/2023/06/north-koreas-kimsuky-group-mimics-key.html',
 'https://thehackernews.com/2023/06/moveit-transfer-under-attack-zero-day.html',
 'https://thehackernews.com/2023/06/evasive-qbot-malware-leverages-short.html']

    def test_invalid_page(self):
        self.scraper.loadFromFile(getAbsPath('stack2.txt'))
        results = self.scraper.get_result_similar('https://thehackernews.com/', 
            html='<body>fhfhhfhfhfhfhfh</body>')
        assert results == []


class TestClearAds:

    def test_all_urls_same_domain(self):
        target = "https://abc.com"
        posts = ["https://abc.com/1", "https://abc.com/2.html"]
        assert clear_ads(target, posts) == posts

    def test_invalid_target(self):
        target = "hjjjggjjggjjh"
        posts = ["https://abc.com/1", "https://abc.com/2.html"]
        assert clear_ads(target, posts) == []

    def test_empty_list(self):
        assert clear_ads("https://abc.com", []) == []

    def test_different_domains(self):
        target = "https://abc.com"
        posts = ["https://abc.com/1.html", "https://abc.com/2.html", 
           "https://hgj.com/1.html", "https://abc.net/2.html", "https://dot.abc.com/2"]
        assert clear_ads(target, posts) == ["https://abc.com/1.html", "https://abc.com/2.html"]
