from django import template
import re

register = template.Library()

@register.filter
def extract_youtube_id(url):
    """
    Extracts the YouTube video ID from a URL.
    Handles both youtu.be and youtube.com URLs.
    """
    if "youtu.be" in url:
        # Get ID for https://youtu.be/VIDEO_ID
        return url.split("/")[-1]  # Last part after slash is the ID
    elif "youtube.com" in url:
        # Match ID for https://www.youtube.com/watch?v=VIDEO_ID
        match = re.search(r'(?:v=|\/)([a-zA-Z0-9_-]{11})', url)
        if match:
            return match.group(1)  # Return the first capture group
    return None

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get item from dictionary
    Usage: {{ mydict|get_item:key }}
    """
    if dictionary is None:
        return False
    return dictionary.get(key, False)

register = template.Library()

@register.filter
def short_number(value):
    """
    Format numbers with K/M/B suffix
    FIXED: Proper formatting without errors
    """
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value
    
    if value >= 1_000_000_000:
        # Billions
        formatted = value / 1_000_000_000
        if formatted >= 10:
            return f"{formatted:.0f}B"
        else:
            return f"{formatted:.1f}B"
    
    elif value >= 1_000_000:
        # Millions
        formatted = value / 1_000_000
        if formatted >= 10:
            return f"{formatted:.0f}M"
        else:
            return f"{formatted:.1f}M"
    
    elif value >= 1_000:
        # Thousands
        formatted = value / 1_000
        if formatted >= 10:
            return f"{formatted:.0f}K"
        else:
            return f"{formatted:.1f}K"
    
    else:
        return str(int(value))

    

