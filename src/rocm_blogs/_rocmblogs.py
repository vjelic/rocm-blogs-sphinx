import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import yaml
from sphinx.util import logging as sphinx_logging

from .blog import Blog
from .holder import BlogHolder


# Direct implementation to avoid circular imports
def log_message(level, message, operation="general", component="rocmblogs", **kwargs):
    """Log message function to avoid circular imports."""
    try:
        from .logger.logger import log_message as logger_log_message

        return logger_log_message(level, message, operation, component, **kwargs)
    except ImportError:
        # Fallback to print if import fails
        print(f"[{level.upper()}] {message}")


class ROCmBlogs:
    def __init__(self) -> None:
        """Initialize ROCmBlogs class."""

        self.blogs_directory = ""
        self.sphinx_app = None
        self.sphinx_env = None
        self.blogs = BlogHolder()
        self.blog_paths: list[str] = []
        self.author_paths: list[str] = []
        self.categories = []
        self.tags = []
        self.yaml_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    # performance improvement
    def find_readme_files_cache(self) -> None:
        """Cache README files in blogs directory."""
        cache_file = Path("readme_files_cache.txt")
        root = Path(self.blogs_directory)
        log_message(
            "debug",
            f"Current working directory: {os.getcwd()}",
            "general",
            "_rocmblogs",
        )

        if cache_file.exists():
            with cache_file.open("r", encoding="utf-8") as f:
                cached_paths = [line.strip() for line in f if line.strip()]
            valid_paths = [path for path in cached_paths if Path(path).exists()]
            if valid_paths and len(valid_paths) == len(cached_paths):
                log_message(
                    "info",
                    f"Loaded {len(valid_paths)} cached README file(s) from {cache_file}",
                    "general",
                    "_rocmblogs",
                )
                self.blog_paths = valid_paths
                return
            else:
                log_message(
                    "info",
                    "Cache invalidated due to deleted or changed files. Rescanning directory.",
                    "general",
                    "_rocmblogs",
                )

        # If no valid cache is available, perform a fresh scan.
        log_message(
            "info", "Scanning {root} for README.md files...", "general", "_rocmblogs"
        )

        candidates = list(root.rglob("README.md"))
        log_message(
            "debug",
            f"Found {len(candidates)} candidate README.md files",
            "general",
            "_rocmblogs",
        )

        with open("candidates.txt", "w", encoding="utf-8") as f:
            for candidate in candidates:
                f.write(str(candidate) + "\n")
        log_message(
            "debug", f"Saved {len(candidates)} candidate paths to candidates.txt"
        )

        readme_files = [str(path.resolve()) for path in candidates if path.is_file()]

        if not readme_files:
            log_message("critical", "No 'README.md' files found in the blogs directory")
            raise FileNotFoundError("No 'README.md' files found.")

        log_message(
            "info",
            f"Found {len(readme_files)} 'README.md' file(s).",
            "general",
            "_rocmblogs",
        )
        self.blog_paths = readme_files

        # Update the cache file with the fresh scan.
        with cache_file.open("w", encoding="utf-8") as f:
            for path in readme_files:
                f.write(path + "\n")
        log_message(
            "debug", f"Updated cache file with {len(readme_files)} README paths"
        )

    def find_readme_files(self) -> None:
        """Find all README.md files in blogs directory."""

        root = Path(self.blogs_directory)

        log_message(
            "debug",
            f"Current working directory: {os.getcwd()}",
            "general",
            "_rocmblogs",
        )
        log_message(
            "info", "Scanning {root} for README.md files...", "general", "_rocmblogs"
        )

        candidates = list(root.rglob("README.md"))
        log_message(
            "debug",
            f"Found {len(candidates)} candidate README.md files",
            "general",
            "_rocmblogs",
        )

        def process_path(path: Path) -> str | None:
            """Check if path is file and return path."""

            if path.is_file():
                return str(path.resolve())
            return None

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(process_path, candidates))

        readme_files = [result for result in results if result is not None]

        if not readme_files:
            log_message("critical", "No 'README.md' files found in the blogs directory")
            raise FileNotFoundError("No 'readme.md' files found.")

        log_message(
            "info",
            f"Found {len(readme_files)} 'README.md' file(s).",
            "general",
            "_rocmblogs",
        )

        self.blog_paths = readme_files

    def process_path(self, path: Path) -> str | None:
        """Check if path is file and return path."""

        if path.is_file():
            return str(path.resolve())
        return None

    def find_author_files(self) -> None:
        """Find all author files in blogs directory."""

        root = Path(self.blogs_directory)

        log_message(
            "debug",
            f"Current working directory: {os.getcwd()}",
            "general",
            "_rocmblogs",
        )
        log_message(
            "info", "Scanning {root} for author directory", "general", "_rocmblogs"
        )

        author_directory = root / "authors"
        if not author_directory.exists():
            log_message(
                "critical", f"The directory '{author_directory}' does not exist."
            )
            raise FileNotFoundError(
                f"The directory '{author_directory}' does not exist."
            )

        candidates = list(author_directory.rglob("*.md"))
        log_message(
            "debug",
            f"Found {len(candidates)} candidate author files",
            "general",
            "_rocmblogs",
        )

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(self.process_path, candidates))

        author_files = [result for result in results if result is not None]

        for author in author_files:
            if not author.endswith(".md"):
                log_message(
                    "info", "Found markdown file: {author}", "general", "_rocmblogs"
                )

        if not author_files:
            log_message("critical", "No 'author.md' files found in the blogs directory")
            raise FileNotFoundError("No 'author.md' files found.")

        log_message(
            "info",
            f"Found {len(author_files)} 'author.md' file(s).",
            "general",
            "_rocmblogs",
        )

        self.author_paths = author_files

    def find_blogs_directory(self, working_directory: str) -> Path:
        """Find blogs directory from working directory."""

        if not os.path.exists(working_directory):
            log_message(
                "critical", f"The directory '{working_directory}' does not exist."
            )
            raise FileNotFoundError(
                f"The directory '{working_directory}' does not exist."
            )

        current_dir = Path(working_directory).resolve()
        log_message(
            "debug",
            f"Starting search for blogs directory from: {current_dir}",
            "general",
            "_rocmblogs",
        )

        while True:
            candidate = current_dir / "blogs"
            log_message(
                "debug",
                f"Checking if {candidate} is a directory",
                "general",
                "_rocmblogs",
            )

            if candidate.is_dir():
                log_message(
                    "info",
                    "Found blogs directory at: {candidate}",
                    "general",
                    "_rocmblogs",
                )
                self.blogs_directory = candidate
                return candidate

            if current_dir == current_dir.parent:
                log_message(
                    "critical", "No 'blogs' directory found in the parent hierarchy."
                )
                raise FileNotFoundError(
                    "No 'blogs' directory found in the parent hierarchy."
                )

            current_dir = current_dir.parent

    def extract_metadata(self) -> dict:
        """Extract metadata from blog files."""
        if not self.blog_paths:
            log_message("warning", "No blog paths available to extract metadata from")
            return {}

        file_path = self.blog_paths[0]
        log_message(
            "info", "Extracting metadata from {file_path}", "general", "_rocmblogs"
        )

        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        match = self.yaml_pattern.match(content)

        if match:
            yaml_content = match.group(1)

            try:
                metadata = yaml.safe_load(yaml_content)

                category = metadata.get("category", "")
                tags = metadata.get("tags", "")

                self.categories.append(category)
                self.tags.append(tags)

                log_message(
                    "debug",
                    f"Extracted metadata - Category: {category}, Tags: {tags}",
                    "general",
                    "_rocmblogs",
                )

                return metadata
            except yaml.YAMLError as error:
                log_message(
                    "error",
                    f"Error parsing YAML in {file_path}: {error}",
                    "general",
                    "_rocmblogs",
                )
                raise ValueError(f"Error parsing YAML: {error}")
        else:
            log_message(
                "warning",
                f"No YAML front matter found in {file_path}. Look at the guidelines for creating a blog.",
                "general",
                "_rocmblogs",
            )

            return {}

    def extract_metadata_from_file(self, file_path: str) -> dict:
        """Extract metadata from blog file."""

        log_message(
            "debug", f"Extracting metadata from {file_path}", "general", "_rocmblogs"
        )

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as file:
                content = file.read()

            match = self.yaml_pattern.match(content)

            if match:
                yaml_content = match.group(1)
                try:
                    metadata = yaml.safe_load(yaml_content)
                    if not isinstance(metadata, dict):
                        log_message(
                            "warning",
                            f"YAML front matter in {file_path} is not a dictionary. Treating as empty metadata.",
                            "general",
                            "_rocmblogs",
                        )
                        return {}

                    category = metadata.get("category", "")
                    tags = metadata.get("tags", "")

                    self.categories.append(category)
                    self.tags.append(tags)

                    log_message(
                        "debug",
                        f"Extracted metadata from {os.path.basename(file_path)} - Category: {category}, Tags: {tags}",
                        "general",
                        "_rocmblogs",
                    )

                    return metadata
                except yaml.YAMLError as error:
                    log_message(
                        "error",
                        f"Error parsing YAML in {file_path}: {error}",
                        "general",
                        "_rocmblogs",
                    )
                    return {}
            else:
                log_message(
                    "warning",
                    f"No YAML front matter found in {file_path}. Look at the guidelines for creating a blog.",
                    "general",
                    "_rocmblogs",
                )
                return {}
        except Exception as e:
            log_message(
                "error",
                f"Could not read or process file {file_path}: {e}",
                "general",
                "_rocmblogs",
            )
            return {}

    def process_blog(self, file_path) -> Blog | None:
        """Create Blog objects from blog files."""

        try:
            metadata = self.extract_metadata_from_file(file_path)
            blog = Blog(file_path, metadata)
            blog.set_file_path(file_path)

            # Check for blog_title attribute
            if not hasattr(blog, "blog_title"):
                # Try to extract title from filename
                filename = os.path.basename(file_path)
                dirname = os.path.basename(os.path.dirname(file_path))

                # Use directory name as title if it's not a generic name
                if dirname and dirname.lower() not in "blogs":
                    blog.blog_title = (
                        dirname.replace("-", " ").replace("_", " ").title()
                    )
                    log_message(
                        "info",
                        "Using directory name as blog title for {filename}: {blog.blog_title}",
                        "general",
                        "_rocmblogs",
                    )
                else:
                    # Use filename without extension as title
                    blog.blog_title = (
                        os.path.splitext(filename)[0]
                        .replace("-", " ")
                        .replace("_", " ")
                        .title()
                    )
                    log_message(
                        "info",
                        "Using filename as blog title: {blog.blog_title}",
                        "general",
                        "_rocmblogs",
                    )

            # Check for date attribute
            if not hasattr(blog, "date") or blog.date is None:
                # Try to extract date from file modification time
                try:
                    mtime = os.path.getmtime(file_path)
                    blog.date = datetime.fromtimestamp(mtime)
                    log_message(
                        "info",
                        f"Using file modification time as blog date for {os.path.basename(file_path)}: {blog.date}",
                        "general",
                        "_rocmblogs",
                    )
                except Exception as date_error:
                    # Use current date as fallback
                    blog.date = datetime.now()
                    log_message(
                        "info",
                        f"Using current date as blog date for {os.path.basename(file_path)}: {blog.date}",
                        "general",
                        "_rocmblogs",
                    )

            # Check for category attribute
            if not hasattr(blog, "category") or not blog.category:
                # Try to use parent directory name as category
                parent_dir = os.path.basename(os.path.dirname(file_path))
                if parent_dir and parent_dir.lower() not in "blogs":
                    blog.category = (
                        parent_dir.replace("-", " ").replace("_", " ").title()
                    )
                    log_message(
                        "info",
                        f"Using parent directory as blog category: {blog.category}",
                        "general",
                        "_rocmblogs",
                    )
                else:
                    # Use grandparent directory if parent is generic
                    grandparent_dir = os.path.basename(
                        os.path.dirname(os.path.dirname(file_path))
                    )
                    if grandparent_dir and grandparent_dir.lower() not in "blogs":
                        blog.category = (
                            grandparent_dir.replace("-", " ").replace("_", " ").title()
                        )
                        log_message(
                            "info",
                            f"Using grandparent directory as blog category: {blog.category}",
                            "general",
                            "_rocmblogs",
                        )
                    else:
                        # Default category
                        blog.category = "ROCm Blog"
                        log_message(
                            "info",
                            f"Using default category for blog: {blog.category}",
                            "general",
                            "_rocmblogs",
                        )

            log_message(
                "debug",
                f"Successfully created blog object for {os.path.basename(file_path)}",
                "general",
                "_rocmblogs",
            )
            return blog
        except Exception as error:
            log_message(
                "error",
                f"Error processing blog {file_path}: {error}",
                "general",
                "_rocmblogs",
            )
            return None

    def create_blog_objects(self) -> None:
        """Create Blog objects from the blog files."""

        if not hasattr(self, "_blog_lock"):
            self._blog_lock = threading.Lock()

        log_message(
            "info",
            f"Creating blog objects from {len(self.blog_paths)} README files",
            "general",
            "_rocmblogs",
        )

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(self.process_blog, self.blog_paths))

        valid_blogs = [blog for blog in results if blog is not None]
        log_message(
            "info",
            f"Found {len(valid_blogs)} valid blogs out of {len(self.blog_paths)} README files",
            "general",
            "_rocmblogs",
        )

        with self._blog_lock:
            added_count = 0
            skipped_count = 0
            seen_titles = set()

            for blog in valid_blogs:
                blog_title = getattr(blog, "blog_title", None)
                if blog_title and blog_title in seen_titles:
                    log_message(
                        "warning",
                        f"Skipping duplicate blog with title: '{blog_title}' from path: {blog.file_path}",
                        "general",
                        "_rocmblogs",
                    )
                    skipped_count += 1
                    continue

                if blog_title:
                    seen_titles.add(blog_title)

                try:
                    self.blogs.add_blog(blog)
                    added_count += 1
                except KeyError as error:
                    log_message(
                        "warning",
                        f"Error adding blog {getattr(blog, 'blog_title', 'Unknown')}: {error}",
                        "general",
                        "_rocmblogs",
                    )

            log_message(
                "info",
                f"Successfully added {added_count} blogs to the blog holder. Skipped {skipped_count} duplicates.",
                "general",
                "_rocmblogs",
            )

    def _setup(self) -> None:
        """Setup the blogs directory."""

        log_message(
            "debug",
            f"Setting up blogs directory: {self.blogs_directory}",
            "general",
            "_rocmblogs",
        )
        if not os.path.exists(self.blogs_directory):
            log_message(
                "critical",
                f"The directory '{self.blogs_directory}' does not exist.",
                "general",
                "_rocmblogs",
            )
            raise FileNotFoundError(
                f"The directory '{self.blogs_directory}' does not exist."
            )
        log_message(
            "debug",
            f"Blogs directory exists: {self.blogs_directory}",
            "general",
            "_rocmblogs",
        )

    def __iter__(self) -> iter:
        """Iterate over the list of blogs."""

        return iter(self.blogs.get_blogs())

    def __len__(self) -> int:
        """Return the number of blogs."""

        return len(self.blogs)

    def __repr__(self) -> str:
        """Return a string representation of the class."""

        return f"ROCmBlogs(blogs_directory='{self.blogs_directory}', blogs={self.blogs}, categories={self.categories}, blog_paths={self.blog_paths})"
