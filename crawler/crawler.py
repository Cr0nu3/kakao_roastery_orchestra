"""
KAKAO AI TOP 100 크롤러

사용 방법:
  python crawler.py

흐름:
  1. headful 브라우저 오픈
  2. 사용자가 사이트 접속 → 로그인 → 문제 목록 페이지로 이동
  3. 터미널에서 Enter → LLM이 사이트 구조 분석 + 전체 문제 크롤링
"""

import argparse
import asyncio
import json
import os
from typing import Union, List, Dict
import pathlib
import re
import time
import zipfile
from urllib.parse import urljoin

from dotenv import load_dotenv
from openai import OpenAI
from playwright.async_api import async_playwright

load_dotenv()

# ── 설정 ──────────────────────────────────────────────────────────────
WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "..", "workspace")
SITE_URL = os.environ.get("CRAWL_SITE_URL", "https://challenge.aitop100.org")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-5.3-chat-latest")
CONCURRENCY = int(os.environ.get("CRAWL_CONCURRENCY", "3"))

_llm = OpenAI()  # OPENAI_API_KEY 환경변수 사용


# ── LLM 유틸 ──────────────────────────────────────────────────────────

def call_llm(system: str, user: str) -> str:
    """LLM 호출. 실패 시 2회 재시도."""
    for attempt in range(3):
        try:
            response = _llm.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM 응답이 비어 있습니다 (content=None)")
            return content
        except Exception as e:
            if attempt == 2:
                raise
            print(f"  [LLM] 오류 ({e}), {attempt + 1}회 재시도...")
            time.sleep(5)


