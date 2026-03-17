import requests
import smtplib
import os
from email.mime.text import MIMEText

print("Startup Radar API mode")

items = []


# ------------------------
# Bizinfo API
# ------------------------

try:

    url = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do?crtfcKey=sample&dataType=json&pageNo=1&numOfRows=50"

    r = requests.get(url, timeout=20)

    data = r.json()

    for row in data["jsonArray"]:

        title = row["pblancNm"]
        link = "https://www.bizinfo.go.kr"

        items.append({
            "title": title,
            "link": link,
            "source": "Bizinfo"
        })

except Exception as e:

    print("Bizinfo API error:", e)



# ------------------------
# KStartup API
# ------------------------

try:

    url = "https://apis.data.go.kr/B552735/kstartupService/getAnnouncementList?serviceKey=sample&pageNo=1&numOfRows=50"

    r = requests.get(url, timeout=20)

    data = r.json()

    rows = data["response"]["body"]["items"]["item"]

    for row in rows:

        title = row["title"]
        link = row["detailUrl"]

        items.append({
            "title": title,
            "link": link,
            "source": "KStartup"
        })

except Exception as e:

    print("KStartup API error:", e)



print("Collected:", len(items))


# ------------------------
# 키워드 필터
# ------------------------

KEYWORDS = [
"창업",
"스타트업",
"예비창업",
"초기창업",
"창업기업",
"패키지",
"TIPS",
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


if len(results) == 0:

    content = "오늘 감지된 창업 공고 없음"

else:

    lines = []

    for r in results:

        lines.append(
            f"[{r['source']}] {r['title']}\n{r['link']}\n"
        )

    content = "\n".join(lines)



# ------------------------
# 메일 발송
# ------------------------

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
