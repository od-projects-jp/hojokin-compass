"""Offline regression tests for individual subsidy publishing."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import collect_individual as collector
from individual_coverage import build_coverage
from collect_aichi import convert, decode_csv
from collect_municipal import normalize, parse_csv, validate_source, collect_one


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
            PUBLIC_FILE=self.public, REVIEW_FILE=self.review,
            VERIFIED_DIR=self.root / "regions"
        )
        self.paths.start()
        self.addCleanup(self.paths.stop)

    def write_verified(self, records):
        self.verified.write_text(
            json.dumps({"subsidies": records}, ensure_ascii=False), encoding="utf-8"
        )

    def test_municipal_registry_csv_normalization(self):
        source = {"id": "koganei", "name": "小金井市", "area": "東京都 小金井市",
                  "dataset_url": "https://www.opendata.metro.tokyo.lg.jp/koganei/22_support_system.csv",
                  "landing_url": "https://catalog.data.metro.tokyo.lg.jp/dataset/t132101d0000000045"}
        rows = parse_csv("制度名,対象者,概要,URL\n住宅支援,市民,家賃補助,https://example.go.jp/program\n".encode("utf-8-sig"))
        items = normalize(rows, source)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["review_status"], "要確認")
        self.assertEqual(items[0]["area"], "東京都 小金井市")
        self.assertEqual(items[0]["source_id"], "koganei")
        self.assertEqual(items[0]["source"], "https://example.go.jp/program")

    def test_municipal_csv_schema_mismatch_fails_safely(self):
        source = {"id": "koganei", "area": "東京都 小金井市",
                  "landing_url": "https://catalog.data.metro.tokyo.lg.jp/dataset/t132101d0000000045"}
        with self.assertRaises(ValueError):
            normalize([{"無関係な列": "value"}], source)

    def test_municipal_rejects_unapproved_download_host(self):
        source = {"id": "bad", "dataset_url": "https://example.com/feed.csv",
                  "landing_url": "https://example.com/"}
        with self.assertRaises(ValueError):
            validate_source(source)

    def test_aichi_candidates_are_review_only(self):
        rows = decode_csv("制度名,対象者,概要\n家賃支援,住民,住まいの支援\n".encode("utf-8-sig"))
        candidates = convert(rows)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["title"], "家賃支援")
        self.assertEqual(candidates[0]["area"], "愛知県")
        self.assertEqual(candidates[0]["review_status"], "要確認")
        self.assertEqual(candidates[0]["source_row"], 1)

    def test_regional_verified_files_are_combined(self):
        self.write_verified([self.record])
        regional_dir = self.root / "regions"
        regional_dir.mkdir()
        osaka = dict(self.record, title="大阪の制度", area="大阪府")
        (regional_dir / "osaka.json").write_text(
            json.dumps({"subsidies": [osaka]}, ensure_ascii=False), encoding="utf-8"
        )
        records = collector.load_verified()
        self.assertEqual(len(records), 2)
        self.assertEqual({r["area"] for r in records}, {"東京都", "大阪府"})

    def test_prefecture_coverage_counts(self):
        report = build_coverage([self.record, dict(self.record, area="全国")])
        self.assertEqual(report["prefectures"]["東京都"], 1)
        self.assertEqual(report["prefectures"]["大阪府"], 0)
        self.assertEqual(report["nationwide"], 1)
        self.assertEqual(report["prefectures_with_records"], 1)
        self.assertEqual(report["total_prefectures"], 47)

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
