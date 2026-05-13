# KAKAO AI TOP 100 Solver

> Codename: **KAKAO Roastery Orchestra**

**Language:** [🇺🇸 English](#english) | [🇰🇷 한국어](#한국어)

범용 Generator-Evaluator 루프 구조로 KAKAO AI TOP 100 문제를 자동으로 푸는 시스템.

```
Orchestrator → Generator ⇄ Evaluator (피드백 루프)
```

> Crawler 설치/사용은 [`crawler/README.md`](./crawler/README.md) 참조.

---

<a id="english"></a>

## English

### Architecture
[archecture](./docs/flowchart.png)

- **Orchestrator** — runs the Generator↔Evaluator loop, tracks best score, submits best round
- **Generator** — reads the problem and produces a solution
- **Evaluator** — independently grades answers (No interaction with Generator)

### Prerequisites

- [Claude Code CLI](https://docs.claude.com/claude-code) (`claude` installed and logged in)
- A `workspace/{slug}/` directory populated by the crawler (see `crawler/README.md`)

### 1. Install

```bash
git clone <repo> kakao_roastery_orchestra
cd kakao_roastery_orchestra

# Claude Code auth (one-time)
claude login
```

### 2. Solve a single problem

```bash
cd kakao_roastery_orchestra/workspace/{slug}
claude -p "$(cat prompt.md)" --dangerously-skip-permissions
```

Orchestrator runs the Generator↔Evaluator loop. Max 2 rounds, early-exit at score ≥ 0.85, highest-scoring round selected.

### 3. Solve all problems (optional)

```bash
cd kakao_roastery_orchestra

# Sequential (safe)
for dir in workspace/*/; do
  [ -f "$dir/prompt.md" ] || continue
  (cd "$dir" && claude -p "$(cat prompt.md)" --dangerously-skip-permissions)
done

# Parallel (not recommended — resource / quota pressure)
for dir in workspace/*/; do
  [ -f "$dir/prompt.md" ] || continue
  (cd "$dir" && claude -p "$(cat prompt.md)" --dangerously-skip-permissions) &
done
wait
```

### 4. Check results

```bash
# Best answer
cat workspace/{slug}/rounds/round_*/solution/answer.json

# Evaluation report
cat workspace/{slug}/rounds/round_*/evaluation/report.md
```

### Directory Layout

```
kakao_roastery_orchestra/
├── agents/                 # generator.md, evaluator.md, orchestrator.md (agent specs)
├── config/                 # evaluation_checklists.md, problem_taxonomy.md
├── crawler/                # problem crawler (see crawler/README.md)
├── docs/                   # architecture.md
└── workspace/              # per-problem run dirs
    └── {slug}/
        ├── prompt.md
        ├── problem/        # description.md, questions.md, files/
        └── rounds/round_N/
            ├── solution/answer.json
            └── evaluation/report.md
```

### Problem Types

Per [`config/problem_taxonomy.md`](./config/problem_taxonomy.md). Generator/Evaluator self-classify problems before solving.

| Type | Description | Trigger | Tools |
|---|---|---|---|
| **TYPE_A** | Data analysis | Large JSON/CSV/TXT + aggregate/classify/predict | pandas, numpy, scikit-learn |
| **TYPE_B** | Code interpretation/execution | DSL spec or obfuscated code | Python runtime |
| **TYPE_C** | Multimedia extraction | Image/video/PDF input | pytesseract, pdfplumber, PyMuPDF |
| **TYPE_D** | Document synthesis | Heterogeneous files + template | docx/xlsx/m4a/pdf parsers |
| **TYPE_E** | Spatial simulation | Coords + collision + simulator | provided `simulator.py`, pygame |

Composite types possible (e.g. A+C: OCR numbers from image → statistics). Apply all relevant verification methods.

### Notes

- **TYPE_C handled by Gemini elsewhere.** This system covers TYPE_A · B · D · E only.
- Mixed types containing TYPE_C (A+C, B+C, D+C) → multimedia extraction step routed externally; remaining steps run here.

---

<a id="한국어"></a>

## 한국어

### 아키텍처
[archecture](./docs/flowchart.png)
- **Orchestrator** — Generator↔Evaluator 루프 실행, 점수 추적, 최고 라운드 제출
- **Generator** — 문제 읽고 풀이 생성
- **Evaluator** — Generator와 독립적으로 문제 풀이 후, 비교

### 사전 조건

- [Claude Code CLI](https://docs.claude.com/claude-code) (`claude` 설치 + 로그인)
- 크롤러로 채워진 `workspace/{slug}/` 디렉토리 (`crawler/README.md` 참조)

### 1. 설치

```bash
git clone <repo> kakao_roastery_orchestra
cd kakao_roastery_orchestra

# Claude Code 인증 (1회)
claude login
```

### 2. 단일 문제 풀이

```bash
cd kakao_roastery_orchestra/workspace/{slug}
claude -p "$(cat prompt.md)" --dangerously-skip-permissions
```

Orchestrator 가 Generator↔Evaluator 루프 실행. 최대 2라운드, score ≥ 0.85 면 조기 종료, 최고 점수 라운드 자동 선정.

### 3. 전체 문제 일괄 풀이 (선택)

```bash
cd kakao_roastery_orchestra

# 순차 (안전)
for dir in workspace/*/; do
  [ -f "$dir/prompt.md" ] || continue
  (cd "$dir" && claude -p "$(cat prompt.md)" --dangerously-skip-permissions)
done

# 병렬 (비추천 — 리소스/쿼터 부담)
for dir in workspace/*/; do
  [ -f "$dir/prompt.md" ] || continue
  (cd "$dir" && claude -p "$(cat prompt.md)" --dangerously-skip-permissions) &
done
wait
```

### 4. 결과 확인

```bash
# 최종 답안
cat workspace/{slug}/rounds/round_*/solution/answer.json

# 평가 리포트
cat workspace/{slug}/rounds/round_*/evaluation/report.md
```

### 디렉토리 구조

```
kakao_roastery_orchestra/
├── agents/                 # generator.md, evaluator.md, orchestrator.md (에이전트 스펙)
├── config/                 # evaluation_checklists.md, problem_taxonomy.md
├── crawler/                # 문제 크롤러 (crawler/README.md 참조)
├── docs/                   # architecture.md
└── workspace/              # 문제별 실행 디렉토리
    └── {slug}/
        ├── prompt.md
        ├── problem/        # description.md, questions.md, files/
        └── rounds/round_N/
            ├── solution/answer.json
            └── evaluation/report.md
```

### 문제 유형

[`config/problem_taxonomy.md`](./config/problem_taxonomy.md) 기반. Generator/Evaluator 가 풀이 전 스스로 분류.

| 유형 | 특징 | 판별 기준 | 핵심 도구 |
|---|---|---|---|
| **TYPE_A** | 데이터 분석형 | 대용량 JSON/CSV/TXT + 집계·분류·예측 | pandas, numpy, scikit-learn |
| **TYPE_B** | 코드 해석/실행형 | DSL 명세 또는 난독화 코드 | Python 실행 환경 |
| **TYPE_C** | 멀티미디어 추출형 | 이미지/영상/PDF 첨부 | pytesseract, pdfplumber, PyMuPDF |
| **TYPE_D** | 문서 종합 작성형 | 복수 이기종 파일 + 템플릿 | docx/xlsx/m4a/pdf 파서 |
| **TYPE_E** | 공간 시뮬레이션형 | 좌표계 + 충돌 + 시뮬레이터 | 제공 `simulator.py`, pygame |

복합 유형 가능 (예: A+C — 이미지에서 수치 OCR → 통계). 각 유형 검증 방법 모두 적용.

### 주의사항

- **TYPE_C 는 별도 Gemini 처리.** 본 시스템은 TYPE_A · B · D · E 만 담당.
- TYPE_C 가 섞인 복합 유형(A+C, B+C, D+C) → 멀티미디어 추출 단계만 외부 라우팅, 나머지 단계는 본 시스템 처리.
