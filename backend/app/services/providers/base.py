"""
Base AI Provider Interface.

All AI providers must inherit from this base class and implement
all abstract methods.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class AIProvider(ABC):
    """
    Abstract base class for AI providers.
    
    Each AI provider should implement all methods to provide
    AI-powered document processing capabilities.
    """
    
    @abstractmethod
    def generate_summary(self, text: str) -> str:
        """
        Generate a concise summary of the document text.
        
        Args:
            text: Document text content
            
        Returns:
            Summary string
        """
        pass

    @abstractmethod
    def generate_markdown(self, text: str) -> str:
        """
        Convert document text to well-structured Markdown.
        
        Args:
            text: Document text content
            
        Returns:
            Markdown formatted string
        """
        pass
    
    @abstractmethod
    def generate_tags(self, text: str, summary: Optional[str] = None) -> List[str]:
        """
        Generate relevant tags/keywords from document text.
        
        Args:
            text: Document text content
            summary: Optional summary for better context
            
        Returns:
            List of tag strings
        """
        pass
    
    @abstractmethod
    def classify_document(self, text: str, summary: Optional[str] = None) -> Optional[str]:
        """
        Classify document into one of the predefined categories.
        
        Categories: Invoice, Medical Record, Resume, Agreement/Contract, 
                    Research Paper, Bank Statement, Other
        
        Args:
            text: Document text content
            summary: Optional summary for better context
            
        Returns:
            Category name or None if classification fails
        """
        pass
    
    @abstractmethod
    def extract_fields(self, text: str, document_category: Optional[str] = None, summary: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract structured key fields from document based on document type.
        
        For Invoices: vendor, amount, date, invoice_number
        For Resumes: name, skills, experience_years, email
        For Contracts: parties_involved, start_date, end_date
        
        Args:
            text: Document text content
            document_category: Optional document category for better extraction
            summary: Optional summary for better context
            
        Returns:
            Dictionary with extracted fields (empty dict if extraction fails)
        """
        pass
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text using AI.
        
        Args:
            text: Document text content
            
        Returns:
            List of floats representing the embedding vector
        """
        pass

