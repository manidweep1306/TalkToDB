import unittest
from app import get_connection, create_sample_db, get_db_schema, llm_invoke, run_agent_once

class TestApp(unittest.TestCase):
    def test_schema(self):
        conn = get_connection()
        create_sample_db(conn)
        s = get_db_schema(conn)
        self.assertIn('Table: employees', s)
        self.assertIn('id (', s)

    def test_llm_invoke(self):
        prompt = "Find engineering workers making above 90000"
        r = llm_invoke(prompt)
        self.assertTrue(hasattr(r, 'content'))
        self.assertIn('SELECT', r.content.upper())

    def test_run_agent_once(self):
        res = run_agent_once("Find engineering workers making above 90000")
        self.assertIn('query_result', res)
        self.assertIsNotNone(res['query_result'])

if __name__ == '__main__':
    unittest.main()
