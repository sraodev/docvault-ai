import anthropic
from ..core.config import ANTHROPIC_API_KEY

class AIService:
    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def generate_summary(self, text: str) -> str:
        if not self.client:
            return "This is a MOCK summary. The document appears to contain information about..." + text[:100] + "..."
        
        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[
                    {"role": "user", "content": f"Please provide a concise summary of the following document:\n\n{text[:10000]}"}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"AI API Error (Summary): {e}")
            return "Error generating summary via AI."

    def generate_markdown(self, text: str) -> str:
        if not self.client:
            return f"# Mock Markdown\n\nThis is a generated markdown representation.\n\n## Extracted Content\n{text[:500]}..."

        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": f"Convert the following document content into clean, well-structured Markdown. Do not include any preamble, just the markdown:\n\n{text[:15000]}"}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"AI API Error (Markdown): {e}")
            return f"# Error\nCould not generate markdown. \n\nOriginal content preview:\n{text[:500]}"
