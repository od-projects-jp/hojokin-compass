"""Guard regional SEO pages against fabricated, stale or mismatched listing data."""
import json
import re
import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
PAGES={"tokyo-support.html":"東京都","koganei-support.html":"東京都 小金井市","yokohama-support.html":"神奈川県 横浜市"}

class ListingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
        self.titles=[]
        self.in_h2=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="a" and "href" in a:self.links.append(a["href"])
        if tag=="h2":self.in_h2=True
    def handle_endtag(self,tag):
        if tag=="h2":self.in_h2=False
    def handle_data(self,data):
        if self.in_h2:self.titles.append(data)

class RegionalSEOTest(unittest.TestCase):
    def test_verified_region_content_and_sitemap(self):
        data=json.loads((ROOT/"public/data/individual.json").read_text(encoding="utf-8"))["subsidies"]
        sitemap=(ROOT/"sitemap.xml").read_text(encoding="utf-8")
        home=(ROOT/"index.html").read_text(encoding="utf-8")
        for file,area in PAGES.items():
            with self.subTest(file=file):
                html=(ROOT/file).read_text(encoding="utf-8")
                parser=ListingParser();parser.feed(html)
                expected=[x for x in data if x["area"]==area]
                self.assertEqual(len(expected),len(parser.titles))
                self.assertEqual(set(parser.titles),{x["title"] for x in expected})
                for x in expected:
                    self.assertIn(x["source"],parser.links)
                self.assertIn(file,sitemap)
                self.assertIn(file,home)
                self.assertIn('rel="canonical"',html)
                self.assertIn('name="description"',html)
                self.assertIn("公式サイト",html)

if __name__=="__main__":unittest.main()
