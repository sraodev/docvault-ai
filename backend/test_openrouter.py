import os
import requests
import json

API_KEY = "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"

print("Testing OpenRouter Key...")

try:
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000", 
        },
        data=json.dumps({
            "model": "anthropic/claude-3-haiku", 
            "messages": [
                {"role": "user", "content": "Hello, are you working?"}
            ]
        })
    )
    
    if response.status_code == 200:
        print("Success!")
        print(response.json()['choices'][0]['message']['content'])
    else:
        print(f"Failed with status {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"Error: {e}")
