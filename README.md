# Personal AI Financial Advisor

A multi-agent AI-powered personal financial advisor with intent routing, hybrid memory, and dual market data providers. Built with LangGraph, FastAPI, and Next.js 14.

This system is for **educational and research purposes only** — not intended for real trading or investment.

## Architecture Overview

```
User → Chat API → AgentState → LangGraph
                                 │
                        start_node
                                 │
                        Intent Router (LLM classifies)
                                 │
                        route_intent (conditional)
                        /    |    |    |    \
                  stock  port  disc  strat gen
                  anal   anal  overy  ad    fin
```

### Intent Routing

The Intent Router (LLM-powered) classifies each user question into one of 5 intents:

| Intent | Triggers | Workflow Path |
|--------|----------|---------------|
| `stock_analysis` | "Should I buy NVDA?" | PFA → Fan-out (4 analysts) → Risk Manager → Portfolio Manager |
| `portfolio_analysis` | "Analyze my portfolio risk" | Risk Manager → Portfolio Analysis Agent |
| `stock_discovery` | "Suggest small cap stocks" | Stock Discovery Agent |
| `strategy_advice` | "How should I save for retirement?" | PFA (direct to END) |
| `general_finance` | "What is a PE ratio?" | RAG Agent |

The router also extracts tickers from the question and overrides any dummy frontend-supplied tickers.

### Workflow Graph

```
start_node ──→ intent_router
                  │
                  │ (conditional: route_intent)
                  ├──→ stock_analysis
                  │       └──→ pfa ──→ fan_out ──→ 4 analysts ──→ risk_manager ──→ portfolio_manager ──→ END
                  │                                          (valuation, fundamentals, technicals, sentiment)
                  │
                  ├──→ portfolio_analysis
                  │       └──→ risk_manager ──→ portfolio_analysis_agent ──→ END
                  │
                  ├──→ stock_discovery
                  │       └──→ stock_discovery_agent ──→ fundamentals ──→ risk_manager ──→ END
                  │
                  ├──→ strategy_advice
                  │       └──→ pfa ──→ END
                  │
                  └──→ general_finance
                          └──→ rag_agent ──→ END
```

### Agents (28 total)

**Hedge Fund Analysts (14):**
Aswath Damodaran, Ben Graham, Bill Ackman, Cathie Wood, Charlie Munger, Michael Burry, Mohnish Pabrai, Nassim Taleb, Peter Lynch, Phil Fisher, Rakesh Jhunjhunwala, Stanley Druckenmiller, Warren Buffett, Growth Analyst

**Data Analysts (4):**
Fundamentals Analyst, Technical Analyst, Valuation Analyst, Sentiment Analyst

**Personal Advisor Agents (6):**
Personal Financial Advisor, Risk Manager, Portfolio Manager, Portfolio Analysis Agent, Stock Discovery Agent, RAG Agent

**System Agents (2):**
Intent Router, News Sentiment Analyst

### State Flow

Every agent reads and writes to a shared `AgentState` dict:

```python
{
  "question": str,
  "data": {
    "tickers": [...],
    "portfolio": {...},
    "analyst_signals": {},
    "start_date": "...",
    "end_date": "..."
  },
  "metadata": {"show_reasoning": bool, "model": str},
  "routing_decision": {"intent": str, "tickers": [...], "confidence": float, ...}
}
```

## Data Flow

### Market Data Provider

Unified data layer with try-Yahoo-then-fallback strategy:

```
Agent Code
    │
    ▼
Module-level convenience functions
(get_prices, get_financial_metrics, get_company_news, etc.)
    │
    ▼
MarketDataProvider (orchestrator)
    │
    ├── YahooFinanceProvider (primary — free, ETFs work)
    │       ├── yfinance.Ticker.history() → Price[]
    │       ├── yfinance.Ticker.info → FinancialMetrics
    │       └── yfinance.Ticker.news → CompanyNews[]
    │
    └── FinancialDatasetsProvider (fallback — paid, richer data)
            ├── src.tools.api.get_prices()
            ├── src.tools.api.get_financial_metrics()
            ├── src.tools.api.get_company_news()
            ├── src.tools.api.get_market_cap()
            ├── src.tools.api.search_line_items()
            └── src.tools.api.get_insider_trades()
```

