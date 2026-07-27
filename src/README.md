# Source Code (`src`)

The `src` directory contains the core backend implementation for the **Multi-Agent Quantitative Financial Intelligence Platform**.

The project follows a modular architecture where each package has a clearly defined responsibility, making it easier to develop, test, and extend individual components independently.

---

# Directory Structure

```text
src/
├── ai/
├── analytics/
├── api/
├── database/
└── ingestion/
```

---

# Module Overview

## `ai/`

Contains the AI research layer responsible for generating investment research and orchestrating AI-assisted workflows.

Includes:

- AI agents
- Prompt templates
- Structured schemas
- Financial research tools
- Research services

Primary responsibility:

> Transform structured financial data into AI-generated research reports.

---

## `analytics/`

Contains the quantitative research engine and analytical models.

Includes:

- Fundamental analysis
- Technical analysis
- Factor models
- Statistical models
- Machine learning models
- Alpha models
- Portfolio construction
- Portfolio optimization
- Backtesting
- Research engine orchestration

Primary responsibility:

> Generate quantitative insights and portfolio recommendations from financial data.

---

## `api/`

Contains the FastAPI backend used by the frontend application.

Includes endpoints for:

- Company research
- Portfolio research
- Quantitative analytics
- Data queries

Primary responsibility:

> Expose the platform's functionality through a REST API.

---

## `database/`

Contains the database layer.

Includes:

- SQLAlchemy ORM models
- Database connection management
- Query services
- Data storage utilities

Primary responsibility:

> Store and retrieve structured financial data.

---

## `ingestion/`

Contains financial data ingestion pipelines.

Current data sources include:

- Market data
- SEC filings
- Financial statements
- Financial news

Primary responsibility:

> Collect, clean, and standardize financial data for downstream analysis.

---

# High-Level Data Flow

```text
Financial Data Sources
          │
          ▼
     ingestion/
          │
          ▼
     database/
          │
          ▼
     analytics/
          │
          ▼
         ai/
          │
          ▼
        api/
          │
          ▼
     React Frontend
```

---

# Design Principles

The backend is organized around several core software engineering principles:

- Modular architecture
- Separation of concerns
- Reusable services
- Layered design
- Clear data flow
- Extensible analytics pipeline

Each module has a single primary responsibility while exposing reusable functionality to the rest of the platform.