def parse_json(raw: str) -> Union[dict, list]:
    """LLM 응답에서 JSON 추출. 3단계 폴백."""
    # 1차: 직접 파싱
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    # 2차: ```json ... ``` 코드블록 추출
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 3차: 첫 { 또는 [ 부터 끝까지 슬라이스
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = raw.find(start_char)
        end = raw.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass

    raise ValueError(f"JSON 파싱 실패:\n{raw[:500]}")


# ── 페이지 컨텍스트 수집 ───────────────────────────────────────────────

async def get_page_context(page) -> dict:
    """페이지 텍스트 + 링크 목록 수집. 리소스 완전 로드 후 실행."""
    # 네트워크 idle 대기 (모든 리소스 로드 완료)
    await page.wait_for_load_state("networkidle")

    # 페이지 끝까지 스크롤 → lazy-load 콘텐츠 강제 렌더링
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(1)
    await page.wait_for_load_state("networkidle")

    html = await page.inner_html("body")

    # 모든 링크·버튼 추출 (href + 텍스트) — aria_snapshot 대체
    links = await page.evaluate(
        """() => Array.from(document.querySelectorAll('a[href], button'))
            .map(el => ({href: el.href || '', text: (el.innerText || el.textContent || '').trim().slice(0, 120)}))
            .filter(l => l.text)
            .slice(0, 300)"""
    )

    return {
        "url": page.url,
        "html": html[:80_000],
        "links": links,
    }


# ── 문제 목록 분석 ────────────────────────────────────────────────────

async def analyze_problem_list(page) -> List[Dict]:
    """현재 페이지에서 LLM으로 문제 목록(이름 + URL + slug) 추출."""
    print("[CRAWLER] 문제 목록 분석 중...")
    ctx = await get_page_context(page)

    system = (
        "너는 AI 경진대회 사이트를 분석하는 전문가다. "
        "주어진 페이지에서 문제 목록을 추출한다. "
        "반드시 JSON만 반환하라. 설명 텍스트는 포함하지 마라."
    )
    user = f"""아래는 AI 경진대회 사이트 페이지다.

## URL
{ctx['url']}

## 페이지 HTML
{ctx['html']}

## 페이지 링크 목록
{ctx['links']}

## 작업
이 페이지에서 도전 가능한 문제(challenge/problem) 목록을 찾아라.
각 문제의 이름과 상세 페이지 URL을 추출하라.
slug는 URL 경로 마지막 세그먼트를 그대로 사용하라 (예: /problem/cooking → "cooking").

## 반환 형식 (JSON)
{{
  "problems": [
    {{
      "name": "문제 제목",
      "slug": "slug",
      "url": "절대 URL"
    }}
  ]
}}"""

    raw = call_llm(system, user)
    result = parse_json(raw)

    problems = result.get("problems", [])

    # 상대 URL → 절대 URL 보정
    for p in problems:
        if not p["url"].startswith("http"):
            p["url"] = urljoin(SITE_URL, p["url"])

    print(f"[CRAWLER] {len(problems)}개 문제 발견: {[p['name'] for p in problems]}")
    return problems


# ── 문제 페이지 분석 ──────────────────────────────────────────────────

async def analyze_problem_page(page) -> dict:
    """문제 페이지에서 description + questions + 다운로드 링크 추출."""
    ctx = await get_page_context(page)

    # ── LLM 호출 A: 콘텐츠 추출 ──
    system_content = (
        "너는 AI 경진대회 문제 페이지를 분석하는 전문가다. "
        "문제 설명과 문항 정보를 정확히 추출한다. "
        "반드시 JSON만 반환하라. 설명 텍스트는 포함하지 마라."
    )
    user_content = f"""아래는 AI 경진대회 문제 페이지다.

## URL
{ctx['url']}

## 페이지 HTML
{ctx['html']}

## 작업
다음 정보를 추출하라.

### description (문제 설명)
- title: 문제 제목
- body: 문제 설명 본문 (원문 그대로, 마크다운 가능. HTML <table>은 마크다운 표로 변환. HTML <img>는 반드시 ![alt](src) 형태로 포함할 것)
- notes: 유의사항 항목 리스트 (없으면 빈 배열)

### questions (문항 목록)
- total_score: 총점 (정수)
- items: 각 문항 배열
  - number: 문항 번호 (정수)
  - score: 배점 (정수)
  - question_text: 질문 텍스트
  - answer_type: 아래 중 정확히 하나
      "객관식 (단일 선택)" — radio 버튼, 하나만 선택
      "복수 선택 (체크박스)" — checkbox, 여러 개 선택
      "숫자 입력" — 숫자만 입력
      "텍스트 입력" — 짧은 텍스트 입력
      "JSON 배열" — JSON 형식 배열 제출
      "자유 텍스트" — 긴 텍스트 또는 문서 작성
  - choices: 선지 배열 (객관식/복수선택일 때만, 없으면 null)
  - format_hint: 형식 힌트 또는 예시 (있으면 문자열, 없으면 null)

### extra_sections (그 외 섹션)
위 두 카테고리에 속하지 않는 모든 섹션 (배점 및 채점 기준, 제출 형식 안내 등)을 원문 그대로 담는다.
- title: 섹션 제목
- content: 섹션 내용 (마크다운, HTML <table>은 마크다운 표로 변환)

## 반환 형식 (JSON)
{{
  "description": {{
    "title": "...",
    "body": "...",
    "notes": ["..."]
  }},
  "questions": {{
    "total_score": 85,
    "items": [
      {{
        "number": 1,
        "score": 10,
        "question_text": "...",
        "answer_type": "객관식 (단일 선택)",
        "choices": ["A", "B", "C"],
        "format_hint": null
      }}
    ]
  }},
  "extra_sections": [
    {{
      "title": "배점 및 채점 기준",
      "content": "..."
    }}
  ]
}}"""

    raw_content = call_llm(system_content, user_content)
    content = parse_json(raw_content)

    if not content.get("description") or not content.get("questions"):
        raise ValueError(f"LLM 응답에 필수 키 누락: {list(content.keys())}")

    # ── LLM 호출 B: 다운로드 링크 추출 ──
    system_files = (
        "너는 웹 페이지에서 다운로드 링크를 찾는 전문가다. "
        "반드시 JSON만 반환하라. 설명 텍스트는 포함하지 마라."
    )
    user_files = f"""아래는 AI 경진대회 문제 페이지의 링크 목록과 텍스트다.

## URL
{ctx['url']}

## 페이지 링크 목록
{ctx['links']}

## 페이지 HTML (일부)
{ctx['html'][:15_000]}

## 작업
이 페이지에서 문제 자료 다운로드 링크를 모두 찾아라.
파일 다운로드 버튼, 첨부파일 링크, zip 파일 링크 등을 포함한다.
일반 네비게이션 링크(다른 페이지 이동)는 제외하라.

## 반환 형식 (JSON)
{{
  "download_links": [
    {{
      "filename": "추정 파일명",
      "url": "URL (href 값 그대로)",
      "a11y_name": "접근성 이름 (버튼/링크의 텍스트)"
    }}
  ]
}}"""

    raw_files = call_llm(system_files, user_files)
    files_result = parse_json(raw_files)

    return {
        "description": content.get("description", {}),
        "questions": content.get("questions", {}),
        "extra_sections": content.get("extra_sections", []),
        "download_links": files_result.get("download_links", []),
    }


# ── 파일 저장 ─────────────────────────────────────────────────────────

def save_prompt(workspace_dir: str, slug: str) -> None:
    content = f"""너는 Orchestrator다. `../../agents/orchestrator.md`를 읽고 지시를 따라라.

- 문제 ID: {slug}
- 작업 디렉토리: workspace/{slug}/
"""
    path = os.path.join(workspace_dir, slug, "prompt.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  → prompt.md 저장")


def save_description(problem_dir: str, desc: dict, extra_sections: list) -> None:
    notes_md = "\n".join(f"- {n}" for n in desc.get("notes", [])) or "- 없음"
    content = f"""# {desc.get('title', '제목 없음')}

## 문제 설명
```
{desc.get('body', '')}
```

## **[CRITICAL]** 유의사항 **[CRITICAL]**
```
{notes_md}
```
"""
    for sec in extra_sections:
        title = sec.get('title', '기타')
        sec_content = sec.get('content', '')
        if any(kw in title for kw in ("채점", "배점")):
            content += f"\n## **[CRITICAL]** {title} **[CRITICAL]**\n```\n{sec_content}\n```\n"
        else:
            content += f"\n## {title}\n```\n{sec_content}\n```\n"

    path = os.path.join(problem_dir, "description.md")
    os.makedirs(problem_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  → description.md 저장")


def save_questions(problem_dir: str, questions: dict) -> None:
    lines = ["# 문항 목록", "", f"총점: {questions.get('total_score', '?')}점", ""]
    for item in questions.get("items", []):
        lines.append(f"## 문항 {item.get('number', '?')} ({item.get('score', '?')}점)")
        lines.append("```")
        lines.append(f"질문: {item.get('question_text', '')}")
        answer_type = item.get('answer_type', '')
        is_multi = "복수" in answer_type or "체크박스" in answer_type
        format_hint = item.get("format_hint")
        needs_marker = is_multi or bool(format_hint)
        if needs_marker:
            lines.append(f"**[IMPORTANT]** 답안 유형: {answer_type} **[IMPORTANT]**")
        else:
            lines.append(f"답안 유형: {answer_type}")
        if item.get("choices"):
            lines.append("선지:")
            for c in item["choices"]:
                lines.append(f"- {c}")
        if format_hint:
            lines.append(f"**[IMPORTANT]** 형식 힌트: {format_hint} **[IMPORTANT]**")
        lines.append("```")
        lines.append("")

    path = os.path.join(problem_dir, "questions.md")
    os.makedirs(problem_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  → questions.md 저장")


async def download_description_images(page, problem_dir: str, body: str) -> str:
    """body 마크다운에서 ![...](url) 이미지 추출 → 다운로드 → 로컬 파일명으로 교체."""
    pattern = re.compile(r'!\[([^\]]*)\]\((https?://[^)]+)\)')
    matches = pattern.findall(body)
    if not matches:
        return body

    os.makedirs(problem_dir, exist_ok=True)
    for idx, (alt, url) in enumerate(matches, 1):
        try:
            resp = await page.context.request.get(url)
            if not resp.ok:
                continue
            # Content-Type에서 확장자 추출, 기본 png
            ct = resp.headers.get("content-type", "image/png").split(";")[0].strip()
            ext = ct.split("/")[-1].replace("jpeg", "jpg")
            if ext not in ("png", "jpg", "gif", "webp", "svg"):
                ext = "png"
            filename = f"description{idx}.{ext}"
            dest = pathlib.Path(problem_dir) / filename
            with open(dest, "wb") as f:
                f.write(await resp.body())
            body = body.replace(url, filename, 1)
            print(f"  → 이미지 저장: {filename}")
        except Exception as e:
            print(f"  [경고] 이미지 다운로드 실패 ({url}): {e}")
    return body


async def download_files(page, files_dir: str, download_links: List[Dict]) -> None:
    if not download_links:
        return
    os.makedirs(files_dir, exist_ok=True)

    for link in download_links:
        raw_url = link.get("url", "")
        filename = link.get("filename", "file")
        a11y_name = link.get("a11y_name", "")

        if not raw_url and not a11y_name:
            continue

        abs_url = urljoin(page.url, raw_url) if raw_url else ""

        try:
            # 경로 A: URL 직접 다운로드 (세션 쿠키 포함)
            if abs_url:
                resp = await page.context.request.get(abs_url)
                if resp.ok:
                    body = await resp.body()
                    # Content-Disposition에서 파일명 추출 시도
                    cd = resp.headers.get("content-disposition", "")
                    m = re.search(r'filename\*?=["\']?(?:UTF-8\'\')?([^"\';\r\n]+)', cd)
                    if m:
                        filename = pathlib.Path(m.group(1).strip()).name  # path traversal 방지
                    dest = pathlib.Path(files_dir) / filename
                    with open(dest, "wb") as f:
                        f.write(body)
                    print(f"  → 다운로드: {filename}")
                    _extract_zip(dest, files_dir)
                    continue

            # 경로 B: 버튼 클릭 다운로드 (JS 트리거)
            if a11y_name:
                async with page.expect_download(timeout=60_000) as dl_info:
                    locator = page.get_by_role("link", name=a11y_name)
                    if not await locator.count():
                        locator = page.get_by_text(a11y_name)
                    await locator.first.click()
                    dl = await dl_info.value
                dest = os.path.join(files_dir, dl.suggested_filename or filename)
                await dl.save_as(dest)
                print(f"  → 다운로드 (클릭): {os.path.basename(dest)}")
                _extract_zip(dest, files_dir)

        except Exception as e:
            print(f"  [경고] 다운로드 실패 ({filename}): {e}")


def _extract_zip(path: str, dest_dir: str) -> None:
    if not path.endswith(".zip"):
        return
    dest = pathlib.Path(dest_dir).resolve()
    try:
        with zipfile.ZipFile(path, "r") as z:
            for member in z.namelist():
                target = (dest / member).resolve()
                if not str(target).startswith(str(dest)):
                    raise ValueError(f"ZIP Slip 차단: {member}")
                z.extract(member, dest_dir)
        print(f"  → zip 해제: {os.path.basename(path)}")
    except zipfile.BadZipFile:
        print(f"  [경고] zip 파일 손상: {os.path.basename(path)}")


# ── 메인 ──────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="KAKAO AI TOP 100 크롤러")
    parser.add_argument("--url", required=True, help="크롤링할 사이트 주소")
    parser.add_argument("--cookie", required=True, help="쿠키 JSON 파일 경로")
    args = parser.parse_args()

    print("=" * 60)
    print("KAKAO AI TOP 100 크롤러")
    print("=" * 60)

    if not os.environ.get("OPENAI_API_KEY"):
        print("\n[오류] OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("  export OPENAI_API_KEY=\"sk-...\"")
        return

    with open(args.cookie, encoding="utf-8") as f:
        auth_data = json.load(f)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        # localStorage 주입을 위해 빈 페이지로 먼저 이동
        await page.goto(args.url, wait_until="networkidle")

        # auth 파일이 배열이면 쿠키, 객체이면 localStorage
        if isinstance(auth_data, list):
            sameSite_map = {"unspecified": "None", "no_restriction": "None", "lax": "Lax", "strict": "Strict"}
            cookies = []
            for c in auth_data:
                cookie = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c["domain"],
                    "path": c.get("path", "/"),
                    "secure": c.get("secure", False),
                    "httpOnly": c.get("httpOnly", False),
                    "sameSite": sameSite_map.get(c.get("sameSite", "").lower(), "None"),
                }
                if "expirationDate" in c:
                    cookie["expires"] = int(c["expirationDate"])
                cookies.append(cookie)
            await context.add_cookies(cookies)
            await page.reload(wait_until="networkidle")
        else:
            # localStorage에 각 키-값 주입 후 페이지 재로드
            for key, value in auth_data.items():
                serialized = json.dumps(value) if isinstance(value, dict) else value
                await page.evaluate(f"localStorage.setItem({json.dumps(key)}, {json.dumps(serialized)})")
            await page.reload(wait_until="networkidle")

        print(f"\n[CRAWLER] {args.url} 접속 완료")

        # 현재 페이지 기준으로 문제 목록 분석
        problems = await analyze_problem_list(page)
        if not problems:
            print("[CRAWLER] 문제를 찾지 못했습니다. 문제 목록 페이지에 있는지 확인하세요.")
            await browser.close()
            return

        # localStorage 인증을 모든 새 페이지에 자동 주입
        if auth_data and not isinstance(auth_data, list):
            init_lines = []
            for key, value in auth_data.items():
                serialized = json.dumps(value) if isinstance(value, dict) else value
                init_lines.append(f"localStorage.setItem({json.dumps(key)}, {json.dumps(serialized)});")
            await context.add_init_script("\n".join(init_lines))

        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def crawl_problem(problem: dict, idx: int, total: int):
            async with semaphore:
                print(f"\n[{idx}/{total}] {problem['name']} ({problem['slug']})")
                tab = await context.new_page()
                try:
                    await tab.goto(problem["url"], wait_until="networkidle")
                    result = await analyze_problem_page(tab)

                    problem_dir = os.path.join(WORKSPACE_DIR, problem["slug"], "problem")
                    files_dir = os.path.join(problem_dir, "files")

                    body = result["description"].get("body", "")
                    result["description"]["body"] = await download_description_images(tab, problem_dir, body)

                    save_prompt(WORKSPACE_DIR, problem["slug"])
                    save_description(problem_dir, result["description"], result.get("extra_sections", []))
                    save_questions(problem_dir, result["questions"])
                    await download_files(tab, files_dir, result["download_links"])

                    return problem["name"], None
                except Exception as e:
                    print(f"  [오류] {problem['name']}: {e}")
                    return None, problem["name"]
                finally:
                    await tab.close()

        results = await asyncio.gather(*(
            crawl_problem(p, i, len(problems))
            for i, p in enumerate(problems, 1)
        ))
        success = [n for n, e in results if n]
        failed  = [e for n, e in results if e]

        await browser.close()

    print()
    print("=" * 60)
    print(f"완료: {len(success)}개 성공, {len(failed)}개 실패")
    if success:
        print(f"성공: {', '.join(success)}")
    if failed:
        print(f"실패: {', '.join(failed)}")

    # 결과 로그 저장
    log_path = os.path.join(WORKSPACE_DIR, "crawl_log.txt")
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"성공: {success}\n실패: {failed}\n")
    print(f"로그: {log_path}")


if __name__ == "__main__":
    asyncio.run(main())
