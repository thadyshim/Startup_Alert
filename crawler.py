import requests
import smtplib
import os
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from xml.etree import ElementTree as ET

print("===== Startup Radar =====")
print("Start:", datetime.now())

items = []

# -----------------------------
# RSS 수집 함수
# -----------------------------

def crawl_rss(url, source):

    try:

        r = requests.get(url, timeout=20)

        root = ET.fromstring(r.content)

        for item in root.iter("item"):

            title = item.find("title").text
            link = item.find("link").text
            pubDate = item.find("pubDate").text

            items.append({
                "title": title,
                "link": link,
                "date": pubDate,
                "source": source
            })

    except Exception as e:

        print(source, "error:", e)


# -----------------------------
# 수집 대상
# -----------------------------

crawl_rss(
    "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do?crtfcKey=sample",
    "Bizinfo"
)

crawl_rss(
    "https://www.k-startup.go.kr/rss/notice.do",
    "KStartup"
)

print("Collected:", len(items))


# -----------------------------
# 키워드 점수
# -----------------------------

KEYWORDS = {
    "창업": 5,
    "스타트업": 5,
    "예비창업": 6,
    "초기창업": 6,
    "창업기업": 5,
    "패키지": 4,
    "액셀러레이팅": 4,
    "TIPS": 5,
    "소셜벤처": 4,
    "중장년": 4,
    "AI": 3,
    "헬스케어": 3
}


def score(title):

    s = 0

    for k,v in KEYWORDS.items():

        if k in title:

            s += v

    return s


scored = []

for i in items:

    s = score(i["title"])

    if s > 0:

        i["score"] = s
        scored.append(i)

print("After scoring:", len(scored))


# -----------------------------
# 중복 제거
# -----------------------------

unique = {}

for i in scored:

    unique[i["title"]] = i

results = list(unique.values())


# -----------------------------
# 점수 정렬
# -----------------------------

results = sorted(results, key=lambda x: x["score"], reverse=True)


# -----------------------------
# 최대 10개
# -----------------------------

results = results[:10]

print("Final results:", len(results))


# -----------------------------
# 이전 공고 기록
# -----------------------------

history_file = "history.json"

if os.path.exists(history_file):

    with open(history_file) as f:

        history = json.load(f)

else:

    history = []


new_items = []

for r in results:

    if r["title"] not in history:

        new_items.append(r)


print("New items:", len(new_items))


# -----------------------------
# history 업데이트
# -----------------------------

for r in results:

    history.append(r["title"])

history = list(set(history))

with open(history_file,"w") as f:

    json.dump(history,f)


# -----------------------------
# 메일 내용
# -----------------------------

if len(new_items) == 0:

    content = "오늘 새 창업 공고 없음"

else:

    lines = []

    for r in new_items:

        lines.append(
            f"[{r['source']}] {r['title']}\n{r['link']}\n"
        )

    content = "\n".join(lines)


# -----------------------------
# 메일 발송
# -----------------------------

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASS = os.environ.get("GMAIL_PASS")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL")

msg = MIMEText(content)

msg["Subject"] = "Startup Radar"
msg["From"] = GMAIL_USER
msg["To"] = NOTIFY_EMAIL


try:

    server = smtplib.SMTP_SSL("smtp.gmail.com",465)

    server.login(GMAIL_USER,GMAIL_PASS)

    server.sendmail(GMAIL_USER,NOTIFY_EMAIL,msg.as_string())

    server.quit()

    print("Email sent")

except Exception as e:

    print("Email error:",e)


print("===== Done =====")
