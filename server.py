from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
from app import handle_question

app = FastAPI()

class QueryRequest(BaseModel):
    question: str

HOME_PAGE = """
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>TalkToDB</title>
        <style>
            :root { color-scheme: light; }
            body {
                margin: 0;
                font-family: Arial, Helvetica, sans-serif;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 45%, #334155 100%);
                color: #e2e8f0;
                min-height: 100vh;
            }
            .wrap {
                max-width: 960px;
                margin: 0 auto;
                padding: 48px 20px;
            }
            .card {
                background: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 20px;
                padding: 28px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            }
            h1 { margin: 0 0 8px; font-size: 40px; }
            p { color: #cbd5e1; line-height: 1.6; }
            textarea {
                width: 100%;
                min-height: 120px;
                resize: vertical;
                border-radius: 14px;
                border: 1px solid #475569;
                background: #0f172a;
                color: #e2e8f0;
                padding: 14px;
                font-size: 16px;
                box-sizing: border-box;
            }
            button {
                margin-top: 12px;
                border: 0;
                border-radius: 12px;
                background: #38bdf8;
                color: #082f49;
                font-weight: 700;
                padding: 12px 18px;
                cursor: pointer;
            }
            button:hover { filter: brightness(1.05); }
            pre {
                white-space: pre-wrap;
                background: #020617;
                border: 1px solid #334155;
                border-radius: 14px;
                padding: 16px;
                overflow: auto;
            }
            .hint { font-size: 14px; color: #94a3b8; }
            .grid { display: grid; gap: 16px; }
        </style>
    </head>
    <body>
        <div class="wrap">
            <div class="card">
                <h1>TalkToDB</h1>
                <p>Ask questions in plain English and query the sample SQLite database.</p>
                <textarea id="question">Find engineering workers making above 90000, sorted by their hire day.</textarea>
                <br />
                <button onclick="runQuery()">Run Query</button>
                <p class="hint">This page calls <code>/query</code> and renders the result below.</p>
                                <p class="hint" id="status">Ready.</p>
                                <div class="grid">
                                    <div>
                                        <p class="hint">Generated SQL</p>
                                        <pre id="sql">Loading initial SQL...</pre>
                                    </div>
                                    <div>
                                        <p class="hint">Result</p>
                                        <pre id="result">Loading initial result...</pre>
                                    </div>
                                </div>
            </div>
        </div>
        <script>
            async function runQuery() {
                const question = document.getElementById('question').value;
                const resultBox = document.getElementById('result');
                const sqlBox = document.getElementById('sql');
                const statusBox = document.getElementById('status');
                resultBox.textContent = 'Running...';
                sqlBox.textContent = 'Generating SQL...';
                statusBox.textContent = 'Fetching live result...';
                try {
                    const response = await fetch('/query', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ question })
                    });
                    const data = await response.json();
                    sqlBox.textContent = data.generated_sql || '(no SQL returned)';
                    resultBox.textContent = data.query_result || data.error_message || JSON.stringify(data, null, 2);
                    statusBox.textContent = 'Last updated: ' + new Date().toLocaleString();
                } catch (error) {
                    resultBox.textContent = 'Request failed: ' + error;
                    sqlBox.textContent = 'Request failed.';
                    statusBox.textContent = 'Request failed.';
                }
            }

            window.addEventListener('DOMContentLoaded', () => {
                runQuery();
            });
        </script>
    </body>
</html>
"""

@app.get('/', response_class=HTMLResponse)
def home():
        return HOME_PAGE

@app.post('/query')
async def query(req: QueryRequest):
    # API routing lives in server.py; execution logic is delegated to app.py.
    return handle_question(req.question)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
