import os
import re
import sqlite3
import pandas as pd
from typing import TypedDict, Optional, Dict, Any

# 1. LOCAL DATABASE SETUP (In-Memory Sandbox)
def create_sample_db(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY,
        name TEXT,
        department TEXT,
        salary INTEGER,
        hire_date TEXT
    )
    """)

    # Populate sample data if empty
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        mock_data = [
            (1, "Alice", "Engineering", 95000, "2023-01-15"),
            (2, "Bob", "Engineering", 105000, "2022-05-20"),
            (3, "Charlie", "Marketing", 70000, "2024-02-10"),
            (4, "David", "Sales", 85000, "2021-11-01"),
            (5, "Emma", "Engineering", 123000, "2020-09-14"),
            (6, "Fiona", "Support", 62000, "2023-08-03"),
            (7, "George", "Finance", 99000, "2021-03-22"),
            (8, "Hannah", "Engineering", 88000, "2024-01-09"),
            (9, "Ivan", "Marketing", 76000, "2022-12-18"),
            (10, "Julia", "Sales", 91000, "2020-06-30")
        ]
        cursor.executemany("INSERT INTO employees VALUES (?,?,?,?,?)", mock_data)
        conn.commit()


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    if db_path:
        return sqlite3.connect(db_path, check_same_thread=False)
    return sqlite3.connect(":memory:", check_same_thread=False)


def get_db_schema(conn: sqlite3.Connection) -> str:
    """Introspect sqlite schema and return a concise schema string for prompts."""
    cur = conn.cursor()
    schema_parts = []
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
    for name, sql in cur.fetchall():
        cur.execute(f"PRAGMA table_info('{name}')")
        cols = [f"{r[1]} ({r[2]})" for r in cur.fetchall()]
        schema_parts.append(f"Table: {name}\nColumns: {', '.join(cols)}")
    return "\n\n".join(schema_parts)


# initialize default in-memory DB for direct runs
conn = get_connection()
create_sample_db(conn)
DB_SCHEMA = get_db_schema(conn)

# 2. AGENT STATE DEFINITION
class AgentState(TypedDict):
    question: str
    generated_sql: Optional[str]
    query_result: Optional[str]
    error_message: Optional[str]
    retry_count: int

# Lightweight local "LLM" substitute: deterministic SQL generation
def llm_invoke(prompt: str) -> Dict[str, Any]:
    # This is a tiny heuristic-based generator to produce executable SQLite SQL.
    # It handles a few common intent types so the demo returns different result shapes.
    dept = None
    salary_threshold = None
    order_by = None

    q = prompt.lower()
    if "engineering" in q:
        dept = "Engineering"

    m = re.search(r"above\s*(\d{2,7})", q)
    if m:
        salary_threshold = int(m.group(1))

    if "hire day" in q or "hire_date" in q or "hire date" in q or "hire-day" in q:
        order_by = "hire_date"

    if any(phrase in q for phrase in ["how many", "count", "number of"]):
        where_clauses = []
        if dept:
            where_clauses.append(f"department = '{dept}'")
        if salary_threshold is not None:
            where_clauses.append(f"salary > {salary_threshold}")
        where = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"SELECT COUNT(*) AS employee_count FROM employees{where};"
    elif any(phrase in q for phrase in ["average salary", "avg salary", "mean salary"]):
        where_clauses = []
        if dept:
            where_clauses.append(f"department = '{dept}'")
        if salary_threshold is not None:
            where_clauses.append(f"salary > {salary_threshold}")
        where = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"SELECT AVG(salary) AS average_salary FROM employees{where};"
    elif any(phrase in q for phrase in ["show all employees", "list all employees", "all employees"]):
        sql = "SELECT * FROM employees;"
        if order_by:
            sql = f"SELECT * FROM employees ORDER BY {order_by};"
    elif dept or salary_threshold:
        where_clauses = []
        if dept:
            where_clauses.append(f"department = '{dept}'")
        if salary_threshold is not None:
            where_clauses.append(f"salary > {salary_threshold}")
        where = " AND ".join(where_clauses)
        order = f" ORDER BY {order_by}" if order_by else ""
        sql = f"SELECT * FROM employees WHERE {where}{order};"
    else:
        sql = "SELECT * FROM employees LIMIT 10;"

    class Resp:
        def __init__(self, content: str):
            self.content = content

    return Resp(sql)


# Optional remote LLM wiring (feature-flagged)
USE_REMOTE_LLM = os.getenv("TALKTODB_USE_LLM", "false").lower() in ("1", "true", "yes")
REMOTE_LLM_AVAILABLE = False
RemoteLLMClass = None
try:
    if USE_REMOTE_LLM:
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
        REMOTE_LLM_AVAILABLE = True
        RemoteLLMClass = ChatGoogleGenerativeAI
except Exception:
    REMOTE_LLM_AVAILABLE = False


def remote_llm_invoke(prompt: str):
    """Call the configured remote LLM. Caller must ensure REMOTE_LLM_AVAILABLE."""
    model_name = os.getenv("TALKTODB_MODEL", "gemini-2.0-flash")
    temp = float(os.getenv("TALKTODB_TEMP", "0"))
    llm = RemoteLLMClass(model=model_name, temperature=temp)
    resp = llm.invoke(prompt)
    return resp


def llm_dispatch(prompt: str):
    """Dispatch to remote LLM if enabled and available, otherwise use local heuristic."""
    if USE_REMOTE_LLM and REMOTE_LLM_AVAILABLE:
        try:
            resp = remote_llm_invoke(prompt)
            # Expect an object with .content
            class R:
                def __init__(self, content):
                    self.content = content
            return R(resp.content if hasattr(resp, "content") else str(resp))
        except Exception:
            # fallback to local generator on any remote error
            return llm_invoke(prompt)
    return llm_invoke(prompt)


def run_agent_once(question: str, max_retries: int = 3, conn_override: Optional[sqlite3.Connection] = None):
    """Run the agent loop once (with internal retries) and return final summary dict."""
    local_conn = conn_override or conn

    state: AgentState = {"question": question, "retry_count": 0}

    # inject live schema into prompt state if needed
    state_schema = get_db_schema(local_conn)

    while True:
        gen = generate_sql(state)
        state.update(gen)

        # execute against provided connection
        try:
            df = pd.read_sql_query(state["generated_sql"], local_conn)
            exec_res = {"query_result": df.to_string(), "error_message": None}
        except Exception as e:
            exec_res = {"error_message": str(e)}

        state.update(exec_res)

        step = route_next_step(state)
        if step == "retry":
            if state.get("retry_count", 0) >= max_retries:
                break
            continue
        if step == "finalize":
            summary = synthesize_summary(state)
            return {**summary, "generated_sql": state.get("generated_sql")}
        break
    return {"query_result": None, "error_message": state.get("error_message"), "generated_sql": state.get("generated_sql")}

# 3. GRAPH NODES (The Reasoning Engine)
def generate_sql(state: AgentState):
    """Translates text to SQL, using error logs as feedback loops if present."""
    error_feedback = ""
    if state.get("error_message"):
        error_feedback = f"\n\nCRITICAL ERROR FEEDBACK FROM PREVIOUS ATTEMPT:\n{state['error_message']}\nReview the schema columns closely and correct your query syntax."

    prompt = f"""
    You are an expert Data Analyst Agent. Write an executable SQLite query to answer the user's question.
    
    Database Schema:
    {DB_SCHEMA}
    
    User Question: {state['question']}{error_feedback}
    
    Return ONLY valid, raw executable SQL. Do not include markdown wraps (like ```sql) or extra text.
    """
    
    response = llm_dispatch(prompt)
    clean_sql = response.content.strip().replace("```sql", "").replace("```", "")

    print(f"\n[Agent Generated SQL]: {clean_sql}")
    return {"generated_sql": clean_sql, "retry_count": state.get("retry_count", 0) + 1}


def execute_sql(state: AgentState):
    """Executes query inside a try-except block to capture raw tracebacks."""
    try:
        df = pd.read_sql_query(state["generated_sql"], conn)
        return {"query_result": df.to_string(), "error_message": None}
    except Exception as e:
        print(f" [DB Execution Failed]: {str(e)}")
        return {"error_message": str(e)}


def synthesize_summary(state: AgentState):
    """Takes structural results and frames a human-readable answer."""
    prompt = f"""
    Analyze this database dump to answer the user's inquiry:
    Inquiry: {state['question']}
    
    Data Block:
    {state['query_result']}
    
    Provide a professional, clear conversational overview.
    """
    # Produce a concise summary from the query result (no external LLM used)
    df_text = state.get("query_result") or ""
    summary = "No results found." if not df_text.strip() else f"Query returned:\n{df_text}"
    return {"query_result": summary}

# 4. Simple workflow loop (replaces external StateGraph dependency)
def route_next_step(state: AgentState) -> str:
    if state.get("error_message"):
        if state.get("retry_count", 0) >= 3:
            print("\n[Max Retries Exhausted]: Abandoning loop.")
            return "stop"
        print("[Self-Healing Activated]: Rewriting query based on error feedback...")
        return "retry"
    return "finalize"

# 5. EXECUTION HARNESS
if __name__ == "__main__":
    print("Initializing TalkToDB Agent Session...")

    # Intentionally vague phrasing using 'hire day' to test column resolution mapping
    user_prompt = "Find engineering workers making above 90000, sorted by their hire day."

    state: AgentState = {"question": user_prompt, "retry_count": 0}

    while True:
        gen = generate_sql(state)
        state.update(gen)

        exec_res = execute_sql(state)
        state.update(exec_res)

        step = route_next_step(state)
        if step == "retry":
            # loop will regenerate SQL with updated retry_count and any error_message
            continue
        if step == "finalize":
            summary = synthesize_summary(state)
            print("\n================ FINAL REPORT ================")
            print(summary["query_result"])
            break
        print("Stopping after repeated failures.")
        print(state.get("error_message"))
        break