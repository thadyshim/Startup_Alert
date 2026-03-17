import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json
import hashlib
from datetime import datetime
import anthropic

GMAIL_USER    = os.environ["GMAIL_USER"]
GMAIL_PASS    = os.environ["GMAIL_PASS"]
NOTIFY_EMAIL  = os.environ["NOTIFY_EMAIL"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]

SEEN_FILE = "seen_ids.json"

# ── MindBridge 프로젝트 소개 (AI 판단 기준) ────────────────
MINDBRIDGE_PROFILE = """
프로젝트명: MindBridge
분야: 인지훈련, 디지털 헬스케어, 노인/치매 예방, AI 기반 뇌건강 플랫폼
기술: 웹 기반 서비스, AI, 소프트웨어 개발
팀 구성: 공동창업자 3명 (개발자 포함), 무자본 창업 초기 단계
목표: 예비창업패키지, 초기창업패키지, 창업도약패키지, 소셜벤처 지원사업 확보
"""

# ── 고액 창업사업 필터 (5000만원 이상 가능 사업) ───────────
HIGH_VALUE_PROGRAMS = [
    "예비창업패키지",
    "초기창업패키지",
    "창업도약패키지",
    "소셜벤처",
    "TIPS",
    "중장년 기술창업",
    "신사업창업사관학교"
]

# ── 일반 키워드 필터 ─────────────────────────────────────
INCLUDE_KEYWORDS = [
    "예비창업", "초기창업", "창업도약",
    "창업지원", "창업패키지",
    "AI", "인공지능", "ICT", "디지털",
    "헬스케어", "디지털헬스",
    "복지", "노인", "치매",
    "소셜벤처", "사회적기업",
    "스타트업", "벤처",
    "R&D", "기술개발"
]

EXCLUDE_KEYWORDS = [
    "제조", "식품", "농업",
    "수출", "해외진출",
    "대기업", "중견기업",
    "프랜차이즈"
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

# ── 1차 키워드 필터 ───────────────────────────────────────
def keyword_filter(title):

    for kw in EXCLUDE_KEYWORDS:
        if kw in title:
            return False

    for kw in INCLUDE_KEYWORDS:
        if kw in title:
            return True

    return False

# ── 고액 사업 필터 ───────────────────────────────────────
def high_value_filter(title):

    for kw in HIGH_VALUE_PROGRAMS:
        if kw in title:
            return True

    return False

# ── Claude AI 필터 ──────────────────────────────────────
def ai_filter(items):

    if not items:
        return []

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    titles_text = "\n".join(
        [f"{i+1}. [{item['source']}] {item['title']}" for i, item in enumerate(items)]
    )

    prompt = f"""
다음은 창업 지원 공고 목록입니다.

{MINDBRIDGE_PROFILE}

공고 목록:
{titles_text}

MindBridge 프로젝트에 적합한 공고 번호만 선택하세요.

응답 형식
1,3,5

적합한 공고가 없으면
없음
"""

    try:

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        response = message.content[0].text.strip()

        print("AI 판단:", response)

        if response == "없음":
            return []

        selected = [
            int(x.strip()) - 1
            for x in response.split(",")
            if x.strip().isdigit()
        ]

        return [items[i] for i in selected if 0 <= i < len(items)]

    except Exception as e:

        print("AI 필터 오류:", e)

        return items


# ── 크롤링 함수 ─────────────────────────────────────────
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
                        "source": "창업넷"
                    })

    except Exception as e:

        print("창업넷 오류:", e)

    return results


def crawl_mss():

    results = []

    try:

        url = "https://www.mss.go.kr/site/smba/ex/bbs/List.do?cbIdx=86"

        r = requests.get(url, timeout=10)

        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.select("td.subject a, td a"):

            title = a.get_text(strip=True)

            href = a.get("href", "")

            if len(title) > 10:

                if href.startswith("/"):
                    href = "https://www.mss.go.kr" + href

                if href.startswith("http"):

                    results.append({
                        "title": title,
                        "url": href,
                        "source": "중소벤처기업부"
                    })

    except Exception as e:

        print("중기부 오류:", e)

    return results


def crawl_bizinfo():

    results = []

    try:

        url = "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"

        r = requests.get(url, timeout=10)

        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.select("td.tit a, .tit a"):

            title = a.get_text(strip=True)

            href = a.get("href", "")

            if len(title) > 10:

                if href.startswith("/"):
                    href = "https://www.bizinfo.go.kr" + href

                if href.startswith("http"):

                    results.append({
                        "title": title,
                        "url": href,
                        "source": "기업마당"
                    })

    except Exception as e:

        print("기업마당 오류:", e)

    return results


# ── 이메일 ─────────────────────────────────────────────
def send_email(new_items, filtered_items):

    if not new_items:
        print("새 공고 없음")
        return

    subject = f"[MindBridge 창업공고] 추천 {len(filtered_items)}건 / 전체 {len(new_items)}건"

    body = ""

    if filtered_items:

        body += "🎯 추천 공고\n"
        body += "=" * 40 + "\n\n"

        for item in filtered_items:

            body += f"[{item['source']}] {item['title']}\n"
            body += f"{item['url']}\n\n"

    else:

        body += "추천 공고 없음\n\n"

    body += "\n전체 새 공고\n"
    body += "-" * 40 + "\n"

    for item in new_items:

        body += f"[{item['source']}] {item['title']}\n"
        body += f"{item['url']}\n\n"

    msg = MIMEMultipart()

    msg["From"] = GMAIL_USER
    msg["To"] = NOTIFY_EMAIL
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:

        server.login(GMAIL_USER, GMAIL_PASS)

        server.send_message(msg)

    print("이메일 발송 완료")


# ── 메인 ───────────────────────────────────────────────
def main():

    print("크롤링 시작:", datetime.now())

    seen = load_seen()

    all_items = []

    all_items += crawl_kstartup()
    all_items += crawl_mss()
    all_items += crawl_bizinfo()

    print("총 수집:", len(all_items))

    new_items = []

    for item in all_items:

        uid = make_id(item["title"], item["url"])

        if uid not in seen:

            new_items.append(item)

            seen.add(uid)

    print("새 공고:", len(new_items))

    # 1차 키워드 필터
    kw_filtered = [i for i in new_items if keyword_filter(i["title"])]
    print("키워드 필터:", len(kw_filtered))

    # 2차 고액사업 필터
    high_value = [i for i in kw_filtered if high_value_filter(i["title"])]
    print("고액 사업:", len(high_value))

    # 3차 AI 필터
    ai_filtered = ai_filter(high_value)
    print("AI 추천:", len(ai_filtered))

    send_email(new_items, ai_filtered)

    save_seen(seen)


if __name__ == "__main__":
    main()
