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
MAX_ITEMS = 10  # 하루 발송 최대 건수

MINDBRIDGE_PROFILE = """
프로젝트명: MindBridge
분야: 인지훈련, 디지털 헬스케어, 노인/치매 예방, AI 기반 뇌건강 플랫폼
기술: 웹 기반 서비스, AI, 소프트웨어 개발
팀 구성: 공동창업자 3명 (개발자 포함), 무자본 창업 초기 단계
목표: 예비창업패키지, 초기창업패키지, 청년창업 지원금 확보
적합한 공고 조건:
- 예비창업자 또는 창업 3년 이내 대상
- ICT/디지털/소프트웨어/AI 분야
- 복지/헬스케어/사회문제 해결 관련
- 청년 창업 지원
- 정부 R&D, 실증 지원 사업
부적합한 공고:
- 제조업, 하드웨어, 식품, 농업 분야
- 창업 5년 이상 기업 대상
- 수출, 해외진출 전용
- 대기업/중견기업 대상
"""

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

INCLUDE_KEYWORDS = [
    "예비창업", "초기창업", "청년창업", "창업지원", "창업패키지",
    "디지털", "ICT", "AI", "인공지능", "소프트웨어", "앱", "플랫폼",
    "헬스케어", "디지털헬스", "복지", "노인", "치매", "인지",
    "사회적기업", "임팩트", "소셜벤처", "스타트업", "벤처",
    "R&D", "실증", "기술개발", "혁신"
]

EXCLUDE_KEYWORDS = [
    "제조", "식품", "농업", "농촌", "수출", "해외진출",
    "대기업", "중견기업", "프랜차이즈", "소상공인 폐업"
]

def keyword_filter(title):
    title_lower = title
    for kw in EXCLUDE_KEYWORDS:
        if kw in title_lower:
            return False
    for kw in INCLUDE_KEYWORDS:
        if kw in title_lower:
            return True
    return False

def ai_filter(items):
    if not items:
        return []
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    titles_text = "\n".join([f"{i+1}. [{item['source']}] {item['title']}" 
                              for i, item in enumerate(items)])
    prompt = f"""다음은 창업 지원 공고 목록입니다. 아래 프로젝트에 적합한 공고 번호만 골라주세요.

{MINDBRIDGE_PROFILE}

공고 목록:
{titles_text}

응답 형식: 적합한 공고 번호를 쉼표로 구분해서만 답하세요. 예: 1,3,5
적합한 공고가 없으면 "없음"이라고만 답하세요.
설명은 하지 마세요."""
    try:
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        response = message.content[0].text.strip()
        if response == "없음":
            return []
        selected_indices = [int(x.strip()) - 1 for x in response.split(",") if x.strip().isdigit()]
        filtered = [items[i] for i in selected_indices if 0 <= i < len(items)]
        return filtered[:MAX_ITEMS]  # 하루 최대 건수 제한
    except Exception as e:
        print(f"AI 필터 오류: {e}")
        return items[:MAX_ITEMS]  # 오류 시 전체 공고 중 일부만 발송

def crawl_generic(url, base_url="", selector="a[href]", source="사이트"):
    results = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select(selector)[:80]:
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if len(title) > 10:
                if href.startswith("/"):
                    href = base_url + href
                if href.startswith("http"):
                    results.append({"title": title, "url": href, "source": source})
    except Exception as e:
        print(f"{source} 오류: {e}")
    return results

def crawl_all():
    all_items = []
    all_items += crawl_generic("https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do", 
                               "https://www.k-startup.go.kr", source="창업넷")
    all_items += crawl_generic("https://www.mss.go.kr/site/smba/ex/bbs/List.do?cbIdx=86", 
                               "https://www.mss.go.kr", selector="td.subject a, td a", source="중소벤처기업부")
    all_items += crawl_generic("https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do", 
                               "https://www.bizinfo.go.kr", selector="td.tit a, .tit a, table a", source="기업마당")
    all_items += crawl_generic("https://startup.seoul.go.kr/notice/list", 
                               "https://startup.seoul.go.kr", source="서울시창업포털")
    return all_items

def send_email(new_items, filtered_items):
    if not new_items:
        print("오늘 새 공고 없음.")
        return
    subject = f"[MindBridge 창업공고] 추천 {len(filtered_items)}건 / 전체 새공고 {len(new_items)}건 - {datetime.now().strftime('%Y-%m-%d')}"
    body = ""
    if filtered_items:
        body += f"🎯 추천 공고 {len(filtered_items)}건\n" + "="*50 + "\n\n"
        for item in filtered_items:
            body += f"📌 [{item['source']}] {item['title']}\n   🔗 {item['url']}\n\n"
    else:
        body += "오늘은 추천 공고가 없습니다.\n\n"
    body += "\n" + "-"*50 + "\n📋 전체 새 공고 (참고용)\n\n"
    for item in new_items[:MAX_ITEMS]:
        body += f"• [{item['source']}] {item['title']}\n  {item['url']}\n\n"
    body += "\n---\nMindBridge 창업공고 자동알림 시스템"
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = NOTIFY_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
    print(f"이메일 발송 완료 - 추천: {len(filtered_items)}건 / 전체: {len(new_items)}건")

def main():
    print(f"크롤링 시작: {datetime.now()}")
    seen = load_seen()
    all_items = crawl_all()
    print(f"총 {len(all_items)}건 수집")
    new_items = []
    for item in all_items:
        uid = make_id(item["title"], item["url"])
        if uid not in seen:
            new_items.append(item)
            seen.add(uid)
    print(f"새 공고: {len(new_items)}건")
    kw_filtered = [item for item in new_items if keyword_filter(item["title"])]
    print(f"키워드 필터 후: {len(kw_filtered)}건")
    ai_filtered = ai_filter(kw_filtered)
    print(f"AI 필터 후: {len(ai_filtered)}건")
    send_email(new_items, ai_filtered)
    save_seen(seen)

if __name__ == "__main__":
    main()
