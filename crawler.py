import requests
from bs4 import BeautifulSoup
import hashlib
import json
from datetime import datetime
import anthropic
import os

SEEN_FILE = "seen_ids.json"

# 환경변수
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

MINDBRIDGE_PROFILE = """
프로젝트명: MindBridge
분야: 인지훈련, 디지털 헬스케어, 노인/치매 예방, AI 기반 뇌건강 플랫폼
목표: 예비창업패키지, 초기창업패키지, 청년창업, 소셜벤처, 중장년 기술창업, 창업도약패키지
"""

INCLUDE_KEYWORDS = [
    "예비창업", "초기창업", "청년창업", "창업지원", "창업패키지",
    "디지털", "ICT", "AI", "인공지능", "소프트웨어", "헬스케어", "복지",
    "노인", "치매", "사회적기업", "임팩트", "소셜벤처", "스타트업", "벤처",
    "R&D", "실증", "기술개발", "혁신"
]

EXCLUDE_KEYWORDS = [
    "제조", "식품", "농업", "수출", "해외진출", "대기업", "중견기업"
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
    title_lower = title
    for kw in EXCLUDE_KEYWORDS:
        if kw in title_lower:
            return False
    for kw in INCLUDE_KEYWORDS:
        if kw in title_lower:
            return True
    return False

def ai_filter(items):
    if not items or not ANTHROPIC_KEY:
        return items
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    titles_text = "\n".join([f"{i+1}. [{item['source']}] {item['title']}" for i, item in enumerate(items)])
    prompt = f"""다음은 창업 지원 공고 목록입니다. 아래 프로젝트에 적합한 공고 번호만 골라주세요.

{MINDBRIDGE_PROFILE}

공고 목록:
{titles_text}

응답 형식: 적합한 공고 번호를 쉼표로 구분해서만 답하세요. 예: 1,3,5
적합한 공고가 없으면 "없음"이라고만 답하세요."""
    try:
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=200,
            messages=[{"role":"user","content":prompt}]
        )
        response = message.content[0].text.strip()
        print("=== AI 판단 ===")
        print(response)
        if response == "없음":
            return []
        indices = [int(x.strip())-1 for x in response.split(",") if x.strip().isdigit()]
        return [items[i] for i in indices if 0 <= i < len(items)]
    except Exception as e:
        print(f"AI 오류: {e}")
        return items

def crawl_site(url, selector, base_url, source_name):
    results = []
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select(selector):
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if href.startswith("/"):
                href = base_url + href
            if len(title) > 5 and href.startswith("http"):
                results.append({"title": title, "url": href, "source": source_name})
    except Exception as e:
        print(f"{source_name} 오류: {e}")
    return results

def main():
    seen = load_seen()
    all_items = []

    # 사이트별 크롤링
    all_items += crawl_site("https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do","a[href]","https://www.k-startup.go.kr","창업넷")
    all_items += crawl_site("https://www.mss.go.kr/site/smba/ex/bbs/List.do?cbIdx=86","td.subject a, td a","https://www.mss.go.kr","중기부")
    all_items += crawl_site("https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do","td.tit a, .tit a, table a","https://www.bizinfo.go.kr","기업마당")
    all_items += crawl_site("https://startup.seoul.go.kr/notice/list","a[href]","https://startup.seoul.go.kr","서울시창업포털")

    print(f"총 수집 공고: {len(all_items)}")
    for i,item in enumerate(all_items[:10]):
        print(f"{i+1}. [{item['source']}] {item['title']} - {item['url']}")

    new_items = []
    for item in all_items:
        uid = make_id(item['title'], item['url'])
        if uid not in seen:
            new_items.append(item)
            seen.add(uid)

    print(f"1차 키워드 필터 전 새 공고 수: {len(new_items)}")
    kw_filtered = [i for i in new_items if keyword_filter(i['title'])]
    print(f"키워드 필터 후: {len(kw_filtered)}")
    for i,item in enumerate(kw_filtered[:10]):
        print(f"🔹 {i+1}. [{item['source']}] {item['title']}")

    ai_filtered = ai_filter(kw_filtered)
    print(f"AI 필터 후: {len(ai_filtered)}")
    for i,item in enumerate(ai_filtered[:10]):
        print(f"✅ {i+1}. [{item['source']}] {item['title']} - {item['url']}")

    save_seen(seen)
    print("=== 디버그 완료 ===")

if __name__ == "__main__":
    main()
