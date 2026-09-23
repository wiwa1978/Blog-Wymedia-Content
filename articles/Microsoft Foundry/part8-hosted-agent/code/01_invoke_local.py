import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).with_name(".env"), override=True)


client = OpenAI(
    base_url=os.getenv("LOCAL_AGENT_BASE_URL", "http://127.0.0.1:8088"),
    api_key="local-development-only",
)

response = client.responses.create(
    input=os.getenv(
        "TEST_PROMPT",
        "Read data/quantum-computing-rag-test.md and summarize how quantum computing differs from classical computing.",
    ),
)

print(response.output_text)
