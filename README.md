# TalkToDB

TalkToDB is a lightweight, local-first prototype that demonstrates a safe, deterministic
pipeline for translating natural-language database questions into executable SQLite queries.
It was designed to reduce LLM hallucinations via a structured feedback loop and an optional
feature-flagged remote LLM path for production integration.

Repository: https://github.com/manidweep1306/TalkToDB

Key features
- Local-first: runs without external LLMs by default using a deterministic SQL generator.
- Dynamic schema injection: introspects the SQLite database and builds concise schema prompts.
- Self-healing loop: captures SQL execution errors and retries generation (configurable retries).
- FastAPI server: `server.py` exposes a POST `/query` endpoint for integration.
- Tests and CI: unit tests included and a GitHub Actions workflow to run them on push/PR.

Quick start (create virtualenv, install deps):

```bash
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Run the CLI agent:

```bash
python app.py
```

Run the FastAPI server locally:

```bash
uvicorn server:app --reload
# then POST JSON {"question": "Find engineering workers making above 90000"}
# to http://localhost:8000/query
```

Docker
------
Build and run the provided Docker image (uses the FastAPI server):

```bash
docker build -t talktodb:latest .
docker run -p 8000:8000 talktodb:latest
```

Continuous Integration
----------------------
A GitHub Actions workflow is included at `.github/workflows/ci.yml` which installs
dependencies and runs the unit tests on push and pull requests.

Enabling remote LLM (optional)
-------------------------------
Remote LLM usage is feature-flagged. Set the following environment variables to enable it:

- `TALKTODB_USE_LLM=true` — enable remote LLM path
- `TALKTODB_MODEL=gemini-2.0-flash` — model name (default in code)
- `TALKTODB_TEMP=0` — temperature (default 0)

When enabled, the code attempts to import `langchain_google_genai.ChatGoogleGenerativeAI`.
If that package or credentials are missing, the system gracefully falls back to the local generator.

Pushing this repository to your GitHub
-----------------------------------
To push these changes to your repository `https://github.com/manidweep1306/TalkToDB`, run:

```bash
git init
git add --all
git commit -m "Add Docker, CI, server, tests, and README"
git remote add origin https://github.com/manidweep1306/TalkToDB.git
git branch -M main
git push -u origin main
```

If your repository already exists and has commits, prefer pulling first or force-pushing only when
you're sure:

```bash
git pull origin main --rebase
git push origin main
```

Support & Next Steps
--------------------
- Add production-grade LLM integration with credential handling and rate limiting.
- Replace the simple loop with a `StateGraph` implementation and persistent logging.
- Add Docker Compose manifest and a ready-made deployment pipeline (Helm/GKE or ECS).

If you want, I can create a GitHub Actions workflow that builds and pushes the Docker image to
GitHub Packages or Docker Hub next.
