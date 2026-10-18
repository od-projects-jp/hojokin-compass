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
from build_individual_review_queue import build_queue, normalized_title
from individual_deadlines import build_deadline_report, deadline_status
from datetime import date


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

    def test_verified_publication_survives_upstream_outage(self):
        self.write_verified([self.record])
        existing_review = {"subsidies": [{"title": "前回の確認候補"}]}
        self.review.write_text(json.dumps(existing_review, ensure_ascii=False), encoding="utf-8")
        with patch.object(collector, "fetch_rows", side_effect=OSError("HTTP 503")):
            collector.main()
        published = json.loads(self.public.read_text(encoding="utf-8"))
        self.assertEqual(published["total"], 1)
        self.assertEqual(published["subsidies"][0]["title"], "確認済み制度")
        self.assertEqual(json.loads(self.review.read_text(encoding="utf-8")), existing_review)

    def test_ended_municipal_program_is_not_high_priority(self):
        source = {"id": "koganei", "area": "東京都 小金井市",
                  "landing_url": "https://catalog.data.metro.tokyo.lg.jp/dataset/t132101d0000000045"}
        items = normalize([{"タイトル（制度名）": "給付金の受付は終了しました",
                            "対象者": "小金井市民",
                            "URL": "https://www.city.koganei.lg.jp/closed"}], source)
        self.assertEqual(items[0]["review_priority"], "終了要確認")
        self.assertTrue(items[0]["ended_in_title"])

    def test_title_normalization_removes_ascii_and_full_width_spaces(self):
        self.assertEqual(normalized_title(" 児童　育成 手当（小金井市） "), "児童育成手当")

    def test_fixed_deadline_status_boundaries(self):
        today = date(2026, 10, 19)
        self.assertEqual(deadline_status("2026-10-18", today), ("期限経過", -1))
        self.assertEqual(deadline_status("2026-10-19", today), ("締切間近", 0))
        self.assertEqual(deadline_status("2026-11-18", today), ("締切間近", 30))
        self.assertEqual(deadline_status("2026-11-19", today), ("期限設定あり", 31))
        with self.assertRaises(ValueError):
            deadline_status("2026-02-30", today)

    def test_deadline_report_only_uses_explicit_dates(self):
        items = [
            {"title": "制度A", "area": "東京都", "source": "https://example.org/a",
             "application_deadline": "2026-10-25"},
            {"title": "制度B", "area": "全国", "source": "https://example.org/b"},
            {"title": "制度C", "area": "東京都", "source": "https://example.org/c",
             "application_deadline": "2026-10-01"},
        ]
        report = build_deadline_report(items, date(2026, 10, 19))
        self.assertEqual(report["total_with_fixed_deadlines"], 2)
        self.assertEqual(report["upcoming_within_30_days"], 1)
        self.assertEqual(report["past_deadline"], 1)

    def test_city_qualified_titles_are_matched_in_review_queue(self):
        self.assertEqual(normalized_title("児童育成手当（小金井市）"), normalized_title("児童育成手当"))
        dataset = {"subsidies": [{"title": "児童育成手当", "area": "東京都 小金井市",
                  "source_id": "koganei", "source": "https://www.city.koganei.lg.jp/benefit",
                  "review_priority": "高", "possible_business_only": False}]}
        verified = [{"title": "児童育成手当（小金井市）", "area": "東京都 小金井市",
                     "source": "https://www.city.koganei.lg.jp/benefit"}]
        self.assertEqual(build_queue([dataset], verified), [])

    def test_review_queue_excludes_verified_name_and_flags_shared_page(self):
        verified = [{"title": "制度A", "area": "東京都 小金井市",
                     "source": "https://www.city.koganei.lg.jp/a"}]
        dataset = {"subsidies": [
            {"title": "制度A", "area": "東京都 小金井市", "source_id": "koganei",
             "source": "https://www.city.koganei.lg.jp/a", "review_priority": "高",
             "possible_business_only": False},
            {"title": "制度B", "area": "東京都 小金井市", "source_id": "koganei",
             "source": "https://www.city.koganei.lg.jp/a/", "review_priority": "高",
             "possible_business_only": False},
            {"title": "制度C", "area": "東京都 小金井市", "source_id": "koganei",
             "source": "https://www.city.koganei.lg.jp/c", "review_priority": "通常",
             "possible_business_only": False},
        ]}
        queue = build_queue([dataset], verified)
        self.assertEqual([x["title"] for x in queue], ["制度B", "制度C"])
        self.assertTrue(queue[0]["potentially_covered"])
        self.assertFalse(queue[1]["potentially_covered"])

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

    def test_koganei_real_header_names(self):
        source = {"id": "koganei", "area": "東京都 小金井市",
                  "landing_url": "https://catalog.data.metro.tokyo.lg.jp/dataset/t132101d0000000045"}
        records = normalize([{"タイトル（制度名）": "制度A", "制度概要": "説明",
                              "制度所管組織": "担当課", "対象者": "市民"}], source)
        self.assertEqual(records[0]["title"], "制度A")
        self.assertEqual(records[0]["agency"], "担当課")
        self.assertEqual(records[0]["review_priority"], "通常")

    def test_municipal_csv_schema_mismatch_fails_safely(self):
        source = {"id": "koganei", "area": "東京都 小金井市",
                  "landing_url": "https://catalog.data.metro.tokyo.lg.jp/dataset/t132101d0000000045"}
        with self.assertRaises(ValueError):
            normalize([{"無関係な列": "value"}], source)

    def test_nakano_official_source_allowed(self):
        validate_source({"id": "nakano",
                         "dataset_url": "https://www2.wagmap.jp/nakanodatamap/nakanodatamap/opendatafile/map_1/CSV/opendata_5000776.csv",
                         "landing_url": "https://catalog.data.metro.tokyo.lg.jp/dataset/t131148d0000000035"})

    def test_prior_year_program_is_flagged_for_review(self):
        source = {"id": "koganei", "area": "東京都 小金井市",
                  "landing_url": "https://catalog.data.metro.tokyo.lg.jp/dataset/t132101d0000000045"}
        items = normalize([{"タイトル（制度名）": "令和7年度 住宅支援",
                            "対象者": "小金井市民", "URL": "https://www.city.koganei.lg.jp/example"}], source)
        self.assertTrue(items[0]["past_year_in_title"])
        self.assertEqual(items[0]["review_priority"], "要更新確認")
        self.assertEqual(items[0]["review_status"], "要確認")

    def test_municipal_source_note_is_retained(self):
        source = {"id": "nakano", "area": "東京都 中野区",
                  "landing_url": "https://catalog.data.metro.tokyo.lg.jp/dataset/t131148d0000000035",
                  "source_note": "公式データ更新日2024年。要再確認"}
        items = normalize([{"タイトル": "住宅支援", "対象者": "区民"}], source)
        self.assertEqual(items[0]["review_status"], "要確認")
        self.assertIn("2024", items[0]["source_note"])

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
