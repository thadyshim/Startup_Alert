import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json
import hashlib
from datetime import datetime

GMAIL_USER    = os.environ["GMAIL_USER"]
GMAIL_PASS    = os.environ["GMAIL_PASS"]
NOTIFY_EMAIL  = os.environ["NOTIFY_EMAIL"]

SEEN_FILE = "seen_ids.json"

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

def crawl_kstartup():
    results = []
    try:
        url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href]")[:50]:
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if len(title) > 10 and any(k in title for k in ["창업", "지원", "모집", "공고"]):
                if href.startswith("/"):
                    href = "https://www.k-startup.go.kr" + href
                if href.startswith("http"):
                    results.append({"title": title, "url": href, "source": "창업넷"})
    except Exception as e:
        print(f"창업넷 오류: {e}")
    return results[:10]

def crawl_mss():
    results = []
    try:
        url = "https://www.mss.go.kr/site/smba/ex/bbs/List.do?cbIdx=86"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("td.subject a, td a"):
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if len(title) > 10 and any(k in title for k in ["창업", "지원", "모집", "공고", "스타트업", "벤처"]):
                if href.startswith("/"):
                    href = "https://www.mss.go.kr" + href
                elif not href.startswith("http"):
                    continue
                results.append({"title": title, "url": href, "source": "중소벤처기업부"})
    except Exception as e:
        print(f"중기부 오류: {e}")
    return results[:10]

def crawl_bizinfo():
    results = []
    try:
        url = "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("td.tit a, .tit a, table a"):
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if len(title) > 10:
                if href.startswith("/"):
                    href = "https://www.bizinfo.go.kr" + href
                if href.startswith("http") and "bizinfo" in href:
                    results.append({"title": title, "url": href, "source": "기업마당"})
    except Exception as e:
        print(f"기업마당 오류: {e}")
    return results[:10]

def crawl_seoul():
    results = []
    try:
        url = "https://startup.seoul.go.kr/notice/list"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href]"):
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if len(title) > 10 and any(k in title for k in ["창업", "지원", "모집", "공고"]):
                if href.startswith("/"):
                    href = "https://startup.seoul.go.kr" + href
                if href.startswith("http"):
                    results.append({"title": title, "url": href, "source": "서울시창업포털"})
    except Exception as e:
        print(f"서울시 오류: {e}")
    return results[:10]

def send_email(new_items):
    if not new_items:
        print("새 공고 없음.")
        return

    subject = f"[창업공고 알림] 새 공고 {len(new_items)}건 - {datetime.now().strftime('%Y-%m-%d')}"
    body = f"안녕하세요! 오늘 새로운 창업 지원 공고 {len(new_items)}건을 발견했습니다.\n\n"

    for item in new_items:
        body += f"📌 [{item['source']}] {item['title']}\n"
        body += f"   🔗 {item['url']}\n\n"

    body += "\n---\n창업공고 자동알림 시스템"

    msg = MIMEMultipart()
    msg["From"]    = GMAIL_USER
    msg["To"]      = NOTIFY_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)

    print(f"이메일 발송 완료: {len(new_items)}건")

def main():
    print(f"크롤링 시작: {datetime.now()}")
    seen = load_seen()

    all_items = []
    all_items += crawl_kstartup()
    all_items += crawl_mss()
    all_items += crawl_bizinfo()
    all_items += crawl_seoul()

    print(f"총 {len(all_items)}건 수집")

    new_items = []
    for item in all_items:
        uid = make_id(item["title"], item["url"])
        if uid not in seen:
            new_items.append(item)
            seen.add(uid)

    print(f"새 공고: {len(new_items)}건")
    send_email(new_items)
    save_seen(seen)

if __name__ == "__main__":
    main()