- Yahoo Finance handles ETFs (SPY, QQQ, VOO, DIA) that FinancialDatasets.ai blocks with HTTP 402.
- In-memory caching (`_PRICE_CACHE`, `_METRICS_CACHE`, `_NEWS_CACHE`) — cached per (ticker, date_range) key.
- Agents never pass `api_key` — the provider reads `FINANCIAL_DATASETS_API_KEY` from `os.environ`.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | Next.js 14 + React 18 + TypeScript |
| **AI Orchestration** | LangGraph (LangChain) |
| **LLMs** | DeepSeek, Groq, Claude, GPT-4o, Ollama (local) |
| **Market Data** | Yahoo Finance (primary) + FinancialDatasets.ai (fallback) |
| **Database** | PostgreSQL / SQLite |
| **Vector Store** | ChromaDB (conversation memory, user profiles) |
| **Auth** | JWT (python-jose) + bcrypt |
| **CI/Tracing** | LangSmith |

## Project Structure

```
├── app/
│   ├── backend/           # FastAPI backend
│   │   ├── main.py        # App creation, CORS, startup
│   │   ├── routes/        # API route handlers (chat, auth, portfolio, etc.)
│   │   ├── services/      # Graph builder, market data provider, Ollama
│   │   └── database/      # SQLAlchemy models + migrations
│   └── frontend/          # Next.js 14 frontend
│       └── src/
│           ├── app/       # Pages (dashboard, advisor, portfolio, etc.)
│           ├── components/# UI components
│           └── lib/       # API client, utilities
├── src/
│   ├── main.py            # Workflow builder + CLI entry point
│   ├── agents/            # 28 agent implementations
│   ├── tools/             # Market data API tools (FinancialDatasets.ai)
│   ├── data/              # Pydantic models (Price, FinancialMetrics, etc.)
│   ├── graph/             # AgentState TypedDict
│   ├── memory/            # ChromaDB vector store
│   ├── db/                # User/portfolio ORM models
│   ├── llm/               # Model configuration
│   └── utils/             # Analysts config, display, LLM helper
├── v2/                    # Quantitative pipeline (signals, risk, optimizer)
└── docker/                # Docker Compose files
```

## Prerequisites

- Python 3.12+
- Node.js 18+
- Poetry (`curl -sSL https://install.python-poetry.org | python3 -`)
- API keys (see below)

## Installation

### 1. Clone and set up API keys

```bash
git clone <repo-url>
cd personal_financial_advisor
cp .env.example .env
```

Edit `.env` with your keys. At minimum, set one LLM key + `FINANCIAL_DATASETS_API_KEY`:

```env
OPENAI_API_KEY=sk-...
# or
DEEPSEEK_API_KEY=...
# or
GROQ_API_KEY=...

FINANCIAL_DATASETS_API_KEY=your-key-here
```

### 2. Install backend dependencies

```bash
poetry install
```

### 3. Install frontend dependencies

```bash
cd app/frontend
npm install
cd ../..
```

## Running

### Start the backend

```bash
poetry run uvicorn app.backend.main:app --reload --port 8000
```

### Start the frontend (separate terminal)

```bash
cd app/frontend
npm run dev
```

Open `http://localhost:3000`, register an account, and start chatting with the AI advisor.

### CLI mode (standalone, no frontend)

```bash
poetry run python src/main.py --ticker AAPL,MSFT,NVDA
```

Optional flags: `--start-date`, `--end-date`, `--ollama` (for local LLMs), `--show-reasoning`.

### Backtesting

```bash
poetry run python src/backtester.py --ticker AAPL,MSFT,NVDA
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Login (returns JWT) |
| POST | `/api/v1/chat/` | Chat with AI advisor |
| GET | `/api/v1/portfolio/` | Get portfolio holdings |
| POST | `/api/v1/portfolio/holdings` | Add holding |
| GET | `/api/v1/recommendations/history` | Past recommendations |
| GET | `/api/v1/users/me` | Current user profile |

## Key Design Decisions

1. **Intent Router as entry point** — Only executes agents relevant to the user's intent, saving tokens and reducing latency.
2. **Yahoo Finance primary** — Free and handles ETFs (SPY, QQQ, VOO) that FinancialDatasets.ai blocks on free tier.
3. **Router extracts tickers** — The LLM extracts tickers from natural language ("should I buy NVIDIA?" → NVDA), overriding any frontend-supplied defaults.
4. **LangGraph conditional edges** — `route_intent()`, `route_from_pfa()`, `route_from_risk_manager()` dynamically select the next node based on state.
5. **Hybrid memory** — ChromaDB (semantic + conversation) + PostgreSQL (structured profile/portfolio data).
6. **JWT auth** — Bearer tokens stored in `localStorage` key `advisor_token`.

## Disclaimer

This project is for **educational and research purposes only**. Not intended for real trading or investment. No investment advice or guarantees provided. Past performance does not indicate future results.
