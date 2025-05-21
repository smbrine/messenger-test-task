"""
Helper functions for the web interface.
"""
import typing as t
import random
from string import ascii_uppercase


def generate_avatar_initials(name: str) -> str:
    """
    Generate avatar initials from a name.
    
    Args:
        name: The name to generate initials from
        
    Returns:
        Initials (1-2 characters)
    """
    if not name:
        return "??"
        
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    elif len(parts) == 1 and parts[0]:
        if len(parts[0]) >= 2:
            return parts[0][:2].upper()
        elif len(parts[0]) == 1:
            return (parts[0][0] + parts[0][0]).upper()
    
    return "??"


def generate_random_initials() -> str:
    """
    Generate random 2-letter initials for avatars.
    
    Returns:
        A string with 2 random uppercase letters
    """
    return ''.join(random.choices(ascii_uppercase, k=2))


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate text to a maximum length, adding ellipsis if needed.
    
    Args:
        text: The text to truncate
        max_length: Maximum length before truncation
    
    Returns:
        Truncated text with ellipsis if needed
    """
    if not text or len(text) <= max_length:
        return text
    return text[:max_length] + '...' 