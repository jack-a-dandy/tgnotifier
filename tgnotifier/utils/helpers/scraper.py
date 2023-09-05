from bs4 import BeautifulSoup, SoupStrainer
from html import unescape
import requests
import unicodedata
from urllib.parse import urljoin, urlparse
from difflib import SequenceMatcher
from collections import OrderedDict, defaultdict
import hashlib
import string
import random
import json
import time

def find_all_multiple(tg, targets, recursive=True):
    generator = tg.descendants
    if not recursive:
        generator = tg.children
        
    strainers = []
        
    for t in targets:
        name = t.get('name')
        if isinstance(name, SoupStrainer):
            strainers.append(name)
        else:
            strainers.append(SoupStrainer(**t))
                
    results = []
        
    while True:
        try:
            i = next(generator)
        except StopIteration:
            break
        if i:
            for idx, s in enumerate(strainers):
                found = s.search(i)
                if found:
                    results.append((found, idx))
    return results

def normalize(item):
    if not isinstance(item, str):
        return item
    return unicodedata.normalize("NFKD", item.strip())
    
def text_match(t1, t2, ratio_limit):
    if hasattr(t1, 'fullmatch'):
        return bool(t1.fullmatch(t2))
    if ratio_limit >= 1:
        return t1 == t2
    return SequenceMatcher(None, t1, t2).ratio() >= ratio_limit
    
def unique_stack_list(stack_list):
    seen = set()
    unique_list = []
    for stack in stack_list:
        stack_hash = stack['hash']
        if stack_hash in seen:
            continue
        del stack['hash']
        unique_list.append(stack)
        seen.add(stack_hash)
    return unique_list

def unique_hashable(hashable_items):
    return list(OrderedDict.fromkeys(hashable_items))

def list_duplicates(seq):
    tally = defaultdict(list)
    for i,item in enumerate(seq):
        tally[item].append(i)
    return [(key,locs) for key,locs in tally.items()]
    
def get_non_rec_text(element):
    return ''.join(element.find_all(text=True, recursive=False)).strip()
    
def get_random_str(n):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for i in range(n))


class FuzzyText(object):
    def __init__(self, text, ratio_limit):
        self.text = text
        self.ratio_limit = ratio_limit
        self.match = None

    def search(self, text):
        return SequenceMatcher(None, self.text, text).ratio() >= self.ratio_limit
        

