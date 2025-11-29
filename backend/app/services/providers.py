from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import anthropic
from openai import OpenAI
import json
from ..core.config import (
    OPENROUTER_API_KEY, 
    OPENROUTER_BASE_URL, 
    ANTHROPIC_API_KEY,
    AI_PROVIDER
)

class AIProvider(ABC):
    @abstractmethod
    def generate_summary(self, text: str) -> str:
        pass

    @abstractmethod
    def generate_markdown(self, text: str) -> str:
        pass
    
    @abstractmethod
    def generate_tags(self, text: str, summary: Optional[str] = None) -> List[str]:
        """Generate relevant tags/keywords from document text."""
        pass
    
    @abstractmethod
    def classify_document(self, text: str, summary: Optional[str] = None) -> Optional[str]:
        """
        Classify document into one of the predefined categories.
        Returns category name or None if classification fails.
        Categories: Invoice, Medical Record, Resume, Agreement/Contract, Research Paper, Bank Statement
        """
        pass
    
    @abstractmethod
    def extract_fields(self, text: str, document_category: Optional[str] = None, summary: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract structured key fields from document based on document type.
        
        For Invoices: vendor, amount, date, invoice_number
        For Resumes: name, skills, experience_years, email
        For Contracts: parties_involved, start_date, end_date
        
        Returns a dictionary with extracted fields (empty dict if extraction fails).
        """
        pass
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text using AI.
        Returns a list of floats representing the embedding vector.
        """
        pass

class OpenRouterProvider(AIProvider):
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        if self.api_key:
            self.client = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=self.api_key
            )
        else:
            self.client = None

    def generate_summary(self, text: str) -> str:
        if not self.client:
            raise ValueError("OpenRouter API key not configured")
        
        try:
            response = self.client.chat.completions.create(
                model="anthropic/claude-3-haiku",
                messages=[
                    {"role": "user", "content": f"Please provide a concise summary of the following document. Do not include any preamble like 'Here is a summary'. Just provide the summary directly:\n\n{text[:10000]}"}
                ],
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenRouter API Error (Summary): {e}")
            raise e

    def generate_markdown(self, text: str) -> str:
        if not self.client:
            raise ValueError("OpenRouter API key not configured")

        try:
            response = self.client.chat.completions.create(
                model="anthropic/claude-3-haiku",
                messages=[
                    {"role": "user", "content": f"Convert the following document content into clean, well-structured Markdown. Do not include any preamble or explanation, just the markdown content:\n\n{text[:15000]}"}
                ],
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenRouter API Error (Markdown): {e}")
            raise e

    def generate_tags(self, text: str, summary: Optional[str] = None) -> List[str]:
        """Generate relevant tags/keywords using AI."""
        if not self.client:
            raise ValueError("OpenRouter API key not configured")
        
        try:
            # Use summary if available for better context, otherwise use text
            context = summary if summary else text[:5000]
            full_text = text[:10000]
            
            prompt = f"""Analyze the following document and extract 5-8 relevant tags/keywords that best describe its content, topics, and themes.

Document Summary:
{context}

Full Document (excerpt):
{full_text}

Return ONLY a comma-separated list of tags (no numbering, no bullets, no explanation). Each tag should be 1-3 words, lowercase, and descriptive. Example format: python, machine learning, data analysis, api, documentation"""
            
            response = self.client.chat.completions.create(
                model="anthropic/claude-3-haiku",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200
            )
            
            # Parse the response - extract tags from comma-separated list
            tags_text = response.choices[0].message.content.strip()
            # Split by comma and clean up
            tags = [tag.strip().lower() for tag in tags_text.split(',') if tag.strip()]
            # Limit to 8 tags max
            return tags[:8]
        except Exception as e:
            print(f"OpenRouter API Error (Tags): {e}")
            raise e
    
    def classify_document(self, text: str, summary: Optional[str] = None) -> Optional[str]:
        """Classify document into predefined category using AI."""
        if not self.client:
            raise ValueError("OpenRouter API key not configured")
        
        try:
            # Use summary if available for better context
            context = summary if summary else text[:5000]
            full_text = text[:10000]
            
            prompt = f"""Analyze the following document and classify it into ONE of these categories:
- Invoice
- Medical Record
- Resume
- Agreement/Contract
- Research Paper
- Bank Statement

Document Summary:
{context}

Full Document (excerpt):
{full_text}

Return ONLY the category name (exactly as listed above, case-sensitive). If the document doesn't fit any category, return "Other". Do not include any explanation or preamble."""
            
            response = self.client.chat.completions.create(
                model="anthropic/claude-3-haiku",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50
            )
            
            category = response.choices[0].message.content.strip()
            
            # Validate category is one of the allowed ones
            valid_categories = [
                "Invoice", "Medical Record", "Resume", "Agreement/Contract", 
                "Research Paper", "Bank Statement", "Other"
            ]
            
            # Check if category matches (case-insensitive)
            for valid_cat in valid_categories:
                if category.lower() == valid_cat.lower():
                    return valid_cat
            
            return "Other"
        except Exception as e:
            print(f"OpenRouter API Error (Classification): {e}")
            return None
    
    def extract_fields(self, text: str, document_category: Optional[str] = None, summary: Optional[str] = None) -> Dict[str, Any]:
        """Extract structured key fields from document based on document type."""
        if not self.client:
            raise ValueError("OpenRouter API key not configured")
        
        try:
            # Use summary if available for better context
            context = summary if summary else text[:5000]
            full_text = text[:15000]  # More text for field extraction
            
            # Determine fields to extract based on category
            if document_category == "Invoice":
                fields_to_extract = "vendor, amount, date, invoice_number"
                field_descriptions = """
- vendor: Name of the vendor/company issuing the invoice
- amount: Total amount (numeric value, include currency if mentioned)
- date: Invoice date (format: YYYY-MM-DD if possible)
- invoice_number: Invoice number or reference ID
"""
            elif document_category == "Resume":
                fields_to_extract = "name, skills, experience_years, email"
                field_descriptions = """
- name: Full name of the person
- skills: List of skills (comma-separated)
- experience_years: Total years of experience (numeric)
- email: Email address
"""
            elif document_category == "Agreement/Contract":
                fields_to_extract = "parties_involved, start_date, end_date"
                field_descriptions = """
- parties_involved: Names of parties/entities involved (comma-separated)
- start_date: Contract start date (format: YYYY-MM-DD if possible)
- end_date: Contract end date (format: YYYY-MM-DD if possible)
"""
            else:
                # For other document types, try to extract common fields
                fields_to_extract = "key_information"
                field_descriptions = """
- key_information: Important information extracted from the document
"""
            
            prompt = f"""Extract the following structured fields from this document:

Document Category: {document_category or 'Unknown'}

Fields to extract: {fields_to_extract}

{field_descriptions}

Document Summary:
{context}

Full Document (excerpt):
{full_text}

Return ONLY a valid JSON object with the extracted fields. Use null for fields that cannot be found. Example format:
{{
  "vendor": "Company Name",
  "amount": "1000.00 USD",
  "date": "2024-01-15",
  "invoice_number": "INV-12345"
}}

Do not include any explanation or preamble, just the JSON object."""
            
            response = self.client.chat.completions.create(
                model="anthropic/claude-3-haiku",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                response_format={"type": "json_object"} if document_category == "Invoice" else None
            )
            
            # Parse JSON response
            response_text = response.choices[0].message.content.strip()
            
            # Try to extract JSON from response (handle cases where AI adds explanation)
            try:
                # Find JSON object in response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    extracted_fields = json.loads(json_str)
                    return extracted_fields
                else:
                    # Try parsing entire response
                    extracted_fields = json.loads(response_text)
                    return extracted_fields
            except json.JSONDecodeError:
                print(f"Failed to parse JSON from field extraction response: {response_text}")
                return {}
        except Exception as e:
            print(f"OpenRouter API Error (Field Extraction): {e}")
            return {}
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text using OpenAI embeddings via OpenRouter."""
        if not self.client:
            raise ValueError("OpenRouter API key not configured")
        
        try:
            # Use text-embedding-ada-002 model for embeddings (via OpenRouter)
            # Truncate text to reasonable length for embeddings (max ~8000 tokens)
            text_for_embedding = text[:32000]  # Roughly 8000 tokens
            
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text_for_embedding
            )
            
            embedding = response.data[0].embedding
            return embedding
        except Exception as e:
            print(f"OpenRouter API Error (Embedding): {e}")
            # Fallback: try with text-embedding-3-small if ada-002 fails
            try:
                response = self.client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text[:32000]
                )
                return response.data[0].embedding
            except Exception as fallback_error:
                print(f"OpenRouter API Error (Embedding Fallback): {fallback_error}")
                raise e

class AnthropicProvider(AIProvider):
    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def generate_summary(self, text: str) -> str:
        if not self.client:
            raise ValueError("Anthropic API key not configured")
        
        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[
                    {"role": "user", "content": f"Please provide a concise summary of the following document. Do not include any preamble like 'Here is a summary'. Just provide the summary directly:\n\n{text[:10000]}"}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Anthropic API Error (Summary): {e}")
            raise e

    def generate_markdown(self, text: str) -> str:
        if not self.client:
            raise ValueError("Anthropic API key not configured")

        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": f"Convert the following document content into clean, well-structured Markdown. Do not include any preamble or explanation, just the markdown content:\n\n{text[:15000]}"}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Anthropic API Error (Markdown): {e}")
            raise e

    def generate_tags(self, text: str, summary: Optional[str] = None) -> List[str]:
        """Generate relevant tags/keywords using AI."""
        if not self.client:
            raise ValueError("Anthropic API key not configured")
        
        try:
            # Use summary if available for better context, otherwise use text
            context = summary if summary else text[:5000]
            full_text = text[:10000]
            
            prompt = f"""Analyze the following document and extract 5-8 relevant tags/keywords that best describe its content, topics, and themes.

Document Summary:
{context}

Full Document (excerpt):
{full_text}

Return ONLY a comma-separated list of tags (no numbering, no bullets, no explanation). Each tag should be 1-3 words, lowercase, and descriptive. Example format: python, machine learning, data analysis, api, documentation"""
            
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the response - extract tags from comma-separated list
            tags_text = message.content[0].text.strip()
            # Split by comma and clean up
            tags = [tag.strip().lower() for tag in tags_text.split(',') if tag.strip()]
            # Limit to 8 tags max
            return tags[:8]
        except Exception as e:
            print(f"Anthropic API Error (Tags): {e}")
            raise e
    
    def classify_document(self, text: str, summary: Optional[str] = None) -> Optional[str]:
        """Classify document into predefined category using AI."""
        if not self.client:
            raise ValueError("Anthropic API key not configured")
        
        try:
            # Use summary if available for better context
            context = summary if summary else text[:5000]
            full_text = text[:10000]
            
            prompt = f"""Analyze the following document and classify it into ONE of these categories:
- Invoice
- Medical Record
- Resume
- Agreement/Contract
- Research Paper
- Bank Statement

Document Summary:
{context}

Full Document (excerpt):
{full_text}

Return ONLY the category name (exactly as listed above, case-sensitive). If the document doesn't fit any category, return "Other". Do not include any explanation or preamble."""
            
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=50,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            category = message.content[0].text.strip()
            
            # Validate category is one of the allowed ones
            valid_categories = [
                "Invoice", "Medical Record", "Resume", "Agreement/Contract", 
                "Research Paper", "Bank Statement", "Other"
            ]
            
            # Check if category matches (case-insensitive)
            for valid_cat in valid_categories:
                if category.lower() == valid_cat.lower():
                    return valid_cat
            
            return "Other"
        except Exception as e:
            print(f"Anthropic API Error (Classification): {e}")
            return None
    
    def extract_fields(self, text: str, document_category: Optional[str] = None, summary: Optional[str] = None) -> Dict[str, Any]:
        """Extract structured key fields from document based on document type."""
        if not self.client:
            raise ValueError("Anthropic API key not configured")
        
        try:
            # Use summary if available for better context
            context = summary if summary else text[:5000]
            full_text = text[:15000]  # More text for field extraction
            
            # Determine fields to extract based on category
            if document_category == "Invoice":
                fields_to_extract = "vendor, amount, date, invoice_number"
                field_descriptions = """
- vendor: Name of the vendor/company issuing the invoice
- amount: Total amount (numeric value, include currency if mentioned)
- date: Invoice date (format: YYYY-MM-DD if possible)
- invoice_number: Invoice number or reference ID
"""
            elif document_category == "Resume":
                fields_to_extract = "name, skills, experience_years, email"
                field_descriptions = """
- name: Full name of the person
- skills: List of skills (comma-separated)
- experience_years: Total years of experience (numeric)
- email: Email address
"""
            elif document_category == "Agreement/Contract":
                fields_to_extract = "parties_involved, start_date, end_date"
                field_descriptions = """
- parties_involved: Names of parties/entities involved (comma-separated)
- start_date: Contract start date (format: YYYY-MM-DD if possible)
- end_date: Contract end date (format: YYYY-MM-DD if possible)
"""
            else:
                # For other document types, try to extract common fields
                fields_to_extract = "key_information"
                field_descriptions = """
- key_information: Important information extracted from the document
"""
            
            prompt = f"""Extract the following structured fields from this document:

Document Category: {document_category or 'Unknown'}

Fields to extract: {fields_to_extract}

{field_descriptions}

Document Summary:
{context}

Full Document (excerpt):
{full_text}

Return ONLY a valid JSON object with the extracted fields. Use null for fields that cannot be found. Example format:
{{
  "vendor": "Company Name",
  "amount": "1000.00 USD",
  "date": "2024-01-15",
  "invoice_number": "INV-12345"
}}

Do not include any explanation or preamble, just the JSON object."""
            
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse JSON response
            response_text = message.content[0].text.strip()
            
            # Try to extract JSON from response (handle cases where AI adds explanation)
            try:
                # Find JSON object in response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    extracted_fields = json.loads(json_str)
                    return extracted_fields
                else:
                    # Try parsing entire response
                    extracted_fields = json.loads(response_text)
                    return extracted_fields
            except json.JSONDecodeError:
                print(f"Failed to parse JSON from field extraction response: {response_text}")
                return {}
        except Exception as e:
            print(f"Anthropic API Error (Field Extraction): {e}")
            return {}
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text using OpenAI embeddings (Anthropic doesn't have native embeddings)."""
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")
        
        try:
            # Anthropic doesn't have native embeddings, so we use OpenAI embeddings
            # This requires OPENAI_API_KEY to be set separately
            from openai import OpenAI
            import os
            
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                raise ValueError("OPENAI_API_KEY not configured for embeddings")
            
            openai_client = OpenAI(api_key=openai_key)
            text_for_embedding = text[:32000]  # Roughly 8000 tokens
            
            response = openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text_for_embedding
            )
            
            return response.data[0].embedding
        except Exception as e:
            print(f"Anthropic Provider Error (Embedding): {e}")
            raise e

class MockProvider(AIProvider):
    def generate_summary(self, text: str) -> str:
        return "This is a MOCK summary. The document appears to contain information about..." + text[:100] + "..."

    def generate_markdown(self, text: str) -> str:
        return f"# Mock Markdown\n\nThis is a generated markdown representation.\n\n## Extracted Content\n{text[:500]}..."
    
    def generate_tags(self, text: str, summary: Optional[str] = None) -> List[str]:
        """Generate mock tags for testing."""
        # Extract some basic keywords from text as mock tags
        words = text.lower().split()
        # Simple keyword extraction (first few unique words)
        unique_words = []
        for word in words:
            if len(word) > 4 and word not in unique_words and word.isalpha():
                unique_words.append(word)
                if len(unique_words) >= 5:
                    break
        return unique_words[:5] if unique_words else ["document", "content", "text"]
    
    def classify_document(self, text: str, summary: Optional[str] = None) -> Optional[str]:
        """Generate mock classification for testing."""
        text_lower = text.lower()
        
        # Simple keyword-based classification
        if any(word in text_lower for word in ["invoice", "bill", "payment", "due", "amount"]):
            return "Invoice"
        elif any(word in text_lower for word in ["medical", "patient", "diagnosis", "prescription", "doctor"]):
            return "Medical Record"
        elif any(word in text_lower for word in ["resume", "cv", "curriculum vitae", "experience", "skills", "education"]):
            return "Resume"
        elif any(word in text_lower for word in ["agreement", "contract", "terms", "signature", "party"]):
            return "Agreement/Contract"
        elif any(word in text_lower for word in ["research", "study", "paper", "abstract", "methodology", "conclusion"]):
            return "Research Paper"
        elif any(word in text_lower for word in ["bank", "statement", "account", "balance", "transaction", "deposit"]):
            return "Bank Statement"
        else:
            return "Other"
    
    def extract_fields(self, text: str, document_category: Optional[str] = None, summary: Optional[str] = None) -> Dict[str, Any]:
        """Generate mock extracted fields for testing."""
        # Mock field extraction based on category
        if document_category == "Invoice":
            return {
                "vendor": "Mock Vendor Inc.",
                "amount": "1000.00 USD",
                "date": "2024-01-15",
                "invoice_number": "INV-MOCK-001"
            }
        elif document_category == "Resume":
            return {
                "name": "John Doe",
                "skills": "Python, JavaScript, React, Node.js",
                "experience_years": "5",
                "email": "john.doe@example.com"
            }
        elif document_category == "Agreement/Contract":
            return {
                "parties_involved": "Party A, Party B",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        else:
            return {
                "key_information": "Mock extracted information"
            }
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate mock embedding for testing (returns a fixed-size vector)."""
        # Return a mock 1536-dimensional vector (same as text-embedding-ada-002)
        # In real implementation, this would be a proper embedding
        import random
        # Generate a simple mock embedding based on text hash
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        seed = int(hash_obj.hexdigest(), 16) % (2**32)
        random.seed(seed)
        # Generate 1536 random floats between -1 and 1, normalized
        mock_embedding = [random.uniform(-1, 1) for _ in range(1536)]
        # Normalize the vector
        import math
        norm = math.sqrt(sum(x*x for x in mock_embedding))
        if norm > 0:
            mock_embedding = [x / norm for x in mock_embedding]
        return mock_embedding

class AIProviderFactory:
    @staticmethod
    def get_provider() -> AIProvider:
        provider_type = AI_PROVIDER.lower()
        
        # Check API key availability and select appropriate provider
        if provider_type == "anthropic":
            if ANTHROPIC_API_KEY:
                return AnthropicProvider()
            else:
                print("⚠️  Anthropic API key not configured, checking for OpenRouter...")
                if OPENROUTER_API_KEY:
                    print("✓ Using OpenRouter provider as fallback")
                    return OpenRouterProvider()
                else:
                    print("⚠️  No API keys configured, using MockProvider")
                    return MockProvider()
        elif provider_type == "openrouter":
            if OPENROUTER_API_KEY:
                return OpenRouterProvider()
            else:
                print("⚠️  OpenRouter API key not configured, checking for Anthropic...")
                if ANTHROPIC_API_KEY:
                    print("✓ Using Anthropic provider as fallback")
                    return AnthropicProvider()
                else:
                    print("⚠️  No API keys configured, using MockProvider")
                    return MockProvider()
        elif provider_type == "mock":
            return MockProvider()
        else:
            print(f"⚠️  Unknown provider '{provider_type}', checking available API keys...")
            # Try to auto-detect available provider
            if OPENROUTER_API_KEY:
                print("✓ Auto-selecting OpenRouter provider")
                return OpenRouterProvider()
            elif ANTHROPIC_API_KEY:
                print("✓ Auto-selecting Anthropic provider")
                return AnthropicProvider()
            else:
                print("⚠️  No API keys found, using MockProvider")
                return MockProvider()
