from .providers import AIProviderFactory

class AIService:
    def __init__(self):
        self.provider = AIProviderFactory.get_provider()

    def generate_summary(self, text: str) -> str:
        try:
            return self.provider.generate_summary(text)
        except Exception as e:
            print(f"AI Service Error: {e}")
            # Fallback to mock if provider fails? Or just return error message
            return "Error generating summary via AI."

    def generate_markdown(self, text: str) -> str:
        try:
            return self.provider.generate_markdown(text)
        except Exception as e:
            print(f"AI Service Error: {e}")
            return f"# Error\nCould not generate markdown. \n\nOriginal content preview:\n{text[:500]}"
