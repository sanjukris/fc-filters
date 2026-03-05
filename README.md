## Find Care Filters

Split architecture with:
- `backend/`: FastAPI service for loading CSVs and ranking fuzzy matches.
- `ui/`: Streamlit app that calls backend `/search` as user types.

## Setup

```bash
uv sync
```

This uses the existing single `.venv` in the project root.

## Run Backend

```bash
uv run uvicorn backend.main:app --reload
```

Backend URL: `http://127.0.0.1:8000`

## Run UI

In another terminal:

```bash
uv run streamlit run ui/main.py
```

UI defaults to backend `http://127.0.0.1:8000`.
To point to a different backend:

```bash
FILTER_API_BASE_URL=http://host:port uv run streamlit run ui/main.py
```

## React UI (Additional Frontend)

`react-ui/` is a React + Vite frontend with a Google-like search experience and blue theme.
It calls the same backend `/search` endpoint and starts querying only after the input has more than 3 characters.

Install once:

```bash
cd react-ui
npm install
```

Run in dev mode:

```bash
cd react-ui
npm run dev
```

Optional backend URL override:

```bash
cd react-ui
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

## Logging

Default log level is `INFO`.

- Backend log level:
```bash
FILTER_LOG_LEVEL=DEBUG uv run uvicorn backend.main:app --reload
```

- UI log level:
```bash
FILTER_UI_LOG_LEVEL=DEBUG uv run streamlit run ui/main.py
```
