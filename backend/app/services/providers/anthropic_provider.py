"""
Anthropic AI Provider.

Provides AI capabilities using Anthropic's Claude API directly.
Uses OpenAI embeddings for vector generation (Anthropic doesn't have native embeddings).
"""
from typing import Optional, List, Dict, Any
import anthropic
import json
import os
from openai import OpenAI
from ...core.config import ANTHROPIC_API_KEY
from ...core.logging_config import get_logger
from .base import AIProvider

logger = get_logger(__name__)


class AnthropicProvider(AIProvider):
    """
    AI Provider using Anthropic Claude API directly.
    
    Uses Claude models for text processing and OpenAI embeddings
    for vector generation (since Anthropic doesn't have native embeddings).
    """
    
    def __init__(self):
        """Initialize Anthropic provider with API key."""
        self.api_key = ANTHROPIC_API_KEY
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def generate_summary(self, text: str) -> str:
        """Generate a concise summary of the document."""
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
            logger.error(f"Anthropic API Error (Summary): {e}")
            raise e

    def generate_markdown(self, text: str) -> str:
        """Convert document text to well-structured Markdown."""
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
            logger.error(f"Anthropic API Error (Markdown): {e}")
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
            logger.error(f"Anthropic API Error (Tags): {e}")
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
            logger.error(f"Anthropic API Error (Classification): {e}")
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
                logger.error(f"Failed to parse JSON from field extraction response: {response_text}")
                return {}
        except Exception as e:
            logger.error(f"Anthropic API Error (Field Extraction): {e}")
            return {}
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text using OpenAI embeddings.
        
        Note: Anthropic doesn't have native embeddings, so we use OpenAI embeddings.
        This requires OPENAI_API_KEY to be set separately.
        """
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")
        
        try:
            # Anthropic doesn't have native embeddings, so we use OpenAI embeddings
            # This requires OPENAI_API_KEY to be set separately
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
            logger.error(f"Anthropic Provider Error (Embedding): {e}")
            raise e

