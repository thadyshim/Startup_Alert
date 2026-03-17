import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json
import hashlib
import re
from datetime import datetime
import anthropic

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_PASS"]
NOTIFY_EMAIL = os.environ["NOTIFY_EMAIL"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]

SEEN_FILE = "seen_ids.json"

# MindBridge 프로젝트 기준
MINDBRIDGE_PROFILE = """
MindBridge는 AI 기반 인지훈련 / 디지털 헬스케어 서비스입니다.
노인 치매 예방과 인지 훈련을 위한 소프트웨어 플랫폼입니다.

적합 사업
- 예비창업패키지
- 초기창업패키지
- 창업도약패키지
- 소셜벤처
- AI / 디지털헬스 / ICT
"""

HIGH_VALUE_PROGRAMS = [
    "예비창업패키지",
    "초기창업패키지",
    "창업도약패키지",
    "소셜벤처",
    "TIPS",
    "중장년 기술창업",
    "신사업창업사관학교"
]

FUNDING_KEYWORDS = {
    "5천": 50000000,
    "5000": 50000000,
    "1억": 100000000,
    "2억": 200000000,
    "3억": 300000000
}

INCLUDE_KEYWORDS = [
    "창업", "스타트업", "벤처", "AI", "ICT",
    "디지털", "헬스케어", "소셜벤처",
    "R&D", "기술개발"
]

EXCLUDE_KEYWORDS = [
    "농업", "식품", "수출", "프랜차이즈"
]


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


def keyword_filter(title):

    for kw in EXCLUDE_KEYWORDS:
        if kw in title:
            return False

    for kw in INCLUDE_KEYWORDS:
        if kw in title:
            return True

    return False


def high_value_filter(title):

    for kw in HIGH_VALUE_PROGRAMS:
        if kw in title:
            return True

    return False


def estimate_funding(title):

    for key, value in FUNDING_KEYWORDS.items():
        if key in title:
            return value

    return 0


def detect_deadline(title):

    match = re.search(r'(\d{1,2})월\s*(\d{1,2})일', title)

    if not match:
        return None

    month = int(match.group(1))
    day = int(match.group(2))

    year = datetime.now().year

    deadline = datetime(year, month, day)

    delta = (deadline - datetime.now()).days

    if delta <= 3:
        return "D-3"

    if delta <= 7:
        return "D-7"

    return None


def ai_filter(items):

    if not items:
        return []

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    titles = "\n".join(
        [f"{i+1}. {item['title']}" for i, item in enumerate(items)]
    )

    prompt = f"""
다음 창업 공고 중 MindBridge 프로젝트에 적합한 번호만 선택하세요.

{MINDBRIDGE_PROFILE}

공고 목록
{titles}

응답 예시
1,3

없으면
없음
"""

    try:

        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        response = message.content[0].text.strip()

        if response == "없음":
            return []

        idx = [int(x.strip())-1 for x in response.split(",") if x.strip().isdigit()]

        return [items[i] for i in idx if i < len(items)]

    except Exception as e:

        print("AI 오류", e)

        return items


def crawl_kstartup():

    results = []

    try:

        url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"

        r = requests.get(url, timeout=10)

        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.select("a[href]")[:80]:

            title = a.get_text(strip=True)

            href = a.get("href", "")

            if len(title) > 10:

                if href.startswith("/"):
                    href = "https://www.k-startup.go.kr" + href

                if href.startswith("http"):

                    results.append({
                        "title": title,
                        "url": href,
                        "source": "K-Startup"
                    })

    except Exception as e:

        print("kstartup error", e)

    return results


def crawl_mss():

    results = []

    try:

        url = "https://www.mss.go.kr/site/smba/ex/bbs/List.do?cbIdx=86"

        r = requests.get(url, timeout=10)

        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.select("td.subject a"):

            title = a.get_text(strip=True)

            href = a.get("href", "")

            if href.startswith("/"):
                href = "https://www.mss.go.kr" + href

            results.append({
                "title": title,
                "url": href,
                "source": "중소벤처기업부"
            })

    except Exception as e:

        print("mss error", e)

    return results


def crawl_bizinfo():

    results = []

    try:

        url = "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"

        r = requests.get(url, timeout=10)

        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.select("td.tit a"):

            title = a.get_text(strip=True)

            href = a.get("href", "")

            if href.startswith("/"):
                href = "https://www.bizinfo.go.kr" + href

            results.append({
                "title": title,
                "url": href,
                "source": "기업마당"
            })

    except Exception as e:

        print("bizinfo error", e)

    return results


def send_email(new_items, filtered_items):

    if not new_items:
        return

    subject = f"[MindBridge 창업공고] 추천 {len(filtered_items)}건"

    body = "추천 공고\n"
    body += "="*40 + "\n\n"

    for item in filtered_items:

        funding = estimate_funding(item["title"])
        deadline = detect_deadline(item["title"])

        body += f"[{item['source']}] {item['title']}\n"

        if funding > 0:
            body += f"지원금 추정: {funding:,}원\n"

        if deadline:
            body += f"마감 임박: {deadline}\n"

        body += f"{item['url']}\n\n"

    msg = MIMEMultipart()

    msg["From"] = GMAIL_USER
    msg["To"] = NOTIFY_EMAIL
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:

        server.login(GMAIL_USER, GMAIL_PASS)

        server.send_message(msg)


def main():

    seen = load_seen()

    all_items = []

    all_items += crawl_kstartup()
    all_items += crawl_mss()
    all_items += crawl_bizinfo()

    new_items = []

    for item in all_items:

        uid = make_id(item["title"], item["url"])

        if uid not in seen:

            new_items.append(item)

            seen.add(uid)

    kw = [i for i in new_items if keyword_filter(i["title"])]

    hv = [i for i in kw if high_value_filter(i["title"])]

    ai = ai_filter(hv)

    send_email(new_items, ai)

    save_seen(seen)


if __name__ == "__main__":
    main()
