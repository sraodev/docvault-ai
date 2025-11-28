from typing import Optional
from .providers import AIProviderFactory
from .interfaces import IAIService

class AIService(IAIService):
    """
    AI service implementation.
    Handles AI operations - summary generation, markdown generation.
    Follows Single Responsibility Principle.
    """
    def __init__(self):
        self.provider = AIProviderFactory.get_provider()

    def generate_summary(self, text: str) -> Optional[str]:
        try:
            result = self.provider.generate_summary(text)
            # Check if the result contains error messages and return None instead
            if result and ("Error generating summary" in result or "Error code:" in result):
                print(f"AI Service Error: Summary contains error message")
                return None
            return result
        except Exception as e:
            error_str = str(e)
            print(f"AI Service Error: {error_str}")
            # Return None instead of error message - let the frontend handle the display
            return None

    def generate_markdown(self, text: str) -> Optional[str]:
        try:
            result = self.provider.generate_markdown(text)
            # Check if the result contains error messages
            if result and ("Error" in result and "Error code:" in result):
                print(f"AI Service Error: Markdown contains error message")
                return None
            return result
        except Exception as e:
            error_str = str(e)
            print(f"AI Service Error: {error_str}")
            # Return None instead of error message
            return None
