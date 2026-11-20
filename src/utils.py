"""
Utility Functions

Helpers for time formatting, number formatting, and display calculations.
"""

import time


_UNIX_EPOCH_OFFSET = 946684800 if time.gmtime(0)[0] == 2000 else 0


# Color definitions (RGB565 format - 16-bit color)
class Colors:
    BLACK = 0x0000
    WHITE = 0xFFFF
    BITCOIN_ORANGE = 0xF520  # Bitcoin orange (#F7931A)
    GREEN = 0x07E0           # Bright green
    RED = 0xF800             # Bright red
    GRAY = 0x8410            # Medium gray
    LIGHT_GRAY = 0xC618      # Light gray
    DARK_GRAY = 0x4208       # Dark gray


def format_sast_time(unix_timestamp=None):
    """
    Format time as HH:MM SAST (South African Standard Time).
    
    Args:
        unix_timestamp: Unix timestamp (default: now)
    
    Returns:
        "14:32" string format
    """
    if unix_timestamp is None:
        unix_timestamp = time.time() + _UNIX_EPOCH_OFFSET
    
    # SAST is UTC+2
    sast_timestamp = unix_timestamp - _UNIX_EPOCH_OFFSET + (2 * 3600)
    dt = time.gmtime(sast_timestamp)
    return f"{dt[3]:02d}:{dt[4]:02d}"


def format_sast_time_full(unix_timestamp=None):
    """
    Format time as HH:MM:SS SAST.
    
    Args:
        unix_timestamp: Unix timestamp (default: now)
    
    Returns:
        "14:32:45" string format
    """
    if unix_timestamp is None:
        unix_timestamp = time.time() + _UNIX_EPOCH_OFFSET
    
    sast_timestamp = unix_timestamp - _UNIX_EPOCH_OFFSET + (2 * 3600)
    dt = time.gmtime(sast_timestamp)
    return f"{dt[3]:02d}:{dt[4]:02d}:{dt[5]:02d}"


def format_time_ago(unix_timestamp):
    """
    Format time elapsed since a Unix timestamp.
    
    Args:
        unix_timestamp: Unix timestamp of event
    
    Returns:
        "2 min 34 sec ago" or "Just now" or similar
    """
    if unix_timestamp is None:
        return "Unknown"
    
    elapsed = time.time() + _UNIX_EPOCH_OFFSET - unix_timestamp
    
    if elapsed < 0:
        return "In the future?"
    
    if elapsed < 1:
        return "Just now"
    
    if elapsed < 60:
        return f"{int(elapsed)} sec ago"
    
    if elapsed < 3600:
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        if seconds == 0:
            return f"{minutes} min ago"
        return f"{minutes} min {seconds} sec ago"
    
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    if minutes == 0:
        return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"
    return f"{hours}h {minutes}m ago"


def format_time_delta(seconds):
    """
    Format seconds as MM:SS or HH:MM:SS.
    
    Args:
        seconds: Number of seconds (float or int)
    
    Returns:
        "2:34" or "1:02:30" string format
    """
    if seconds is None or seconds < 0:
        return "00:00"
    
    total_seconds = int(seconds)
    
    if total_seconds < 3600:
        # MM:SS format
        minutes = total_seconds // 60
        secs = total_seconds % 60
        return f"{minutes}:{secs:02d}"
    else:
        # HH:MM:SS format
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"


def format_number(value, decimals=2):
    """
    Format number with K, M, B, T suffixes.
    
    Args:
        value: Number to format
        decimals: Decimal places to show
    
    Returns:
        "45.3K" or "1.2M" or "3.4B" or "84.2T"
    """
    if value is None:
        return "N/A"
    
    abs_value = abs(value)
    
    if abs_value >= 1e12:
        return f"{value/1e12:.{decimals}f}T"
    elif abs_value >= 1e9:
        return f"{value/1e9:.{decimals}f}B"
    elif abs_value >= 1e6:
        return f"{value/1e6:.{decimals}f}M"
    elif abs_value >= 1e3:
        return f"{value/1e3:.{decimals}f}K"
    else:
        return f"{value:.{decimals}f}"


