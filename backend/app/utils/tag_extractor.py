"""
Tag extraction utilities - Extract keywords and tags from document content.
"""
from typing import List, Optional, Dict
import re

# Common stop words to filter out
_STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
    'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must',
    'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
    'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
    'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such',
    'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can',
    'int', 'code', 'copyright', 'education', 'nick', 'parlante', 'file', 'files',
    'document', 'documents', 'page', 'pages', 'section', 'sections', 'chapter', 'chapters'
}

# Configuration constants
_MIN_WORD_LENGTH = 3
_MIN_FREQUENCY = 2
_MAX_KEYWORDS = 10
_MAX_PHRASES = 5
_MAX_TAGS = 8


def extract_tags_from_text(text: str, summary: Optional[str] = None) -> List[str]:
    """
    Extract tags from document text content.
    
    Works with or without AI summary - extracts keywords and important terms.
    Combines text and summary for better tag extraction when summary is available.
    
    Args:
        text: Document text content
        summary: Optional AI-generated summary for better context
        
    Returns:
        List of extracted tags (max 8 tags)
    """
    # Combine text and summary for better tag extraction
    content = f"{summary}\n{text}" if summary else text
    
    # Extract keywords from word frequency
    keywords = _extract_keywords(content)
    
    # Extract capitalized phrases (proper nouns/topics)
    phrases = _extract_capitalized_phrases(content)
    
    # Combine and deduplicate
    all_tags = list(set(keywords + phrases))
    
    # Limit to max tags
    return all_tags[:_MAX_TAGS]


def _extract_keywords(content: str) -> List[str]:
    """
    Extract top keywords based on word frequency.
    
    Args:
        content: Text content to analyze
        
    Returns:
        List of top keywords
    """
    # Extract words (alphanumeric, at least MIN_WORD_LENGTH characters)
    words = re.findall(rf'\b[a-zA-Z]{{{_MIN_WORD_LENGTH},}}\b', content.lower())
    
    # Count word frequency
    word_freq: Dict[str, int] = {}
    for word in words:
        if word not in _STOP_WORDS and len(word) >= _MIN_WORD_LENGTH:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Get top keywords (most frequent, at least MIN_FREQUENCY occurrences)
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    top_keywords = [
        word for word, freq in sorted_words[:_MAX_KEYWORDS]
        if freq >= _MIN_FREQUENCY
    ]
    
    return top_keywords


def _extract_capitalized_phrases(content: str) -> List[str]:
    """
    Extract capitalized phrases (potential proper nouns/topics).
    
    Args:
        content: Text content to analyze
        
    Returns:
        List of unique phrases (lowercased)
    """
    capitalized_phrases = re.findall(
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
        content
    )
    unique_phrases = list(set([
        phrase.lower() for phrase in capitalized_phrases[:_MAX_PHRASES]
    ]))
    
    return unique_phrases