class OrderedAutoScraper():

    request_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 \
            (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36"
    }

    reconnect_attempts = 3
    reconnect_interval = 1

    def __init__(self, stack_list=[]):
        self.stack_list = stack_list
    
    @classmethod
    def _fetch_html(cls, url, request_args=None):
        request_args = request_args or {}
        headers = dict(cls.request_headers)
        if url:
            headers["Host"] = urlparse(url).netloc

        user_headers = request_args.pop("headers", {})
        headers.update(user_headers)
        for i in range(cls.reconnect_attempts):
            try:
                res = requests.get(url, headers=headers, **request_args)
                if res.status_code == 200:
                    break
                else:
                    time.sleep(cls.reconnect_interval)
            except:
                time.sleep(cls.reconnect_interval)
        if res.status_code == 200:
            if res.encoding == "ISO-8859-1" and not "ISO-8859-1" in res.headers.get(
                "Content-Type", ""
            ):
                res.encoding = res.apparent_encoding
            html = res.text
            return html
        else:
            raise Exception("Unable to get a valid response from site.")
    
    @classmethod
    def _get_soup(cls, url=None, html=None, request_args=None):
        if html:
            html = normalize(unescape(html))
            return BeautifulSoup(html, "lxml")

        html = cls._fetch_html(url, request_args)
        html = normalize(unescape(html))

        return BeautifulSoup(html, "lxml")
        
    @staticmethod
    def _child_has_text(child, text, url, text_fuzz_ratio):
        child_text = child.getText().strip()

        if text_match(text, child_text, text_fuzz_ratio):
            parent_text = child.parent.getText().strip()
            if child_text == parent_text and child.parent.parent:
                return False

            child.wanted_attr = None
            return True

        if text_match(text, get_non_rec_text(child), text_fuzz_ratio):
            child.is_non_rec_text = True
            child.wanted_attr = None
            return True

        for key, value in child.attrs.items():
            if not isinstance(value, str):
                continue

            value = value.strip()
            if text_match(text, value, text_fuzz_ratio):
                child.wanted_attr = key
                return True

            if key in {"href", "src"}:
                full_url = urljoin(url, value)
                if text_match(text, full_url, text_fuzz_ratio):
                    child.wanted_attr = key
                    child.is_full_url = True
                    return True

        return False
    
    def _get_children(self, soup, text, url, text_fuzz_ratio):
        children = reversed(soup.findChildren())
        children = [
            x for x in children if self._child_has_text(x, text, url, text_fuzz_ratio)
        ]
        return children
        
    @staticmethod
    def _get_valid_attrs(item):
        key_attrs = {"class", "style"}
        attrs = {
            k: v if v != [] else "" for k, v in item.attrs.items() if k in key_attrs
        }

        for attr in key_attrs:
            if attr not in attrs:
                attrs[attr] = ""
        return attrs
        
    @staticmethod
    def _get_fuzzy_attrs(attrs, attr_fuzz_ratio):
        attrs = dict(attrs)
        for key, val in attrs.items():
            if isinstance(val, str) and val:
                val = FuzzyText(val, attr_fuzz_ratio)
            elif isinstance(val, (list, tuple)):
                val = [FuzzyText(x, attr_fuzz_ratio) if x else x for x in val]
            attrs[key] = val
        return attrs
        
    def build(self, wanted_list, url=None, html=None, text_fuzz_ratio=1.0):
    
        soup = self._get_soup(url=url, html=html)
        
        result_list = []

        wanted_list = [normalize(x) for x in wanted_list]
        
        stack_list = []

        for wanted in wanted_list:
            children = self._get_children(soup, wanted, url, text_fuzz_ratio)

            for child in children:
                stack = self._build_stack(child)
                stack_list.append(stack)

        stack_list = unique_stack_list(stack_list)
        
        if len(stack_list) == 0:
            return []
        
        if len(stack_list) > 1:
            self.stack_list = self._merge_stacks([], stack_list)
            result_list = self._get_results_with_stacks(self.stack_list, [soup], url, [], 1.0)
        else:
            self.stack_list = stack_list
            result_list = self._get_result_with_stack(self.stack_list[0], [soup], url, 1.0)
        
        return unique_hashable(result_list)
    
    @classmethod
    def _merge_stacks(cls, res, stack_list):
        
        hashs = []
        
        for s in stack_list:
            hashs.append(hashlib.sha256(str(s['content'][0]).encode("utf-8")).hexdigest())
            
        shashs = list_duplicates(hashs)
        
        if len(shashs) == 1:
            res.append(stack_list[0]['content'][0])
            for s in stack_list:
                s['content'].pop(0)
            cls._merge_stacks(res, stack_list)
        else:
            l = []
            res.append(l)
            for h in shashs:
                if len(h[1]) == 1:
                    l.append(stack_list[h[1][0]])
                else:
                    l2 = []
                    l.append(l2)
                    cls._merge_stacks(l2, [stack_list[i] for i in h[1]])
        return res
        
    @classmethod
    def _build_stack(cls, child):
        content = [(child.name, cls._get_valid_attrs(child))]

        parent = child
        while True:
            grand_parent = parent.findParent()
            if not grand_parent:
                break

            children = grand_parent.findAll(
                parent.name, cls._get_valid_attrs(parent), recursive=False
            )
            for i, c in enumerate(children):
                if c == parent:
                    content.insert(
                        0, (grand_parent.name, cls._get_valid_attrs(grand_parent), i)
                    )
                    break

            if not grand_parent.parent:
                break

            parent = grand_parent

        wanted_attr = getattr(child, "wanted_attr", None)
        is_full_url = getattr(child, "is_full_url", False)
        is_non_rec_text = getattr(child, "is_non_rec_text", False)
        stack = dict(
            content=content,
            wanted_attr=wanted_attr,
            is_full_url=is_full_url,
            is_non_rec_text=is_non_rec_text,
        )
        stack["hash"] = hashlib.sha256(str(stack).encode("utf-8")).hexdigest()
        stack["stack_id"] = "rule_" + get_random_str(4)
        return stack
        
    @staticmethod
    def _fetch_result_from_child(child, wanted_attr, is_full_url, url, is_non_rec_text):
        if wanted_attr is None:
            if is_non_rec_text:
                return get_non_rec_text(child)
            return child.getText().strip()

        if wanted_attr not in child.attrs:
            return None

        if is_full_url:
            return urljoin(url, child.attrs[wanted_attr])

        return child.attrs[wanted_attr]
        
    def _get_result_with_stack(self, stack, parents, url, attr_fuzz_ratio=1.0):
        stack_content = stack["content"]
        for index, item in enumerate(stack_content):
            children = []
            if item[0] == "[document]":
                continue
            for parent in parents:

                attrs = item[1]
                if attr_fuzz_ratio < 1.0:
                    attrs = self._get_fuzzy_attrs(attrs, attr_fuzz_ratio)

                found = parent.findAll(item[0], attrs, recursive=False)
                if not found:
                    continue

                if index == len(stack_content) - 1:
                    idx = min(len(found) - 1, stack_content[index - 1][2])
                    found = [found[idx]]

                children += found

            parents = children

        wanted_attr = stack["wanted_attr"]
        is_full_url = stack["is_full_url"]
        is_non_rec_text = stack.get("is_non_rec_text", False)
        result = [
                self._fetch_result_from_child(
                    i, wanted_attr, is_full_url, url, is_non_rec_text
                )  
            for i in parents
        ]
        return result
        
    def _get_results_with_stacks(self, stacks, parents, url, results=[], attr_fuzz_ratio=1.0):
        
        lel = stacks[-1]
        
        for index in range(len(stacks)-1):
            item = stacks[index]
            children = []
            if item[0] == "[document]":
                continue
            for parent in parents:

                attrs = item[1]
                if attr_fuzz_ratio < 1.0:
                    attrs = self._get_fuzzy_attrs(attrs, attr_fuzz_ratio)

                found = parent.findAll(item[0], attrs, recursive=False)
                if not found:
                    continue

                children += found

            parents = children
            
        item = lel
        children = []
        tys = []
        els = []
        for i in item:
            if isinstance(i, dict):
                els.append(i['content'][0])
                tys.append(0)
            else:
                els.append(i[0])
                tys.append(1)
                        
        targets = [{'name': e[0], 
            'attrs': self._get_fuzzy_attrs(e[1], attr_fuzz_ratio) if attr_fuzz_ratio < 1.0 else e[1]} 
            for e in els
            ]
                
        for parent in parents:
            found = find_all_multiple(parent, targets, recursive=False)
            if not found:
                continue
            for f in found:
                if tys[f[1]]:
                    self._get_results_with_stacks(item[f[1]][1:], [f[0]], url, results, attr_fuzz_ratio)
                else:
                    l = len(item[f[1]]['content'])
                    if l > 2:
                        c = item[f[1]].copy()
                        c['content'].pop(0)
                        r = self._get_result_with_stack(c, [f[0]], attr_fuzz_ratio)
                        results.extend(r)
                    else:
                        st = item[f[1]]['content']
                        attrs = st[1][1]
                        if attr_fuzz_ratio < 1.0:
                            attrs = self._get_fuzzy_attrs(attrs, attr_fuzz_ratio)

                        found2 = f[0].findAll(st[1][0], attrs, recursive=False)
                        if found2:
                            idx = min(len(found2) - 1, st[0][2])
                            r = found2[idx]
                            wanted_attr = item[f[1]]["wanted_attr"]
                            is_full_url = item[f[1]]["is_full_url"]
                            is_non_rec_text = item[f[1]].get("is_non_rec_text", False)
                            r = self._fetch_result_from_child(
                                        r, wanted_attr, is_full_url, url, is_non_rec_text
                                    )
                            results.append(r)
                     
        return results
        
    def loadFromStr(self, s):
        data = json.loads(s)
        self.stack_list = data["stack_list"]
            
    def dumpToStr(self):
        return json.dumps(dict(stack_list=self.stack_list))
            
    def dumpToFile(self, fname):
        data = dict(stack_list=self.stack_list)
        with open(fname, "w") as f:
            json.dump(data, f)
        
    def loadFromFile(self, fname):
        with open(fname, "r") as f:
            data = json.load(f)

        self.stack_list = data["stack_list"]
            
    def get_result_similar(self, url, html=None, attr_fuzz_ratio=1.0):
        soup = self._get_soup(url=url, html=html)
        result_list = None
        
        if len(self.stack_list) > 1:
            result_list = self._get_results_with_stacks(self.stack_list, [soup], url, [], attr_fuzz_ratio)
        else:
            result_list = self._get_result_with_stack(self.stack_list[0], [soup], url, attr_fuzz_ratio)
        
        return unique_hashable(result_list)