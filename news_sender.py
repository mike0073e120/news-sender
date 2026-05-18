import os
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
import html
import json
import time
from datetime import datetime

# --- Load .env manually (no dotenv needed) ---
_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

LINE_TOKEN   = os.environ.get("LINE_CHANNEL_TOKEN", "")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "")

YAHOO_RSS = "https://tw.news.yahoo.com/rss/"
TECH_RSS = "https://technews.tw/feed/"


def fetch_rss(url, max_items=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        items = []
        for item in root.iter("item"):
            if len(items) >= max_items:
                break
            title_el = item.find("title")
            link_el  = item.find("link")
            if title_el is not None and title_el.text:
                title = html.unescape(title_el.text.strip())
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0].strip()
                if len(title) > 75:
                    title = title[:73] + "…"
                link = (link_el.text or "").strip() if link_el is not None else ""
                items.append((title, link))
        return items
    except Exception as e:
        print(f"  RSS 讀取失敗: {e}")
        return []


def send_line(message):
    if not LINE_TOKEN or not LINE_USER_ID:
        print("  錯誤: 未設定 LINE_CHANNEL_TOKEN 或 LINE_USER_ID")
        return -1
    payload = json.dumps({
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=payload
    )
    req.add_header("Authorization", f"Bearer {LINE_TOKEN}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"  LINE HTTP {e.code}: {body}")
        return e.code
    except Exception as e:
        print(f"  LINE 發送失敗: {e}")
        return -1


def shorten_url(url):
    if not url:
        return ""
    try:
        api = "https://tinyurl.com/api-create.php?url=" + urllib.parse.quote(url, safe="")
        req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode().strip()
    except Exception:
        return url


def build_message(icon, heading, date, items, footer=""):
    lines = [f"{icon} {heading}", date, "─" * 20]
    for i, (title, link) in enumerate(items, 1):
        lines.append(f"{i:2}. {title}")
        if link:
            lines.append(f"    {shorten_url(link)}")
        lines.append("")
    if footer:
        lines.append(footer)
    return "\n".join(lines)


def main():
    today = datetime.now().strftime("%Y/%m/%d")

    # --- 科技新報十大新聞 ---
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 抓取 科技新報…")
    tech_items = fetch_rss(TECH_RSS, 10)
    if tech_items:
        msg = build_message(
            "💻", "科技十大新聞", today, tech_items,
            footer="（來源：科技新報）"
        )
        code = send_line(msg)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 科技新聞 → LINE: {code}")
    else:
        print("  科技新聞取得失敗，略過")

    time.sleep(3)

    # --- 電池相關新聞 ---
    BATTERY_KEYWORDS = {"電池", "鋰電池", "固態電池", "充電", "儲能", "磷酸鐵鋰", "三元鋰", "超級電容", "燃料電池"}
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 過濾電池相關新聞…")
    all_tech = fetch_rss(TECH_RSS, 50)
    battery_items = [
        (t, l) for t, l in all_tech
        if any(kw in t for kw in BATTERY_KEYWORDS)
    ]
    if battery_items:
        msg = build_message(
            "🔋", "電池相關新聞", today, battery_items,
            footer="（來源：科技新報）"
        )
        code = send_line(msg)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 電池新聞 → LINE: {code}")
    else:
        print("  今日無電池相關新聞")


if __name__ == "__main__":
    main()
