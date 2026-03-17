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
    "예비창업",
    "초기창업",
    "창업기업",
    "창업지원"
]

HIGH_VALUE = [
    "패키지",
    "액셀러레이팅",
    "TIPS",
    "소셜벤처",
    "기술창업",
    "중장년"
]

items = []


def crawl_kstartup():
    print("Crawling KStartup")

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

        items.append({
            "title": title,
            "link": "https://www.k-startup.go.kr",
            "source": "KStartup"
        })


def crawl_bizinfo():
    print("Crawling Bizinfo")

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


# 1️⃣ 창업 관련 필터
filtered = []

for i in items:
    title = i["title"]

    if any(k in title for k in KEYWORDS):
        filtered.append(i)

print("After keyword filter:", len(filtered))


# 2️⃣ 중복 제거
unique = {i["title"]: i for i in filtered}
results = list(unique.values())

print("After duplicate removal:", len(results))


# 3️⃣ 중요사업 우선순위
def score(item):
    title = item["title"]
    return sum(k in title for k in HIGH_VALUE)

results = sorted(results, key=score, reverse=True)


# 4️⃣ 최대 10개만
results = results[:10]

print("Final results:", len(results))


# 메일 내용 생성
if len(results) == 0:
    content = "오늘 감지된 창업 관련 공고가 없습니다."
else:

    lines = []
    for r in results:

        lines.append(
            f"[{r['source']}] {r['title']}\n{r['link']}\n"
        )

    content = "\n".join(lines)


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

    print("Email sent")

except Exception as e:
    print("Email error:", e)

print("===== Done =====")
