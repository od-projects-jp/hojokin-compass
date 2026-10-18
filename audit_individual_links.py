"""Audit official links without deleting verified programs on transient network errors."""
import json
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from collect_individual import load_verified

OUTPUT = Path("public/data/individual_link_health.json")


def probe(url, opener=urllib.request.urlopen):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return {"status": "invalid", "http_status": None, "reason": "Not an HTTPS URL"}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; HojokinCompassLinkAudit/1.0)"}
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, headers=headers, method=method)
            with opener(req, timeout=12) as response:
                return {"status": "ok", "http_status": response.status, "reason": ""}
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (403, 405, 501):
                continue
            return {"status": "needs_review", "http_status": exc.code, "reason": f"HTTP {exc.code}"}
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if method == "HEAD":
                continue
            return {"status": "unreachable", "http_status": None, "reason": type(exc).__name__}
    return {"status": "unreachable", "http_status": None, "reason": "No successful response"}


def build_report(records, probe_fn=probe):
    by_url = defaultdict(list)
    for item in records:
        by_url[item["source"]].append(item["title"])
    results = []
    for url, titles in sorted(by_url.items()):
        result = probe_fn(url)
        results.append({"source": url, "titles": titles, **result})
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total_unique_urls": len(results),
        "ok": sum(x["status"] == "ok" for x in results),
        "needs_review": sum(x["status"] != "ok" for x in results),
        "notice": "一時的な403・404・接続失敗だけで制度を削除しません。要確認は公式情報の再点検が必要です。",
        "results": results,
    }


def main():
    report = build_report(load_verified())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Official URL audit: {report['ok']}/{report['total_unique_urls']} reachable; {report['needs_review']} review")
    for item in report["results"]:
        if item["status"] != "ok":
            print("REVIEW:", item["http_status"], item["source"])


if __name__ == "__main__":
    main()
