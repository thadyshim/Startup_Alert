import requests
from bs4 import BeautifulSoup
import json
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from anthropic import Anthropic

SEEN_FILE = "seen.json"

KEYWORDS = [
"창업","스타트업","예비창업",
"창업지원","사업화","창업패키지",
"장년창업","중장년"
]

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def load_seen():
    if os.path.exists(SEEN_FILE):
        return json.load(open(SEEN_FILE))
    return {}


def save_seen(data):
    json.dump(data, open(SEEN_FILE,"w"))


def clean_seen(data):

    limit = datetime.now() - timedelta(days=7)

    cleaned={}

    for k,v in data.items():

        if datetime.fromisoformat(v) > limit:
            cleaned[k]=v

    return cleaned


def crawl_kstartup():

    url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"

    r=requests.get(url,timeout=20)
    soup=BeautifulSoup(r.text,"html.parser")

    results=[]

    for a in soup.select("a"):

        title=a.get_text(strip=True)

        if len(title)<10:
            continue

        if any(k in title for k in KEYWORDS):

            link=a.get("href")

            if link and not link.startswith("http"):
                link="https://www.k-startup.go.kr"+link

            results.append({
                "title":title,
                "link":link,
                "source":"KSTARTUP"
            })

    return results


def crawl_bizinfo():

    url="https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"

    r=requests.get(url,timeout=20)
    soup=BeautifulSoup(r.text,"html.parser")

    results=[]

    for a in soup.select("a"):

        title=a.get_text(strip=True)

        if len(title)<10:
            continue

        if any(k in title for k in KEYWORDS):

            link=a.get("href")

            if link and not link.startswith("http"):
                link="https://www.bizinfo.go.kr"+link

            results.append({
                "title":title,
                "link":link,
                "source":"BIZINFO"
            })

    return results


def filter_new(items):

    seen=clean_seen(load_seen())
    new=[]

    for i in items:

        uid=i["title"]

        if uid not in seen:

            new.append(i)
            seen[uid]=datetime.now().isoformat()

    save_seen(seen)

    return new


def ai_rank(items):

    if not items:
        return []

    text="\n".join([i["title"] for i in items])

    prompt=f"""
다음 창업 지원사업 제목을 분석해서

지원금 규모
선정 가능성
중장년 창업 적합도

를 기준으로 상위 5개만 추천해라.

{text}
"""

    r=client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=500,
        messages=[{"role":"user","content":prompt}]
    )

    return r.content[0].text


def send_email(items,analysis):

    body=""

    for i in items:

        body+=f"""
{i['title']}
출처:{i['source']}
{i['link']}

"""

    body+=f"""

====================

AI 추천 분석

{analysis}
"""

    if not items:
        body="오늘 감지된 창업 공고 없음"

    msg=MIMEText(body)

    msg["Subject"]=f"창업 공고 레이더 {len(items)}건"

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

    items=[]

    items+=crawl_kstartup()
    items+=crawl_bizinfo()

    items=filter_new(items)

    analysis=ai_rank(items)

    send_email(items,analysis)


if __name__=="__main__":
    main()
