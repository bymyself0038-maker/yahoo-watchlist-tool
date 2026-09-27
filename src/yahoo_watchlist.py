"""Yahoo!オークションの「ウォッチリスト」ページを取得・解析するモジュール。

注意:
  auctions.yahoo.co.jp のHTML構造は予告なく変わることがある。
  ここでのセレクタは長年 Yahoo!オークションの一覧系ページ(検索結果/カテゴリ/
  ウォッチリスト)で共通して使われてきた "Product" 系のBEMクラス名を基準にしている。
  もし fetch_watchlist() がアイテムを1件も取れなくなったら、
  main.py を --save-html 付きで実行して保存されたHTMLを確認し、
  下記の *_SELECTORS を実際のマークアップに合わせて調整すること。
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://auctions.yahoo.co.jp"
WATCHLIST_URL = f"{BASE_URL}/my/watchlist"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# 調整が必要になったらまずここを見直す
ITEM_SELECTORS = ["li.Product", "div.Product", "li[class*='Product']"]
NAME_SELECTORS = [".Product__titleLink", ".Product__title a", ".Product__title", "a.Product__titleLink"]
TIME_SELECTORS = [".Product__time", ".Product__closetime", ".Product__remain", "time"]
LOGIN_MARKERS = ["ログイン - Yahoo! JAPAN", "id.rakuten.co.jp", "login.yahoo.co.jp"]


class AuthError(RuntimeError):
    """Cookieが無効/期限切れでログインページにリダイレクトされた場合。"""


@dataclass
class WatchlistItem:
    name: str
    url: str
    remaining_text: str
    remaining_seconds: Optional[int]  # 解析できなければ None


def _first_match(el, selectors: list[str]):
    for sel in selectors:
        found = el.select_one(sel)
        if found is not None:
            return found
    return None


def _looks_like_login_page(soup: BeautifulSoup, final_url: str) -> bool:
    if "login" in final_url:
        return True
    title = soup.title.get_text() if soup.title else ""
    return any(marker in title for marker in LOGIN_MARKERS)


def parse_remaining_seconds(text: str) -> Optional[int]:
    """「残り3日20時間」のような文字列を秒数に変換する。解析できなければ None。"""
    text = text.strip()
    if not text:
        return None
    if "まもなく" in text:
        return 0
    if "終了" in text and not re.search(r"\d", text):
        # 「終了しました」等、すでに終わっている出品
        return None

    day = re.search(r"(\d+)\s*日", text)
    hour = re.search(r"(\d+)\s*時間", text)
    minute = re.search(r"(\d+)\s*分", text)
    second = re.search(r"(\d+)\s*秒", text)

    if not any([day, hour, minute, second]):
        return None

    total = 0
    if day:
        total += int(day.group(1)) * 86400
    if hour:
        total += int(hour.group(1)) * 3600
    if minute:
        total += int(minute.group(1)) * 60
    if second:
        total += int(second.group(1))
    return total


def _parse_page(html: str, page_url: str) -> list[WatchlistItem]:
    soup = BeautifulSoup(html, "html.parser")

    if _looks_like_login_page(soup, page_url):
        raise AuthError(
            "ログインページにリダイレクトされました。YAHOO_COOKIE が無効・期限切れの可能性があります。"
            "ブラウザで再ログインし、Cookieを取得し直してください。"
        )

    items: list[WatchlistItem] = []
    nodes = []
    for sel in ITEM_SELECTORS:
        nodes = soup.select(sel)
        if nodes:
            break

    for node in nodes:
        name_el = _first_match(node, NAME_SELECTORS)
        if name_el is None:
            continue
        name = name_el.get_text(strip=True)
        href = name_el.get("href") or ""
        url = urljoin(BASE_URL, href)

        time_el = _first_match(node, TIME_SELECTORS)
        remaining_text = time_el.get_text(strip=True) if time_el is not None else ""
        remaining_seconds = parse_remaining_seconds(remaining_text)

        if not name:
            continue

        items.append(
            WatchlistItem(
                name=name,
                url=url,
                remaining_text=remaining_text,
                remaining_seconds=remaining_seconds,
            )
        )

    return items


def fetch_watchlist(
    cookie: str,
    max_pages: int = 20,
    request_interval_sec: float = 1.0,
    save_html: bool = False,
) -> list[WatchlistItem]:
    """全ページ分のウォッチリストを取得する。空のページに到達したら打ち切り。"""
    session = requests.Session()
    session.headers.update(
        {
            "Cookie": cookie,
            "User-Agent": USER_AGENT,
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        }
    )

    all_items: list[WatchlistItem] = []

    for page in range(1, max_pages + 1):
        url = WATCHLIST_URL if page == 1 else f"{WATCHLIST_URL}?page={page}"
        resp = session.get(url, timeout=30)
        resp.raise_for_status()

        if save_html:
            with open(f"debug_page_{page}.html", "w", encoding="utf-8") as f:
                f.write(resp.text)

        page_items = _parse_page(resp.text, resp.url)
        if not page_items:
            break

        all_items.extend(page_items)

        if page < max_pages:
            time.sleep(request_interval_sec)

    return all_items
