"""Offline regression tests for individual subsidy publishing."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import collect_individual as collector


class IndividualDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.verified = self.root / "verified.json"
        self.public = self.root / "public.json"
        self.review = self.root / "review.json"
        self.record = {
            "title": "確認済み制度", "description": "説明", "area": "東京都",
            "agency": "東京都", "target": "個人", "categories": ["子育て"],
            "source": "https://example.go.jp/program",
            "review_status": "公式情報確認済み", "verified_at": "2026-10-18"
        }
        self.paths = patch.multiple(
            collector, VERIFIED_FILE=self.verified,
            PUBLIC_FILE=self.public, REVIEW_FILE=self.review
        )
        self.paths.start()
        self.addCleanup(self.paths.stop)

    def write_verified(self, records):
        self.verified.write_text(
            json.dumps({"subsidies": records}, ensure_ascii=False), encoding="utf-8"
        )

    def test_only_verified_records_published(self):
        self.write_verified([self.record])
        unverified = {
            "補助金名": "未確認の制度", "補助金の概要": "子育て支援",
            "補助対象者": "個人", "所管部署": "東京都",
            "補助対象経費": "", "各局HPリンク": ""
        }
        with patch.object(collector, "fetch_rows", return_value=[unverified]):
            collector.main()
        public = json.loads(self.public.read_text(encoding="utf-8"))
        review = json.loads(self.review.read_text(encoding="utf-8"))
        self.assertEqual(public["total"], 1)
        self.assertEqual(public["subsidies"][0]["title"], "確認済み制度")
        self.assertEqual(review["total"], 1)
        self.assertEqual(review["subsidies"][0]["title"], "未確認の制度")

    def test_duplicate_verified_record_is_deduplicated(self):
        self.write_verified([self.record, dict(self.record)])
        self.assertEqual(len(collector.load_verified()), 1)

    def test_missing_official_link_blocks_publication(self):
        bad = dict(self.record, source="")
        self.write_verified([bad])
        with self.assertRaises(ValueError):
            collector.load_verified()

    def test_unapproved_record_blocks_publication(self):
        bad = dict(self.record, review_status="要確認")
        self.write_verified([bad])
        with self.assertRaises(ValueError):
            collector.load_verified()

    def test_invalid_data_does_not_overwrite_public_file(self):
        self.public.write_text("existing public data", encoding="utf-8")
        self.write_verified([dict(self.record, source="http://example.com")])
        with patch.object(collector, "fetch_rows", return_value=[]):
            with self.assertRaises(ValueError):
                collector.main()
        self.assertEqual(self.public.read_text(encoding="utf-8"), "existing public data")


if __name__ == "__main__":
    unittest.main()
