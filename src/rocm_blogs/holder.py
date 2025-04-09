"""
File: _blog_holder.py

BlogHolder class to hold the blogs.
"""

import os
from datetime import datetime
from sphinx.util import logging as sphinx_logging

from .blog import Blog

# Initialize logger
sphinx_diagnostics = sphinx_logging.getLogger(__name__)


class BlogHolder:
    def __init__(self) -> None:
        """Initialize the BlogHolder class."""

        self.blogs: dict[tuple[str, datetime], Blog] = {}
        self.blogs_categories: dict[str, list[Blog]] = {}

    def _make_key(self, blog: Blog) -> tuple[str, datetime]:
        """Make a key for the blog."""

        if not isinstance(blog, Blog):
            sphinx_diagnostics.error(
                f"Expected Blog instance but got {type(blog)}"
            )
            raise TypeError("The blog must be an instance of the 'Blog' class.")

        # Get title with fallback
        if hasattr(blog, "blog_title") and blog.blog_title:
            title = blog.blog_title
        else:
            # Use file path as fallback
            if hasattr(blog, "file_path"):
                filename = os.path.basename(blog.file_path)
                title = os.path.splitext(filename)[0].replace("-", " ").replace("_", " ").title()
                sphinx_diagnostics.warning(
                    f"Blog missing blog_title attribute, using filename: {title}"
                )
            else:
                title = "Untitled Blog"
                sphinx_diagnostics.warning(
                    f"Blog missing both blog_title and file_path, using default: {title}"
                )

        # Get date with fallback
        if hasattr(blog, "date") and blog.date:
            date = blog.date
        else:
            # Use current date as fallback
            date = datetime.now()
            sphinx_diagnostics.warning(
                f"Blog '{title}' missing date attribute, using current date: {date}"
            )

        sphinx_diagnostics.debug(
            f"Created key for blog: ({title}, {date})"
        )
        return (title, date)

    def add_blog(self, blog: Blog) -> None:
        """Add a blog to the list of blogs."""

        key = self._make_key(blog)
        if key in self.blogs:
            sphinx_diagnostics.warning(
                f"Duplicate blog detected: '{key[0]}' with date '{key[1]}'"
            )
            raise KeyError(
                f"Blog with title '{key[0]}' and date '{key[1]}' already exists."
            )
        self.blogs[key] = blog
        sphinx_diagnostics.debug(
            f"Added blog: '{key[0]}' with date '{key[1]}'"
        )

    def remove_blog(self, blog: Blog) -> None:
        """Remove a blog from the list of blogs."""

        if not hasattr(blog, "blog_title"):
            sphinx_diagnostics.error(
                "Cannot remove blog: missing blog_title attribute"
            )
            raise AttributeError("The blog must have a 'blog_title' attribute.")
        title = blog.blog_title

        if not hasattr(blog, "date"):
            sphinx_diagnostics.error(
                f"Cannot remove blog '{title}': missing date attribute"
            )
            raise AttributeError("The blog must have a 'date' attribute.")
        date = blog.date

        key = (title, date)
        if key in self.blogs:
            del self.blogs[key]
            sphinx_diagnostics.info(
                f"Removed blog: '{title}' with date '{date}'"
            )
        else:
            sphinx_diagnostics.warning(
                f"Cannot remove blog: '{title}' with date '{date}' not found"
            )
            raise KeyError("Blog not found.")

    def get_blog_by_key(self, key: tuple[str, datetime]) -> Blog:
        """Get a blog by its key."""

        if key in self.blogs:
            sphinx_diagnostics.debug(
                f"Found blog with key: {key}"
            )
            return self.blogs[key]

        sphinx_diagnostics.debug(
            f"No blog found with key: {key}"
        )
        return None

    def get_blogs(self) -> list[Blog]:
        """Return the list of blogs."""
        
        blog_count = len(self.blogs)
        sphinx_diagnostics.debug(
            f"Returning {blog_count} blogs"
        )
        return list(self.blogs.values())

    def clear_blogs(self) -> None:
        """Clear the list of blogs."""
        
        blog_count = len(self.blogs)

        sphinx_diagnostics.info(
            f"Clearing {blog_count} blogs from the blog holder"
        )
        self.blogs.clear()
        sphinx_diagnostics.debug(
            "Blog holder cleared"
        )

    def sort_blogs_by_date(self, reverse: bool = True) -> list[Blog]:
        """Sort the blogs by date."""
        
        sphinx_diagnostics.info(
            f"Sorting {len(self.blogs)} blogs by date (reverse={reverse})"
        )
        
        self.blogs = dict(
            sorted(
                self.blogs.items(),
                key=lambda item: (
                    item[1].date if item[1].date is not None else datetime.min
                ),
                reverse=reverse,
            )
        )
        
        sphinx_diagnostics.debug("Blogs sorted by date")
        return list(self.blogs.values())

    def sort_blogs_by_category(self, categories) -> list[Blog]:
        """Sort the blogs by category."""
        
        sphinx_diagnostics.info(
            f"Sorting {len(self.blogs)} blogs into {len(categories)} categories"
        )
        
        # Clear existing category lists
        self.blogs_categories = {}
        
        # Initialize category lists
        for category in categories:
            self.blogs_categories[category] = []
            sphinx_diagnostics.debug(
                f"Initialized category: {category}"
            )

        # Sort blogs into categories
        category_counts = {}
        for blog in self.blogs.values():
            if blog.category in categories:
                self.blogs_categories[blog.category].append(blog)
                category_counts[blog.category] = category_counts.get(blog.category, 0) + 1
        
        # Log category counts
        for category, count in category_counts.items():
            sphinx_diagnostics.info(
                f"Category '{category}' has {count} blogs"
            )
        
        # Log categories with no blogs
        for category in categories:
            if category not in category_counts:
                sphinx_diagnostics.warning(
                    f"Category '{category}' has no blogs"
                )

    def get_latest_blogs(self, count: int = 15) -> list[Blog]:
        """Get the latest blogs based on the count."""
        
        available_count = min(count, len(self.blogs))
        sphinx_diagnostics.debug(
            f"Getting {available_count} latest blogs (requested: {count})"
        )
        return list(self.blogs.values())[:available_count]

    def get_blog_by_title(self, title: str) -> Blog:
        """Get a blog by its title."""
        
        sphinx_diagnostics.debug(
            f"Searching for blog with title: {title}"
        )
        
        for blog in self.blogs.values():
            if blog.blog_title == title:
                sphinx_diagnostics.debug(
                    f"Found blog with title: {title}"
                )
                return blog

        sphinx_diagnostics.debug(
            f"No blog found with title: {title}"
        )
        return None

    def get_blogs_by_category(self, category: str) -> list[Blog]:
        """Get blogs by category."""
        
        if category in self.blogs_categories:
            blog_count = len(self.blogs_categories[category])
            sphinx_diagnostics.debug(
                f"Found {blog_count} blogs in category: {category}"
            )
            return self.blogs_categories[category]

        sphinx_diagnostics.debug(
            f"No blogs found in category: {category}"
        )
        return []

    def __iter__(self) -> iter:
        """Iterate over the list of blogs."""

        return iter(self.blogs.values())

    def __len__(self) -> int:
        """Return the number of blogs."""

        return len(self.blogs)

    def __repr__(self) -> str:
        """Return a string representation of the class."""

        return f"BlogHolder(blogs={self.blogs})"