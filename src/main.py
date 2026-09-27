"""Yahoo!オークションのウォッチリストを取得し、残り時間の短い順に並べて
Google Apps Script 経由でGoogleドキュメントに書き込むエントリーポイント。

ドキュメントには商品名だけを書き出す(残り時間・リンクは含めない)。
DOC_URL を設定した場合は、そのドキュメントの一番上に
「見出し(終了日) + 商品名リスト」を追記する(過去の内容はそのまま下に残る)。
DOC_URL が未設定の場合は、実行のたびに新規ドキュメントを作成する。

使い方:
    python src/main.py            通常実行
    python src/main.py --dry-run  ドキュメントは作らず、内容を標準出力に表示するだけ
    python src/main.py --save-html  取得した各ページの生HTMLを debug_page_N.html に保存
                                     (スクレイピングが失敗するようになった時の調査用)
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

import requests
from dotenv import load_dotenv

from yahoo_watchlist import AuthError, WatchlistItem, fetch_watchlist

HEADING_SUFFIX = "ヤフオク"


def build_heading(earliest: WatchlistItem, now: dt.datetime) -> str:
    end_dt = now + dt.timedelta(seconds=earliest.remaining_seconds or 0)
    return f"{end_dt.year}年 {end_dt.month}月 {end_dt.day}日 {HEADING_SUFFIX}"


def sort_key(item: WatchlistItem) -> int:
    # 残り時間が解析できなかったアイテムは末尾に回す
    return item.remaining_seconds if item.remaining_seconds is not None else sys.maxsize


def post_to_apps_script(
    url: str, token: str, heading: str, items: list[WatchlistItem], doc_url: str
) -> dict:
    payload = {
        "token": token,
        "title": heading,
        "heading": heading,
        "items": [{"name": item.name} for item in items],
    }
    if doc_url:
        payload["docUrl"] = doc_url
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="ドキュメントを作成せず内容を表示するだけ")
    parser.add_argument("--save-html", action="store_true", help="取得したHTMLをデバッグ用に保存する")
    args = parser.parse_args()

    load_dotenv()
    cookie = os.environ.get("YAHOO_COOKIE", "").strip()
    apps_script_url = os.environ.get("APPS_SCRIPT_URL", "").strip()
    apps_script_token = os.environ.get("APPS_SCRIPT_TOKEN", "").strip()
    doc_url = os.environ.get("DOC_URL", "").strip()

    if not cookie:
        print("エラー: .env の YAHOO_COOKIE が設定されていません。", file=sys.stderr)
        return 1
    if not args.dry_run and (not apps_script_url or not apps_script_token):
        print("エラー: .env の APPS_SCRIPT_URL / APPS_SCRIPT_TOKEN が設定されていません。", file=sys.stderr)
        return 1

    try:
        items = fetch_watchlist(cookie, save_html=args.save_html)
    except AuthError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    except requests.RequestException as e:
        print(f"エラー: Yahoo!オークションへのアクセスに失敗しました: {e}", file=sys.stderr)
        return 1

    if not items:
        print("ウォッチリストにアイテムが見つかりませんでした。"
              "--save-html を付けて実行し、debug_page_1.html を確認してください。", file=sys.stderr)
        return 1

    items.sort(key=sort_key)

    now = dt.datetime.now()
    heading = build_heading(items[0], now)

    print(f"取得件数: {len(items)}件")
    print(f"見出し/タイトル: {heading}")
    for i, item in enumerate(items, start=1):
        print(f"  {i}. {item.name}")

    if args.dry_run:
        print("\n--dry-run のためドキュメントは作成していません。")
        return 0

    result = post_to_apps_script(apps_script_url, apps_script_token, heading, items, doc_url)
    if not result.get("ok"):
        print(f"エラー: Apps Script側でエラーが発生しました: {result.get('error')}", file=sys.stderr)
        return 1

    print(f"\n書き込みました: {result.get('url')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
