import requests
from bs4 import BeautifulSoup
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import os

print("===== Startup Alert Crawler =====")
print("Start:", datetime.now())

KEYWORDS = [
    "창업",
    "스타트업",
    "AI",
    "데이터",
    "헬스케어",
    "소셜벤처",
    "중장년"
]

items = []

def crawl_kstartup():
    print("Crawling KStartup...")
    url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
    r = requests.get(url, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    rows = soup.select("table tbody tr")

    print("KStartup rows:", len(rows))

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        title = cols[1].get_text(strip=True)
        link = "https://www.k-startup.go.kr"

        items.append({
            "title": title,
            "link": link,
            "source": "KStartup"
        })


def crawl_bizinfo():
    print("Crawling Bizinfo...")
    url = "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"
    r = requests.get(url, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    rows = soup.select("table tbody tr")

    print("Bizinfo rows:", len(rows))

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        title = cols[1].get_text(strip=True)

        items.append({
            "title": title,
            "link": "https://www.bizinfo.go.kr",
            "source": "Bizinfo"
        })


crawl_kstartup()
crawl_bizinfo()

print("Total collected:", len(items))

# 키워드 필터
filtered = []

for i in items:
    title = i["title"]

    if any(k in title for k in KEYWORDS):
        filtered.append(i)

print("After keyword filter:", len(filtered))

# 중복 제거
unique = {}
for i in filtered:
    unique[i["title"]] = i

results = list(unique.values())

print("After duplicate removal:", len(results))

# 메일 내용 생성
if len(results) == 0:
    content = "오늘 감지된 창업 관련 공고가 없습니다."
else:
    lines = []
    for r in results[:20]:
        lines.append(f"[{r['source']}] {r['title']}\n{r['link']}\n")

    content = "\n".join(lines)

print("Preparing email...")

# 이메일 발송
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASS = os.environ.get("GMAIL_PASS")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL")

msg = MIMEText(content)
msg["Subject"] = "Startup Support Alerts"
msg["From"] = GMAIL_USER
msg["To"] = NOTIFY_EMAIL

try:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(GMAIL_USER, GMAIL_PASS)
    server.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())
    server.quit()
    print("Email sent successfully")
except Exception as e:
    print("Email send error:", e)

print("===== Done =====")
