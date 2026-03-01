import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json
import hashlib
from datetime import datetime

# ── 환경변수에서 Gmail 정보 읽기 ──────────────────────────
GMAIL_USER    = os.environ["GMAIL_USER"]
GMAIL_PASS    = os.environ["GMAIL_PASS"]
NOTIFY_EMAIL  = os.environ["NOTIFY_EMAIL"]

SEEN_FILE = "seen_ids.json"

# ── 이미 본 공고 ID 불러오기 / 저장하기 ───────────────────
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def make_id(title, url):
    return hashlib.md5((title + url).encode()).hexdigest()

# ── 크롤링 대상 사이트 목록 ────────────────────────────────
def crawl_kstartup():
    """창업넷 (k-startup.go.kr) 공고"""
    results = []
    try:
        url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".list-item") or soup.select(".biz-item") or soup.select("li.item")
        for item in items[:20]:
            a = item.find("a")
            if a:
                title = a.get_text(strip=True)
                href = "https://www.k-startup.go.kr" + a.get("href", "")
                if any(k in title for k in ["창업", "지원", "공고", "모집"]):
                    results.append({"title": title, "url": href, "source": "창업넷"})
    except Exception as e:
        print(f"창업넷 크롤링 오류: {e}")
    return results

def crawl_mss():
    """중소벤처기업부 공고"""
    results = []
    try:
        url = "https://www.mss.go.kr/site/smba/ex/bbs/List.do?cbIdx=86"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table tbody tr")
        for row in rows[:15]:
            a = row.find("a")
            if a:
                title = a.get_text(strip=True)
                href = "https://www.mss.go.kr" + a.get("href", "")
                if any(k in title for k in ["창업", "지원", "공고", "모집", "예비창업"]):
                    results.append({"title": title, "url": href, "source": "중소벤처기업부"})
    except Exception as e:
        print(f"중기부 크롤링 오류: {e}")
    return results

def crawl_seoul():
    """서울시 창업포털 공고"""
    results = []
    try:
        url = "https://startup.seoul.go.kr/notice/list"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".board-list li") or soup.select("ul.list li")
        for item in items[:15]:
            a = item.find("a")
            if a:
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = "https://startup.seoul.go.kr" + href
                if title:
                    results.append({"title": title, "url": href, "source": "서울시창업포털"})
    except Exception as e:
        print(f"서울시 크롤링 오류: {e}")
    return results

def crawl_bizinfo():
    """기업마당 (중기부 산하) 지원사업 공고"""
    results = []
    try:
        url = "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table tbody tr")
        for row in rows[:20]:
            a = row.find("a")
            if a:
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.bizinfo.go.kr" + href
                if any(k in title for k in ["창업", "지원", "공고", "모집"]):
                    results.append({"title": title, "url": href, "source": "기업마당"})
    except Exception as e:
        print(f"기업마당 크롤링 오류: {e}")
    return results

# ── 이메일 발송 ────────────────────────────────────────────
def send_email(new_items):
    if not new_items:
        print("새 공고 없음. 이메일 발송 안 함.")
        return

    subject = f"[창업공고 알림] 새 공고 {len(new_items)}건 - {datetime.now().strftime('%Y-%m-%d')}"

    body = f"""
안녕하세요! 오늘 새로운 창업 지원 공고 {len(new_items)}건을 발견했습니다.\n\n
"""
    for item in new_items:
        body += f"📌 [{item['source']}] {item['title']}\n"
        body += f"   🔗 {item['url']}\n\n"

    body += "\n---\nCareBrainBridge 창업공고 자동알림 시스템"

    msg = MIMEMultipart()
    msg["From"]    = GMAIL_USER
    msg["To"]      = NOTIFY_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)

    print(f"이메일 발송 완료: {len(new_items)}건")

# ── 메인 실행 ──────────────────────────────────────────────
def main():
    print(f"크롤링 시작: {datetime.now()}")
    seen = load_seen()

    # 모든 사이트 크롤링
    all_items = []
    all_items += crawl_kstartup()
    all_items += crawl_mss()
    all_items += crawl_seoul()
    all_items += crawl_bizinfo()

    print(f"총 {len(all_items)}건 수집")

    # 새 공고만 필터링
    new_items = []
    for item in all_items:
        uid = make_id(item["title"], item["url"])
        if uid not in seen:
            new_items.append(item)
            seen.add(uid)

    print(f"새 공고: {len(new_items)}건")

    # 이메일 발송
    send_email(new_items)

    # 본 공고 저장
    save_seen(seen)

if __name__ == "__main__":
    main()
