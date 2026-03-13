import re

def validate_url(url):
    """
    Basic validation for URLs.
    """
    if not url:
        return False, "URL cannot be empty."
    
    # Very basic regex for URL presence
    url_pattern = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not re.match(url_pattern, url):
        return False, "Invalid URL format."
    
    return True, None

def sanitize_input(text):
    """
    Clean up user input if necessary.
    """
    if not text:
        return ""
    return text.strip()
