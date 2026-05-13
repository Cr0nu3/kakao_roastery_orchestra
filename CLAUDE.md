# KAKAO AI TOP 100 Solver

범용 Generator-Evaluator 구조로 KAKAO AI TOP 100 문제를 자동으로 풀기 위한 시스템.

## Architecture

```
Orchestrator → Generator ⇄ Evaluator (피드백 루프)
```

- **Orchestrator**: 루프 관리, 점수 추적, 최선 답안 제출
- **Generator**: 문제 파일을 읽고 접근법을 스스로 결정해 풀이 생성
- **Evaluator**: 답안 형식 기반으로 독립 검증 (Generator 추론 과정 차단)

## Key Design Rules

1. **범용 설계** — 특정 문제에 특화된 전략 없음. 에이전트가 문제에서 직접 도출
2. **Evaluator<->Generator 완전 분리** — Evaluator는 Generator의 추론 과정을 볼 수 없음
3. **파일 기반 통신** — 에이전트 간 데이터는 파일로만 교환
4. **best_so_far** — 최대 2라운드, score >= 0.85면 조기 종료, 항상 최고 점수 라운드 제출

## Workspace Structure

각 문제는 독립 디렉토리에서 실행된다:

```
workspace/{problem_name}/
├── prompt.md               # 사용자 작성 — Claude Code 시작 프롬프트
├── problem/
│   ├── description.md      # 문제 설명 (크롤링)
│   ├── questions.md        # 소문제 + 선지 + 답안 형식 (크롤링)
│   └── files/              # 다운로드된 문제 파일 (크롤링)
└── rounds/
    └── round_N/
        ├── solution/
        │   ├── answer.json
        │   └── evidence/   # 코드, 중간 결과
        └── evaluation/
            └── report.md
```

## Agent Specs

- `agents/generator.md` — Generator 행동 규칙
- `agents/evaluator.md` — Evaluator 행동 규칙
- `agents/orchestrator.md` — 루프 실행 절차

> workspace/{problem}/ 에서 실행 시 agents/ 경로는 `../../agents/`

## How to Run

```bash
# 단일 문제
cd workspace/{problem_name}
claude -p "$(cat prompt.md)" --dangerously-skip-permissions

# 여러 문제 실행 (비추천)
for dir in workspace/*/; do
    (cd "$dir" && claude -p "$(cat prompt.md)" --dangerously-skip-permissions) &
done
wait
```
