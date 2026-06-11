# TalkToDB

TalkToDB is a local-first Natural Language to SQL demo built with Python, SQLite, and FastAPI.
It converts plain-English questions into executable SQL, runs the query, and returns results.

## Project Objectives

- Provide a simple NL-to-SQL workflow that works out of the box.
- Keep the default path deterministic and offline-friendly.
- Support an optional remote LLM integration via feature flags.
- Expose both API and web UI entry points.

## Features

- SQLite sample database with employee data.
- Automatic schema introspection for SQL generation context.
- Retry-based self-healing loop for SQL execution errors.
- FastAPI service with:
	- `GET /` simple web UI
	- `POST /query` question-to-result endpoint
- Unit tests with GitHub Actions CI.
- Docker support for containerized runs.

## Tech Stack

- Python
- FastAPI
- Pandas
- SQLite
- Uvicorn
- GitHub Actions
- Docker

## Repository Structure

```text
.
|-- app.py
|-- server.py
|-- requirements.txt
|-- Dockerfile
|-- tests/
|   |-- __init__.py
|   `-- test_app.py
`-- .github/workflows/
		|-- ci.yml
		`-- docker-publish.yml
```

## How It Works

1. A user asks a natural-language question.
2. The app inspects database schema metadata.
3. The SQL generator produces a candidate SQLite query.
4. The query is executed.
5. On error, the app retries with error-informed regeneration.
6. On success, rows are returned as text output.

## Setup

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Running the Project

### Run FastAPI Server

```bash
uvicorn server:app --reload
```

Open:

- `http://localhost:8000` for the built-in web page
- `POST http://localhost:8000/query` for API usage

### API Request Example

```bash
curl -X POST "http://localhost:8000/query" \
	-H "Content-Type: application/json" \
	-d "{\"question\":\"Find engineering workers making above 90000\"}"
```

Sample JSON response shape:

```json
{
	"generated_sql": "SELECT * FROM employees WHERE department = 'Engineering' AND salary > 90000;",
	"query_result": "...",
	"error_message": null
}
```

## Optional Remote LLM Mode

By default, TalkToDB uses a local deterministic SQL generator.
To enable remote LLM calls, set:

- `TALKTODB_USE_LLM=true`
- `TALKTODB_MODEL=gemini-2.0-flash`
- `TALKTODB_TEMP=0`

If the remote LLM package or credentials are unavailable, the app falls back to the local path.

## Docker

Build and run:

```bash
docker build -t talktodb:latest .
docker run -p 8000:8000 talktodb:latest
```

## Testing

Run unit tests:

```bash
python -m unittest -v
```

## CI/CD

- `.github/workflows/ci.yml`: installs dependencies and runs tests on push/PR.
- `.github/workflows/docker-publish.yml`: builds Docker image and conditionally publishes when DockerHub secrets exist.

## License

No license file is currently included in this repository.
