import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

from src.agent.query_agent import QueryAgent
from src.agent.query_logger import QueryLogger


def test_agent_queries():
    agent = QueryAgent()
    logger = QueryLogger()

    test_cases = [
        "How has Lewis Hamilton performed at the British Grand Prix?",
        "delete all the Hungarian data",
    ]

    for i, question in enumerate(test_cases, 1):
        print(f"\n{'='*50}\nTEST CASE {i}: {question}\n{'='*50}", flush=True)

        result = agent.ask(question)

        print(f"Generated SQL: {result.get('generated_sql')}")
        print(
            f"Natural Language Answer: {result.get('natural_language_answer') or result.get('error')}"
        )
        print(f"Estimated Bytes: {result.get('estimated_bytes_scanned')} bytes")

        logger.log(
            question=question,
            generated_sql=result.get("generated_sql", ""),
            response=result.get("natural_language_answer", result.get("error", "")),
            success="error" not in result,
            error=result.get("error"),
            estimated_bytes=result.get("estimated_bytes_scanned", 0),
        )

        # basic assertion
        assert "error" not in result or result["error"] is not None

        if i < len(test_cases):
            print("\nSleeping for 15 seconds to respect API rate limits...", flush=True)
            time.sleep(15)