def format_thousands(value):
    """Format an integer or integer string with space separators."""
    whole = str(value)
    sign = '-' if whole.startswith('-') else ''
    digits = whole[1:] if sign else whole
    groups = []
    while len(digits) > 3:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    groups.insert(0, digits)
    return sign + ' '.join(groups)


def format_price(usd_price):
    """
    Format Bitcoin price for display.
    
    Args:
        usd_price: Price in USD
    Returns:
        "$45 320.50"
    """
    if usd_price is None:
        return "N/A"
    
    whole, _, decimals = f"{usd_price:.2f}".partition('.')
    return f"${format_thousands(whole)}.{decimals}"


def format_hash(hash_string, truncate=True, length=16):
    """
    Format Bitcoin hash for display.
    
    Args:
        hash_string: Full hash (hex string)
        truncate: Whether to truncate (default True)
        length: Length to show if truncating (default 16)
    
    Returns:
        "0a3f7e2c..." (truncated) or full hash
    """
    if hash_string is None:
        return "N/A"
    
    if truncate and len(hash_string) > length:
        return f"{hash_string[:length]}..."
    
    return hash_string


def format_difficulty(difficulty):
    """
    Format difficulty for display.
    
    Args:
        difficulty: Difficulty value
    
    Returns:
        "84.2T" or similar using format_number
    """
    return format_number(difficulty, decimals=1)


def seconds_since_block(block_time):
    """
    Calculate seconds since block was mined.
    
    Args:
        block_time: Unix timestamp of block
    
    Returns:
        Elapsed seconds (float)
    """
    if block_time is None:
        return None
    
    return time.time() + _UNIX_EPOCH_OFFSET - block_time


def get_price_color(current_price, previous_price):
    """
    Determine color based on price change.
    
    Args:
        current_price: Current price
        previous_price: Previous price
    
    Returns:
        Colors.GREEN (up), Colors.RED (down), or Colors.WHITE (same)
    """
    if previous_price is None or current_price is None:
        return Colors.WHITE
    
    if current_price > previous_price:
        return Colors.GREEN
    elif current_price < previous_price:
        return Colors.RED
    else:
        return Colors.WHITE


def truncate_text(text, max_length):
    """
    Truncate text to max length, adding ellipsis if needed.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
    
    Returns:
        Truncated text with "..." if needed
    """
    if text is None:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."


def center_text(text, width):
    """
    Center text within a given width.
    
    Args:
        text: Text to center
        width: Width to center within
    
    Returns:
        Centered text with padding
    """
    if len(text) >= width:
        return text
    
    padding = (width - len(text)) // 2
    return " " * padding + text


# Testing
if __name__ == '__main__':
    print("Utility Functions Test")
    print("=" * 60)
    
    print("\nTime Formatting:")
    print(f"SAST Time: {format_sast_time()}")
    print(f"SAST Time Full: {format_sast_time_full()}")
    
    # Test time ago with a timestamp from 2.5 minutes ago
    old_time = time.time() - 150
    print(f"Time ago: {format_time_ago(old_time)}")
    
    print(f"Time delta (150s): {format_time_delta(150)}")
    print(f"Time delta (3665s): {format_time_delta(3665)}")
    
    print("\nNumber Formatting:")
    print(f"Format 84.2T: {format_number(84.2e12, 1)}")
    print(f"Format 1234567: {format_number(1234567)}")
    
    print("\nPrice Formatting:")
    print(f"Price: {format_price(45320.50)}")
    
    print("\nHash Formatting:")
    test_hash = "0a3f7e2c1b4a8f9e3d5c6b7a8f9e0d1c2b3a4f5"
    print(f"Hash (truncated): {format_hash(test_hash)}")
    print(f"Hash (full): {format_hash(test_hash, truncate=False)}")
    
    print("\nDifficulty Formatting:")
    print(f"Difficulty: {format_difficulty(84.2e12)}")
    
    print("\nColor Test:")
    print(f"GREEN: {Colors.GREEN:04x}")
    print(f"RED: {Colors.RED:04x}")
    print(f"BITCOIN_ORANGE: {Colors.BITCOIN_ORANGE:04x}")
