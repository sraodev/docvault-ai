import os
from dotenv import load_dotenv
from app.services.ai_service import AIService
from app.core.config import OPENROUTER_API_KEY

# Load env vars explicitly to be sure
load_dotenv()

print(f"OpenRouter Key present: {bool(OPENROUTER_API_KEY)}")

service = AIService()
print("Attempting to generate summary...")
try:
    summary = service.generate_summary("This is a test document content that is long enough to be summarized.")
    print(f"Result: {summary}")
except Exception as e:
    print(f"Caught exception in test script: {e}")
