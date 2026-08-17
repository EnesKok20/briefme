# BriefMe

**Your inbox is broken. BriefMe fixes it.**

Every day you receive hundreds of messages across Gmail (and, optionally, LinkedIn and Instagram). Promotions you never asked for, connection requests from strangers, newsletters you forgot to unsubscribe from — all mixed in with the one email from your manager that actually matters.

You don't have time to read everything. But you can't afford to miss the important stuff either.

BriefMe is an AI-powered automation system that reads your messages, understands what each one is about, and delivers a single daily briefing by email — so you walk into your day already knowing what needs your attention.

> **Status:** Gmail is the primary, fully-supported source today. LinkedIn and Instagram connectors exist in the codebase but are **disabled by default** — see [A note on LinkedIn & Instagram](#a-note-on-linkedin--instagram) before turning them on.

--------

## What You Get Every Day

At 6 PM (or whenever you set it), BriefMe sends you a clean, visual HTML email — stat tiles, a source/category/priority breakdown, and a full sorted list of the day's messages, each with a one-click "Open in Gmail" link. A matching (and more detailed) HTML report is also saved locally under `reports/`.

**The Overview** — How many messages came in today, where they came from, and the overall distribution. One glance tells you if it was a busy day or a quiet one.

**Critical Items** — The messages you absolutely cannot ignore. A client escalation, a deadline reminder, a security alert. These float to the top, always.

**Opportunities** — Good news you might have missed. A recruiter reaching out, a positive response to your proposal, a collaboration offer buried under 50 newsletters.

**Work & Follow-ups** — Meeting invites, task assignments, threads waiting for your reply. Organized and summarized so you don't have to dig through chains.

**Noise & Promotions** — Every discount code, every "we miss you" email, every mass LinkedIn message — sorted into one section you can safely skip.

**Threats** — Phishing attempts, suspicious links, scam patterns. Flagged before you accidentally click something you shouldn't.

---

## How It Works Under the Hood

```
                    ┌──────────────────────┐
                    │     SCHEDULER        │
                    │  (daily, your time)  │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌───────────┐   ┌───────────┐   ┌────────────┐
        │   Gmail   │   │ LinkedIn  │   │ Instagram  │
        │ Connector │   │ Connector │   │ Connector  │
        │ (default) │   │ (opt-in)  │   │  (opt-in)  │
        └─────┬─────┘   └─────┬─────┘   └─────┬──────┘
              └────────────────┼────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │    AI ANALYZER       │
                    │      (Gemini)        │
                    │                      │
                    │  Classify            │
                    │  Detect sentiment    │
                    │  Score priority      │
                    │  Flag threats        │
                    │  Summarize           │
                    └──────────┬───────────┘
                               │
                         ┌─────┴─────┐
                         ▼           ▼
                   ┌──────────┐ ┌──────────┐
                   │  Report  │ │  Email   │
                   │  (HTML + │ │ Notifier │
                   │  charts) │ │          │
                   └──────────┘ └──────────┘
```

**Connectors** pull your messages from each platform. Gmail uses OAuth2 (official Google API), so your credentials never touch our code. LinkedIn and Instagram use unofficial, reverse-engineered APIs — see the note below before enabling them.

**Analyzer** runs each message through an LLM pipeline (Gemini today; the config has room for other providers later). The AI doesn't just keyword-match — it actually reads and understands context, tone, and intent.

**Reporter** turns the analysis into a visual HTML briefing with Plotly charts and organized sections, saved locally under `reports/`.

**Notifier** emails that same briefing (in an email-client-safe layout) to you at the time you choose.

### A note on LinkedIn & Instagram

Neither platform offers a public API for reading a personal inbox. The connectors in this repo (`src/connectors/linkedin.py`, `src/connectors/instagram.py`) use unofficial libraries (`linkedin-api`, `instagrapi`) that reverse-engineer each platform's internal API. That means:

- It's against both platforms' Terms of Service.
- Your account can get a security challenge (2FA prompt) or a temporary restriction — permanent bans are rarer for read-only use but not impossible.
- The response format isn't documented and can change without notice; both connectors are written defensively (per-item try/except) so a shape change degrades gracefully instead of crashing the whole run.

Both are **off by default** (`ENABLE_LINKEDIN=false` locally; Instagram was already opted into before this was written up, at your own risk). Flip the flag in `.env` only if you accept that risk — ideally test with a secondary account first.

---

## Why BriefMe Exists

Most "email management" tools give you filters and labels. You still have to set up rules, maintain them, and check everything yourself.

BriefMe takes a different approach:

- **It reads, so you don't have to.** Every message gets a 1-2 sentence summary. You scan 200 messages in 2 minutes.
- **It thinks, not just filters.** AI understands that "Let's circle back next quarter" is a soft rejection, not a meeting request.
- **It watches your back.** Phishing detection runs on every message, every day, automatically.
- **It connects everything.** Gmail, LinkedIn, Instagram — one unified view instead of three separate inboxes.
- **It learns your patterns.** Over time, the system understands what matters to you and what doesn't.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Language | Python 3.11+ | AI ecosystem, async support |
| Email | Gmail API (OAuth2) | Official, secure, read + send |
| Social (opt-in) | `linkedin-api`, `instagrapi` | Unofficial — no public inbox API exists for either platform |
| AI | Gemini (`google-genai`) | Fast, cheap, structured JSON output |
| Scheduler | APScheduler | Reliable daily execution (cron-style) |
| Notifications | Gmail API | Sends the daily briefing as an HTML email |
| Charts | Plotly | Clean, interactive visuals in the local HTML report |
| Reports | Plain Python (f-strings) | No templating engine — generated directly in `src/reporters/` |
| Config | pydantic-settings | Typed `.env` loading |

Planned, not yet built: persistent history/database, a Telegram notifier, a historical analytics dashboard, Docker packaging, CI/CD. See [Roadmap](#roadmap).

---

## Project Structure

```
briefme/
├── src/
│   ├── connectors/        # Gmail (default), LinkedIn & Instagram (opt-in) integrations
│   ├── analyzers/         # Gemini-powered classification, sentiment, threat detection
│   ├── reporters/         # Plotly chart generation and HTML report building
│   ├── notifiers/         # Email delivery
│   ├── scheduler/         # Daily job scheduling (APScheduler)
│   ├── storage/           # Reserved for future persistence — currently empty
│   ├── core/              # Engine orchestration, pipeline wiring, config
│   └── utils/             # Logging and helpers
├── tests/                 # Unit and integration tests (scaffolded, not yet written)
├── docs/                  # Architecture and setup guides
├── requirements.txt
└── main.py                # Entry point
```

---

## Quick Start

```bash
git clone https://github.com/EnesKok20/briefme.git
cd briefme

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env             # Add your API keys

python main.py --run-now         # Run once
python main.py --start           # Start daily scheduler
```

**Before the first run:**
1. Create an OAuth client in Google Cloud Console (Gmail API enabled), download it as `credentials.json` in the project root. The first `--run-now` opens a browser for consent and caches the result in `token.json` — after that it's silent.
2. Set `GEMINI_API_KEY` in `.env` — the analyzer won't start without it.
3. Set `NOTIFICATION_EMAIL` (or `SMTP_USER`) in `.env`, otherwise a report is built but nothing gets sent.
4. Leave `ENABLE_LINKEDIN` / `ENABLE_INSTAGRAM` as-is unless you've read the [note above](#a-note-on-linkedin--instagram) and accept the risk.

---

## Roadmap

- [x] Project architecture and structure
- [x] Core engine and data pipeline
- [x] Gmail connector with OAuth2
- [x] AI analysis pipeline (classify, sentiment, summarize) — Gemini
- [x] Threat and phishing detection
- [x] Daily HTML report with charts (Plotly)
- [x] Daily email briefing (stat tiles, priority breakdown, full message list, "Open in Gmail" links)
- [x] Scheduled daily execution (APScheduler)
- [x] LinkedIn connector — built, **opt-in / off by default**, unofficial API
- [x] Instagram connector — built, **opt-in**, unofficial API
- [ ] Telegram notifier
- [ ] Persistent history / database (`src/storage/`)
- [ ] Historical analytics dashboard
- [ ] Automated tests
- [ ] Docker containerization
- [ ] CI/CD with GitHub Actions

---

## License

MIT — see [LICENSE](LICENSE) for details.