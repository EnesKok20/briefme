# BriefMe

**Your inbox is broken. BriefMe fixes it.**

Every day you receive hundreds of messages across Gmail, LinkedIn, and Instagram. Promotions you never asked for, connection requests from strangers, newsletters you forgot to unsubscribe from — all mixed in with the one email from your manager that actually matters.

You don't have time to read everything. But you can't afford to miss the important stuff either.

BriefMe is an AI-powered automation system that reads all your messages across platforms, understands what each one is about, and delivers a single daily briefing to your phone — so you walk into your day already knowing what needs your attention.

---

## What You Get Every Day

At 6 PM (or whenever you set it), BriefMe sends you a clean, visual report:

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
        └─────┬─────┘   └─────┬─────┘   └─────┬──────┘
              └────────────────┼────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │    AI ANALYZERS      │
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
                   │ Database │ │ Reporter │
                   │          │ │ (charts  │
                   │          │ │  + HTML) │
                   └──────────┘ └────┬─────┘
                                     │
                                ┌────┴────┐
                                ▼         ▼
                         ┌──────────┐ ┌────────┐
                         │ Telegram │ │ Email  │
                         │   Bot    │ │        │
                         └──────────┘ └────────┘
```

**Connectors** pull your messages from each platform using official APIs. Gmail uses OAuth2, so your credentials never touch our code.

**Analyzers** run each message through an LLM pipeline. The AI doesn't just keyword-match — it actually reads and understands context, tone, and intent.

**Reporter** turns the analysis into a visual briefing with charts and organized sections.

**Notifier** delivers the final report to your Telegram or email at the time you choose.

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
| Email | Gmail API | OAuth2, secure, official |
| Social | LinkedIn & Instagram APIs | Native platform access |
| AI | Claude / OpenAI | Context-aware analysis |
| Database | SQLAlchemy + SQLite | Lightweight, upgradeable to PostgreSQL |
| Scheduler | APScheduler | Reliable daily execution |
| Notifications | Telegram Bot API | Instant, interactive |
| Charts | Plotly | Clean, interactive visuals |
| Reports | Jinja2 | Templated HTML generation |
| Dashboard | FastAPI | Historical data viewer |
| Deploy | Docker + GitHub Actions | One-command deployment |

---

## Project Structure

```
briefme/
├── src/
│   ├── connectors/        # Gmail, LinkedIn, Instagram integrations
│   ├── analyzers/         # AI classification, sentiment, threat detection
│   ├── reporters/         # Chart generation and HTML report building
│   ├── notifiers/         # Telegram and email delivery
│   ├── scheduler/         # Daily job scheduling
│   ├── storage/           # Database models and persistence
│   ├── core/              # Engine orchestration and config
│   └── utils/             # Logging and helpers
├── tests/                 # Unit and integration tests
├── docs/                  # Architecture and setup guides
├── main.py                # Entry point
├── Dockerfile
└── docker-compose.yml
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

---

## Roadmap

- [x] Project architecture and structure
- [ ] Core engine and data pipeline
- [ ] Gmail connector with OAuth2
- [ ] AI analysis pipeline (classify, sentiment, summarize)
- [ ] Threat and phishing detection
- [ ] Daily HTML report with charts
- [ ] Telegram bot with interactive sections
- [ ] Scheduled daily execution
- [ ] LinkedIn connector (messages, connections, job alerts)
- [ ] Instagram connector (DMs, follow requests)
- [ ] Historical analytics dashboard
- [ ] Docker containerization
- [ ] CI/CD with GitHub Actions

---

## License

MIT — see [LICENSE](LICENSE) for details.