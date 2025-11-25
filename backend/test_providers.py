import os
from dotenv import load_dotenv
from app.services.ai_service import AIService
from app.core.config import AI_PROVIDER

# Load env vars explicitly to be sure
load_dotenv()

print(f"Current Provider: {AI_PROVIDER}")

service = AIService()
print(f"Service Provider Class: {service.provider.__class__.__name__}")

print("Attempting to generate summary...")
try:
    summary = service.generate_summary("This is a test document content that is long enough to be summarized.")
    print(f"Result: {summary}")
except Exception as e:
    print(f"Caught exception in test script: {e}")
