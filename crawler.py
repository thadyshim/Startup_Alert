import requests
from bs4 import BeautifulSoup
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime

print("===== Startup Radar =====")
print("Start:", datetime.now())

items = []

# ------------------------
# KSTARTUP 크롤링
# ------------------------

def crawl_kstartup():

    url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"

    r = requests.get(url,timeout=20)

    soup = BeautifulSoup(r.text,"html.parser")

    rows = soup.select("table tbody tr")

    print("KStartup rows:",len(rows))

    for row in rows:

        cols = row.find_all("td")

        if len(cols) < 2:
            continue

        title = cols[1].get_text(strip=True)

        link = "https://www.k-startup.go.kr"

        items.append({
            "title":title,
            "link":link,
            "source":"KStartup"
        })


# ------------------------
# BIZINFO 크롤링
# ------------------------

def crawl_bizinfo():

    url="https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"

    r=requests.get(url,timeout=20)

    soup=BeautifulSoup(r.text,"html.parser")

    rows=soup.select("table tbody tr")

    print("Bizinfo rows:",len(rows))

    for row in rows:

        cols=row.find_all("td")

        if len(cols)<2:
            continue

        title=cols[1].get_text(strip=True)

        link="https://www.bizinfo.go.kr"

        items.append({
            "title":title,
            "link":link,
            "source":"Bizinfo"
        })


crawl_kstartup()
crawl_bizinfo()

print("Total collected:",len(items))


# ------------------------
# 점수 필터
# ------------------------

KEYWORDS={
"창업":5,
"스타트업":5,
"예비창업":6,
"초기창업":6,
"창업기업":5,
"패키지":4,
"TIPS":4,
"액셀러레이팅":4,
"소셜벤처":4,
"중장년":4,
"AI":3,
"헬스케어":3
}

def score(title):

    s=0

    for k,v in KEYWORDS.items():

        if k in title:

            s+=v

    return s


scored=[]

for i in items:

    s=score(i["title"])

    if s>0:

        i["score"]=s

        scored.append(i)

print("After scoring:",len(scored))


# ------------------------
# 중복 제거
# ------------------------

unique={}

for i in scored:

    unique[i["title"]]=i

results=list(unique.values())


# ------------------------
# 점수 정렬
# ------------------------

results=sorted(results,key=lambda x:x["score"],reverse=True)


# ------------------------
# 최대 10개
# ------------------------

results=results[:10]

print("Final results:",len(results))


# ------------------------
# 메일 내용
# ------------------------

if len(results)==0:

    content="오늘 감지된 창업 공고 없음"

else:

    lines=[]

    for r in results:

        lines.append(
            f"[{r['source']}] {r['title']}\n{r['link']}\n"
        )

    content="\n".join(lines)


# ------------------------
# 이메일 발송
# ------------------------

GMAIL_USER=os.environ.get("GMAIL_USER")
GMAIL_PASS=os.environ.get("GMAIL_PASS")
NOTIFY_EMAIL=os.environ.get("NOTIFY_EMAIL")

msg=MIMEText(content)

msg["Subject"]="Startup Radar"

msg["From"]=GMAIL_USER
msg["To"]=NOTIFY_EMAIL

try:

    server=smtplib.SMTP_SSL("smtp.gmail.com",465)

    server.login(GMAIL_USER,GMAIL_PASS)

    server.sendmail(GMAIL_USER,NOTIFY_EMAIL,msg.as_string())

    server.quit()

    print("Email sent")

except Exception as e:

    print("Email error:",e)

print("===== Done =====")
