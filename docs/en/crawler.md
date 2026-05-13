# KAKAO AI TOP 100 Crawler

> Component of **KAKAO Roastery Orchestra**

**Language:** [🇺🇸 English](./crawler.md) | [🇰🇷 한국어](../../crawler/README.md)

Crawler that automatically collects problem info (descriptions, questions, attachments) from the AI competition site.
An LLM (GPT) analyzes the site structure, extracts problem page content, and saves it under `../workspace/{slug}/problem/`.

## 1. Requirements

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) package manager
- OpenAI API key
- Chromium (auto-installed by Playwright)

## 2. Installation

```bash
# Move to the crawler directory
cd {PROJECT_ROOT}/crawler

# Create venv + install deps (uv handles automatically)
uv sync

# Or use requirements.txt
uv pip install -r requirements.txt

# Install Playwright browser binary
uv run playwright install chromium
```

## 3. Environment Variables

Create `.env` in the crawler directory:

```
OPENAI_API_KEY=sk-...
```

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | (required) | OpenAI API key |
| `LLM_MODEL` | `gpt-5.3-chat-latest` | LLM model ID |
| `CRAWL_SITE_URL` | `https://challenge.aitop100.org` | Target site |
| `CRAWL_CONCURRENCY` | `3` | Concurrent problem crawls |

## 4. Auth File

Prepare login info as a JSON file. Two formats supported:

### Format — localStorage (JWT token)

```json
{
    "aitop_tokens": {
        "access_token": "{YOUR_TOKEN}",
        "refresh_token": "{YOUR_TOKEN}"
    }
}
```

## 5. Run

```bash
uv run crawler.py --url <site_url> --cookie <auth_file.json>
```

### Example

```bash
uv run crawler.py \
  --url https://challenge.aitop100.org \
  --cookie test.json
```

[result](../../crawler/docs/image.png)

## 6. Output Structure

Each problem is saved under the project-root `workspace/` directory:

```
PROJECT_ROOT/
├── crawler/                       # this crawler
└── workspace/                     # output location
    └── {slug}/
        ├── prompt.md              # Orchestrator start prompt
        └── problem/
            ├── description.md     # description, notes, grading criteria
            ├── description1.png   # body image (if any)
            ├── questions.md       # question list, choices, scores
            └── files/             # attachments (zip auto-extracted)
```

## 7. Flow

1. Open the `--url` site in Chromium (headful)
2. Inject auth from `--cookie` (localStorage or cookies)
3. LLM extracts the problem list (name + URL + slug) from the current page
4. Crawl each problem page in up to `CRAWL_CONCURRENCY` parallel tabs
   - description / notes / grading criteria
   - questions and choices
   - body images (`description1.png`, …)
   - attachments (auto-unzip with ZIP Slip protection)
5. Save results to `../workspace/{slug}/`
6. Print success/failure list + write `workspace/crawl_log.txt`

## 8. Notes

- Prepare a valid logged-in token in the `--cookie` file before running
- Excessive `CRAWL_CONCURRENCY` risks being blocked — keep default (3)
- Output path is fixed to `../workspace`
