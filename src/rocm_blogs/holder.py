"""
File: _blog_holder.py

BlogHolder class to hold the blogs.
"""

from datetime import datetime
import os

from .blog import Blog


class BlogHolder:
    def __init__(self) -> None:
        """Initialize the BlogHolder class."""

        self.blogs: dict[tuple[str, datetime], Blog] = {}
        self.blogs_categories: dict[str, list[Blog]] = {}

    def _make_key(self, blog: Blog) -> None:
        """Make a key for the blog."""

        if not hasattr(blog, "blog_title"):
            raise AttributeError("The blog must have a 'blog_title' attribute.")

        title = blog.blog_title

        if not hasattr(blog, "date"):
            raise AttributeError("The blog must have a 'date' attribute.")
        date = blog.date

        if not isinstance(blog, Blog):
            raise TypeError("The blog must be an instance of the 'Blog' class.")

        return (title, date)

    def add_blog(self, blog: Blog) -> None:
        """Add a blog to the list of blogs."""

        key = self._make_key(blog)
        if key in self.blogs:
            raise KeyError(
                f"Blog with title '{key[0]}' and date '{key[1]}' already exists."
            )
        self.blogs[key] = blog

    def remove_blog(self, blog: Blog) -> None:
        """Remove a blog from the list of blogs."""

        if not hasattr(blog, "blog_title"):
            raise AttributeError("The blog must have a 'blog_title' attribute.")
        title = blog.blog_title

        if not hasattr(blog, "date"):
            raise AttributeError("The blog must have a 'date' attribute.")
        date = blog.date

        key = (title, date)
        if key in self.blogs:
            del self.blogs[key]
        else:
            raise KeyError("Blog not found.")

    def get_blogs(self) -> list[Blog]:
        """Return the list of blogs."""

        return list(self.blogs.values())

    def clear_blogs(self) -> None:
        """Clear the list of blogs."""

        self.blogs.clear()

    def sort_blogs_by_date(self, reverse: bool = True) -> list[Blog]:
        """Sort the blogs by date."""

        self.blogs = dict(sorted(
            self.blogs.items(),
            key=lambda item: item[1].date if item[1].date is not None else datetime.min,
            reverse=reverse,
        ))
    
    def sort_blogs_by_category(self, categories) -> list[Blog]:
        """Sort the blogs by category."""

        for category in categories:
            self.blogs_categories[category] = []

        for blog in self.blogs.values():
            if blog.category in categories:
                self.blogs_categories[blog.category].append(blog)

    def get_latest_blogs(self, count: int = 15) -> list[Blog]:
        """Get the latest blogs based on the count."""

        return self.blogs[:count]

    def get_blog_by_title(self, title: str) -> Blog:
        """Get a blog by its title."""

        for blog in self.blogs:
            if blog.blog_title == title:
                return blog

        return None

    def __iter__(self) -> iter:
        """Iterate over the list of blogs."""

        return iter(self.blogs.values())

    def __len__(self) -> int:
        """Return the number of blogs."""

        return len(self.blogs)

    def __repr__(self) -> str:
        """Return a string representation of the class."""

        return f"ROCmBlogs({len(self.blogs)} blogs)"