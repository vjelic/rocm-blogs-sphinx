from datetime import datetime
from numpy import remainder as rem

import importlib.resources as pkg_resources
import os
import time
import traceback

from pathlib import Path

from sphinx.util import logging as sphinx_logging
from sphinx.errors import SphinxError

from ._rocmblogs import ROCmBlogs
from .constants import (
    AVERAGE_READING_SPEED_WPM, SPECIAL_CHARS_PATTERN, WHITESPACE_PATTERN_FOR_SLUGS,
    MARKDOWN_PATTERNS
)

logger = sphinx_logging.getLogger(__name__)

class ROCmBlogsError(SphinxError):
    """Custom exception class for ROCm Blogs errors."""

    category = "ROCm Blogs Error"

def import_file(package: str, resource: str) -> str:
    """Important file imports aspart of the pypi package."""
    try:
        return pkg_resources.read_text(package, resource)
    except Exception as error:
        logger.error(f"Error importing file {resource} from package {package}: {error}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise ROCmBlogsError(f"Error importing file {resource} from package {package}: {error}") from error
    
def truncate_string(input_string: str) -> str:
    """Convert a string to a URL-friendly slug format."""
    try:
        if not input_string:
            return ""
        
        # Remove special characters and replace whitespace with hyphens in one pass
        cleaned_string = SPECIAL_CHARS_PATTERN.sub("", input_string)
        slug = WHITESPACE_PATTERN_FOR_SLUGS.sub("-", cleaned_string).lower()
        
        return slug
    except Exception as error:
        logger.error(f"Error truncating string '{input_string}': {error}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        # Return a safe default value - the original string or empty string
        return input_string if input_string else ""
    
def calculate_read_time(words: int) -> int:
    """Calculate estimated reading time based on word count."""
    try:
        if words <= 0:
            return 0
        
        return round(words / AVERAGE_READING_SPEED_WPM)
    except Exception as error:
        logger.error(f"Error calculating read time: {error}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return 0
    
def is_leap_year(year: int) -> bool:
    """Determine whether a year is a leap year."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def calculate_day_of_week(y: int, m: int, d: int) -> str:
    """return day of week of given date as string, using Gauss's algorithm to find it"""

    if is_leap_year(y):
        month_offset = (0, 3, 4, 0, 2, 5, 0, 3, 6, 1, 4, 6)[m - 1]
    else:
        month_offset = (0, 3, 3, 6, 1, 4, 6, 2, 5, 0, 3, 5)[m - 1]
    y -= 1
    wd = int(
        rem(d + month_offset + 5 * rem(y, 4) + 4 * rem(y, 100) + 6 * rem(y, 400), 7)
    )

    return ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")[wd]
    
def count_words_in_markdown(content: str) -> int:
    """
    Count the number of words in a markdown file.
    
    This function strips away markdown syntax elements and counts
    only the actual content words. It handles YAML front matter,
    code blocks, HTML tags, and other markdown formatting.
    
    Args:
        content: The markdown content as a string
        
    Returns:
        The number of words in the content
    """
    try:
        if not content:
            return 0
            
        # Remove YAML front matter if present
        if content.startswith("---"):
            content = MARKDOWN_PATTERNS['yaml_front_matter'].sub("", content)

        # Apply regex replacements to remove markdown elements
        # Order matters - remove code blocks first, then other elements
        for pattern_name in [
            'fenced_code_blocks', 'indented_code_blocks', 'html_tags',
            'urls', 'image_references', 'link_references', 'headers',
            'horizontal_rules', 'blockquotes', 'unordered_list_markers',
            'ordered_list_markers'
        ]:
            content = MARKDOWN_PATTERNS[pattern_name].sub("", content)

        # Split by whitespace and count non-empty words
        words = [word for word in MARKDOWN_PATTERNS['whitespace'].split(content) if word.strip()]
        return len(words)
        
    except Exception as error:
        logger.warning(f"Error counting words in markdown: {error}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return 0