import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import smtplib
from email.mime.text import MIMEText

KEYWORDS = [
"창업","스타트업","예비창업",
"창업지원","사업화","창업패키지"
]

URLS = {
"KSTARTUP":"https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do",
"BIZINFO":"https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"
}

SEEN_FILE="seen.json"


def load_seen():
    if os.path.exists(SEEN_FILE):
        return set(json.load(open(SEEN_FILE)))
    return set()


def save_seen(data):
    json.dump(list(data),open(SEEN_FILE,"w"))


def crawl():

    results=[]

    for name,url in URLS.items():

        res=requests.get(url,timeout=20)
        soup=BeautifulSoup(res.text,"html.parser")

        for a in soup.select("a"):

            title=a.get_text(strip=True)

            if len(title)<10:
                continue

            if any(k in title for k in KEYWORDS):

                link=a.get("href")

                if link and not link.startswith("http"):
                    link=url+link

                results.append({
                    "title":title,
                    "link":link,
                    "source":name
                })

    return results


def filter_new(items):

    seen=load_seen()
    new=[]

    for i in items:

        uid=i["title"]

        if uid not in seen:

            new.append(i)
            seen.add(uid)

    save_seen(seen)

    return new


def send_email(items):

    body=""

    for i in items:

        body+=f"""
{i['title']}
출처:{i['source']}
{i['link']}

"""

    msg=MIMEText(body)

    msg["Subject"]=f"창업 공고 {len(items)}건"
    msg["From"]=os.environ["GMAIL"]
    msg["To"]=os.environ["GMAIL"]

    s=smtplib.SMTP_SSL("smtp.gmail.com",465)

    s.login(
        os.environ["GMAIL"],
        os.environ["APP_PASSWORD"]
    )

    s.send_message(msg)
    s.quit()


def main():

    items=crawl()
    items=filter_new(items)

    if not items:
        items=[{
            "title":"오늘 감지된 창업 공고 없음",
            "link":"",
            "source":"system"
        }]

    send_email(items)


if __name__=="__main__":
    main()
