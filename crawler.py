import requests
from bs4 import BeautifulSoup
import smtplib
import os
from email.mime.text import MIMEText

print("Start crawling")

items = []


# -------------------
# Bizinfo (기업마당)
# -------------------

try:

    url = "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"

    r = requests.get(url, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    rows = soup.select("table tbody tr")

    print("Bizinfo rows:", len(rows))

    for row in rows[:30]:

        title_tag = row.select_one("td a")

        if not title_tag:
            continue

        title = title_tag.text.strip()
        link = "https://www.bizinfo.go.kr" + title_tag["href"]

        items.append({
            "title": title,
            "link": link,
            "source": "Bizinfo"
        })

except Exception as e:

    print("Bizinfo error:", e)



# -------------------
# K-Startup
# -------------------

try:

    url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"

    r = requests.get(url, timeout=20)

    soup = BeautifulSoup(r.text, "html.parser")

    rows = soup.select("div.list-item")

    print("KStartup rows:", len(rows))

    for row in rows[:30]:

        title_tag = row.select_one("a")

        if not title_tag:
            continue

        title = title_tag.text.strip()
        link = "https://www.k-startup.go.kr" + title_tag["href"]

        items.append({
            "title": title,
            "link": link,
            "source": "KStartup"
        })

except Exception as e:

    print("KStartup error:", e)



print("Total collected:", len(items))


# -------------------
# 키워드 필터
# -------------------

KEYWORDS = [
"창업",
"스타트업",
"예비창업",
"초기창업",
"창업기업",
"패키지",
"TIPS",
"액셀러레이팅",
"중장년"
]


results = []

for item in items:

    for k in KEYWORDS:

        if k in item["title"]:

            results.append(item)
            break



print("Filtered:", len(results))


# 중복 제거
unique = {i["title"]: i for i in results}

results = list(unique.values())


# 최대 10개
results = results[:10]


print("Final:", len(results))


# -------------------
# 메일 내용
# -------------------

if len(results) == 0:

    content = "오늘 감지된 창업 공고 없음"

else:

    lines = []

    for r in results:

        lines.append(
            f"[{r['source']}] {r['title']}\n{r['link']}\n"
        )

    content = "\n".join(lines)



# -------------------
# 메일 발송
# -------------------

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_PASS"]
NOTIFY_EMAIL = os.environ["NOTIFY_EMAIL"]

msg = MIMEText(content)

msg["Subject"] = "Startup Radar"
msg["From"] = GMAIL_USER
msg["To"] = NOTIFY_EMAIL

server = smtplib.SMTP_SSL("smtp.gmail.com",465)

server.login(GMAIL_USER,GMAIL_PASS)

server.sendmail(GMAIL_USER,NOTIFY_EMAIL,msg.as_string())

server.quit()

print("Email sent")
