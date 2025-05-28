"""
Test script to verify the enhanced _process_category function.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rocm_blogs._rocmblogs import ROCmBlogs
from rocm_blogs.constants import CATEGORY_TEMPLATE
from rocm_blogs.process import _process_category


def test_filter_criteria():
    """Test the filter criteria functionality in _process_category."""
    print("Testing filter criteria functionality in _process_category")

    # Initialize ROCmBlogs
    rocm_blogs = ROCmBlogs()

    # Find blogs directory
    blogs_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blogs")
    if not os.path.exists(blogs_directory):
        blogs_directory = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "test_blogs"
        )
        if not os.path.exists(blogs_directory):
            print(f"Could not find blogs directory. Creating a test directory.")
            blogs_directory = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "test_blogs"
            )
            os.makedirs(blogs_directory, exist_ok=True)

    rocm_blogs.blogs_directory = blogs_directory
    print(f"Using blogs directory: {blogs_directory}")

    test_category = {
        "name": "Test Category",
        "template": "applications-models.html",
        "output_base": "test-category",
        "category_key": "test-category",
        "title": "Test Category",
        "description": "Test category description",
        "keywords": "test, category",
        "filter_criteria": {"category": ["Applications & models"], "vertical": ["AI"]},
    }

    pagination_template = (
        "<div>{prev_button} Page {current_page} of {total_pages} {next_button}</div>"
    )
    css_content = "body { font-family: Arial; }"
    pagination_css = ".pagination { display: flex; }"
    current_datetime = "2025-05-13 23:00:00"

    # Call _process_category with the test category
    try:
        print("Calling _process_category with filter criteria")
        _process_category(
            test_category,
            rocm_blogs,
            blogs_directory,
            pagination_template,
            css_content,
            pagination_css,
            current_datetime,
            CATEGORY_TEMPLATE,
        )
        print("_process_category completed successfully")
        return True
    except Exception as e:
        print(f"Error in _process_category: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_filter_criteria()
    print(f"Test {'passed' if success else 'failed'}")
    sys.exit(0 if success else 1)
