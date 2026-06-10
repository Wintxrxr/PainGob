# 👹 Pain Goblin

> **Most startup ideas fail because they start with solutions.**
> Pain Goblin starts with pain.

A multi-agent AI system that continuously hunts for startup opportunities by discovering real customer frustrations across online communities — working backwards from actual problems people are already experiencing.

---

## 🧠 Core Philosophy

The internet is a 24/7 complaint machine. Every day, people post about:

- 🔁 Repeated complaints no one has fixed
- 💸 Expensive manual processes begging to be automated
- 🔧 Missing tools they'd pay for immediately
- 💔 Broken workflows destroying productivity
- 😤 Customer frustrations ignored by incumbents
- 🐌 Operational bottlenecks costing real money

Pain Goblin crawls all of it. Identifies what's painful enough to pay to solve. Ranks it. Delivers it to your inbox before you've had your morning coffee.

---

## ⚙️ What It Does

```
1. Collects discussions from Reddit, Hacker News, RSS feeds, and other public sources
2. Identifies recurring complaints, bottlenecks, and unmet needs
3. Runs multiple AI models to independently analyze the same problem
4. Compares model outputs through an arbitration layer
5. Ranks opportunities by severity, frequency, urgency, and business potential
6. Generates structured reports of validated startup and automation opportunities
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                    SOURCES                       │
│                                                  │
│   Reddit    Hacker News    RSS Feeds    +More    │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│               COLLECTORS LAYER                   │
│         Ingests & normalizes raw posts           │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│             POSTGRESQL STORAGE                   │
│         Deduplication · Persistence              │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│               ANALYSIS LAYER                     │
│                                                  │
│        ┌─────────────┬─────────────┐            │
│        │  DeepSeek   │   Gemini    │            │
│        │    Agent    │    Agent    │            │
│        └──────┬──────┴──────┬──────┘            │
│               └──────┬──────┘                   │
└──────────────────────┼──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│             ARBITRATION LAYER                    │
│      Cross-model validation & consensus          │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│           OPPORTUNITY RANKING ENGINE             │
│   Severity · Frequency · Urgency · Monetizability│
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│             REPORTS & ALERTS                     │
│                                                  │
│     📊 Structured Reports    📱 Notifications    │
└─────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Runtime** | Python 3.13 |
| **API Framework** | FastAPI |
| **ORM** | SQLAlchemy |
| **Database** | PostgreSQL |
| **AI — Agent 1** | DeepSeek |
| **AI — Agent 2** | Gemini |
| **Package Manager** | UV |
| **Version Control** | Git + GitHub |

---

## 📁 Project Structure

```
paingoblin/
│
├── analyzers/          # AI model agents
├── arbitration/        # Cross-model comparison logic
├── collectors/         # Reddit, HN, RSS scrapers
├── config/             # Environment & settings management
├── data/               # Raw and processed data
├── database/           # SQLAlchemy models & migrations
├── logs/               # Runtime logs
├── prompts/            # Prompt templates for AI agents
├── reports/            # Generated opportunity reports
├── scheduler/          # Job scheduling
├── scripts/            # Utility scripts
├── services/           # Core business logic
├── tests/              # Test suite
│
├── .env                # Environment variables
├── pyproject.toml      # Project dependencies (UV)
├── README.md
├── ARCHITECTURE.md
└── main.py             # Entry point
```

---

## 🚦 Development Status

### ✅ Completed
- Project architecture & design
- UV environment setup
- PostgreSQL setup
- SQLAlchemy integration
- Configuration management
- GitHub repository setup

### 🔄 In Progress
- Database models
- Reddit collector
- Data pipeline

### 📋 Planned

| Component | Description |
|---|---|
| DeepSeek Analysis Agent | Independent pain signal extraction |
| Gemini Analysis Agent | Independent pain signal extraction |
| Arbitration Engine | Cross-model consensus & conflict resolution |
| Reporting Engine | Structured opportunity report generation |
| Telegram Delivery | Daily push notifications |
| Web Dashboard | Real-time opportunity feed |
| Opportunity Scoring Engine | Multi-factor ranking algorithm |
| Trend Detection | Rising pain signal identification |
| Startup Validation Layer | Market size & competition checks |

---

## 🔮 Vision

The long-term goal is a fully automated startup research engine that continuously discovers, validates, and prioritizes business opportunities using real-world demand signals.

Instead of spending weeks searching for problems manually — founders should wake up every morning to a ranked list of opportunities, each backed by real customer pain.

**No more guessing. No more building in the dark. Just signal.**

---

## 👤 Author

Built by **Karanveer Singh**

*Powered by caffeine, curiosity, and the relentless pursuit of internet complaints.*