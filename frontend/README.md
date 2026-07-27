# Frontend (`frontend`)

The frontend provides the user interface for the **Multi-Agent Quantitative Financial Intelligence Platform**.

Built with **React**, **TypeScript**, and **Vite**, it allows users to generate AI-assisted company and portfolio research reports through an interactive web application.

---

# Directory Structure

```text
frontend/
├── src/
│   ├── api/
│   ├── components/
│   ├── pages/
│   ├── pdf/
│   └── types/
```

---

# Module Overview

## `api/`

Contains API clients responsible for communicating with the FastAPI backend.

Primary responsibility:

> Send research requests and retrieve structured results.

---

## `components/`

Reusable React components used throughout the application.

Includes:

- Company research components
- Portfolio research components
- Shared UI components

Primary responsibility:

> Build reusable user interface elements.

---

## `pages/`

Top-level application pages.

Current pages include:

- Home page
- Company research
- Portfolio research

Primary responsibility:

> Organize application views and user workflows.

---

## `pdf/`

Contains React PDF templates used to generate downloadable research reports.

Includes:

- Company reports
- Portfolio reports
- Shared PDF components
- Styling utilities

Primary responsibility:

> Generate professional PDF investment research reports.

---

## `types/`

Shared TypeScript interfaces used throughout the frontend.

Primary responsibility:

> Maintain type safety and consistent data structures.

---

# Frontend Responsibilities

The frontend is responsible for:

- Collecting user inputs
- Sending requests to the backend API
- Displaying research results
- Rendering interactive dashboards
- Generating downloadable PDF reports

The application communicates with the backend through a REST API exposed by the FastAPI server.
