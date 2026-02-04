import os
from dotenv import load_dotenv
import requests

load_dotenv()

key = os.getenv("GROQ_API_KEY")
print(f"Key found: {bool(key)}")

if key:
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": "Say hello"}],
            "max_tokens": 50
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")