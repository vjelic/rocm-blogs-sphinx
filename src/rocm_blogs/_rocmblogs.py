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

sphinx_diagnostics = sphinx_logging.getLogger(__name__)


class ROCmBlogs:
    def __init__(self) -> None:
        """Initialize the ROCmBlogs class."""

        self.blogs_directory = ""
        self.blogs = BlogHolder()
        self.blog_paths: list[str] = []
        self.categories = []
        self.tags = []
        self.yaml_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def find_readme_files_cache(self) -> None:
        """Cache the README files in the 'blogs' directory."""
        cache_file = Path("readme_files_cache.txt")
        root = Path(self.blogs_directory)
        sphinx_diagnostics.debug(
            f"Current working directory: {os.getcwd()}"
        )

        # Try to load the cached file paths if the cache file exists.
        if cache_file.exists():
            with cache_file.open("r", encoding="utf-8") as f:
                cached_paths = [line.strip() for line in f if line.strip()]
            # Verify that each cached file still exists.
            valid_paths = [path for path in cached_paths if Path(path).exists()]
            if valid_paths and len(valid_paths) == len(cached_paths):
                sphinx_diagnostics.info(
                    f"Loaded {len(valid_paths)} cached README file(s) from {cache_file}"
                )
                self.blog_paths = valid_paths
                return
            else:
                sphinx_diagnostics.info(
                    "Cache invalidated due to deleted or changed files. Rescanning directory."
                )

        # If no valid cache is available, perform a fresh scan.
        sphinx_diagnostics.info(
            f"Scanning {root} for README.md files..."
        )

        candidates = list(root.rglob("README.md"))
        sphinx_diagnostics.debug(
            f"Found {len(candidates)} candidate README.md files"
        )

        # (Optional) Save out all candidates to a file for debugging purposes.
        with open("candidates.txt", "w", encoding="utf-8") as f:
            for candidate in candidates:
                f.write(str(candidate) + "\n")
        sphinx_diagnostics.debug(
            f"Saved {len(candidates)} candidate paths to candidates.txt"
        )

        # Use a list comprehension to process candidates.
        readme_files = [str(path.resolve()) for path in candidates if path.is_file()]

        if not readme_files:
            sphinx_diagnostics.critical(
                "No 'README.md' files found in the blogs directory"
            )
            raise FileNotFoundError("No 'README.md' files found.")

        sphinx_diagnostics.info(
            "Found {len(readme_files)} 'README.md' file(s)."
        )
        self.blog_paths = readme_files

        # Update the cache file with the fresh scan.
        with cache_file.open("w", encoding="utf-8") as f:
            for path in readme_files:
                f.write(path + "\n")
        sphinx_diagnostics.debug(
            f"Updated cache file with {len(readme_files)} README paths"
        )

    def find_readme_files(self) -> None:
        """Find all 'readme.md' files in the blogs directory."""

        root = Path(self.blogs_directory)

        sphinx_diagnostics.debug(
            f"Current working directory: {os.getcwd()}"
        )
        sphinx_diagnostics.info(
            f"Scanning {root} for README.md files..."
        )

        candidates = list(root.rglob("README.md"))
        sphinx_diagnostics.debug(
            f"Found {len(candidates)} candidate README.md files"
        )

        def process_path(path: Path) -> str | None:
            """Check if the path is a file and return the path if it is."""

            if path.is_file():
                return str(path.resolve())
            return None

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(process_path, candidates))

        readme_files = [result for result in results if result is not None]

        if not readme_files:
            sphinx_diagnostics.critical(
                "No 'README.md' files found in the blogs directory"
            )
            raise FileNotFoundError("No 'readme.md' files found.")

        sphinx_diagnostics.info(
            f"Found {len(readme_files)} 'README.md' file(s)."
        )

        self.blog_paths = readme_files

    def find_blogs_directory(self, working_directory: str) -> Path:
        """Find the 'blogs' directory starting from the given working directory."""

        if not os.path.exists(working_directory):
            sphinx_diagnostics.critical(
                f"The directory '{working_directory}' does not exist."
            )
            raise FileNotFoundError(
                f"The directory '{working_directory}' does not exist."
            )

        current_dir = Path(working_directory).resolve()
        sphinx_diagnostics.debug(
            f"Starting search for blogs directory from: {current_dir}"
        )

        while True:
            candidate = current_dir / "blogs"
            sphinx_diagnostics.debug(
                f"Checking if {candidate} is a directory"
            )
            
            if candidate.is_dir():
                sphinx_diagnostics.info(
                    f"Found blogs directory at: {candidate}"
                )
                self.blogs_directory = candidate
                return candidate

            if current_dir == current_dir.parent:
                sphinx_diagnostics.critical(
                    "No 'blogs' directory found in the parent hierarchy."
                )
                raise FileNotFoundError(
                    "No 'blogs' directory found in the parent hierarchy."
                )

            current_dir = current_dir.parent

    def extract_metadata(self) -> dict:
        """Extract metadata from the blog files."""
        if not self.blog_paths:
            sphinx_diagnostics.warning(
                "No blog paths available to extract metadata from"
            )
            return {}

        file_path = self.blog_paths[0]
        sphinx_diagnostics.info(
            f"Extracting metadata from {file_path}"
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
                
                sphinx_diagnostics.debug(
                    f"Extracted metadata - Category: {category}, Tags: {tags}"
                )

                return metadata
            except yaml.YAMLError as error:
                sphinx_diagnostics.error(
                    f"Error parsing YAML in {file_path}: {error}"
                )
                raise ValueError(f"Error parsing YAML: {error}")
        else:
            sphinx_diagnostics.warning(
                f"No YAML front matter found in {file_path}. Look at the guidelines for creating a blog."
            )

            return {}

    def extract_metadata_from_file(self, file_path: str) -> dict:
        """Extract metadata from a blog file."""

        sphinx_diagnostics.debug(
            f"Extracting metadata from {file_path}"
        )

        with open(file_path, "r", encoding="utf-8", errors="replace") as file:
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
                
                sphinx_diagnostics.debug(
                    f"Extracted metadata from {os.path.basename(file_path)} - Category: {category}, Tags: {tags}"
                )

                return metadata
            except yaml.YAMLError as error:
                sphinx_diagnostics.error(
                    f"Error parsing YAML in {file_path}: {error}"
                )
                raise ValueError(
                    f"Error parsing YAML: {error}. Look at the metadata section in the Markdown file."
                )
        else:
            sphinx_diagnostics.warning(
                f"No YAML front matter found in {file_path}. Look at the guidelines for creating a blog."
            )

            return {}

    def process_blog(self, file_path) -> Blog | None:
        """Create Blog objects from the blog files."""

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
                    blog.blog_title = dirname.replace("-", " ").replace("_", " ").title()
                    sphinx_diagnostics.info(
                        f"Using directory name as blog title for {filename}: {blog.blog_title}"
                    )
                else:
                    # Use filename without extension as title
                    blog.blog_title = os.path.splitext(filename)[0].replace("-", " ").replace("_", " ").title()
                    sphinx_diagnostics.info(
                        f"Using filename as blog title: {blog.blog_title}"
                    )
            
            # Check for date attribute
            if not hasattr(blog, "date") or blog.date is None:
                # Try to extract date from file modification time
                try:
                    mtime = os.path.getmtime(file_path)
                    blog.date = datetime.fromtimestamp(mtime)
                    sphinx_diagnostics.info(
                        f"Using file modification time as blog date for {os.path.basename(file_path)}: {blog.date}"
                    )
                except Exception as date_error:
                    # Use current date as fallback
                    blog.date = datetime.now()
                    sphinx_diagnostics.warning(
                        f"Failed to get modification time, using current date for {os.path.basename(file_path)}: {date_error}"
                    )
            
            # Check for category attribute
            if not hasattr(blog, "category") or not blog.category:
                # Try to use parent directory name as category
                parent_dir = os.path.basename(os.path.dirname(file_path))
                if parent_dir and parent_dir.lower() not in "blogs":
                    blog.category = parent_dir.replace("-", " ").replace("_", " ").title()
                    sphinx_diagnostics.info(
                        f"Using parent directory as blog category: {blog.category}"
                    )
                else:
                    # Use grandparent directory if parent is generic
                    grandparent_dir = os.path.basename(os.path.dirname(os.path.dirname(file_path)))
                    if grandparent_dir and grandparent_dir.lower() not in "blogs":
                        blog.category = grandparent_dir.replace("-", " ").replace("_", " ").title()
                        sphinx_diagnostics.info(
                            f"Using grandparent directory as blog category: {blog.category}"
                        )
                    else:
                        # Default category
                        blog.category = "ROCm Blog"
                        sphinx_diagnostics.info(
                            f"Using default category for blog: {blog.category}"
                        )
            
            sphinx_diagnostics.debug(
                f"Successfully created blog object for {os.path.basename(file_path)}"
            )
            return blog
        except Exception as error:
            sphinx_diagnostics.error(
                f"Error processing blog {file_path}: {error}"
            )
            return None

    def create_blog_objects(self) -> None:
        """Create Blog objects from the blog files."""

        if not hasattr(self, "_blog_lock"):
            self._blog_lock = threading.Lock()
            
        sphinx_diagnostics.info(
            f"Creating blog objects from {len(self.blog_paths)} README files"
        )

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(self.process_blog, self.blog_paths))

        valid_blogs = [blog for blog in results if blog is not None]
        sphinx_diagnostics.info(
            f"Found {len(valid_blogs)} valid blogs out of {len(self.blog_paths)} README files"
        )

        with self._blog_lock:
            added_count = 0
            for blog in valid_blogs:
                try:
                    self.blogs.add_blog(blog)
                    added_count += 1
                except KeyError as error:
                    sphinx_diagnostics.warning(
                        f"Error adding blog {getattr(blog, 'blog_title', 'Unknown')}: {error}"
                    )
            
            sphinx_diagnostics.info(
                f"Successfully added {added_count} blogs to the blog holder"
            )

    def _setup(self) -> None:
        """Setup the blogs directory."""

        sphinx_diagnostics.debug(
            f"Setting up blogs directory: {self.blogs_directory}"
        )
        if not os.path.exists(self.blogs_directory):
            sphinx_diagnostics.critical(
                f"The directory '{self.blogs_directory}' does not exist."
            )
            raise FileNotFoundError(
                f"The directory '{self.blogs_directory}' does not exist."
            )
        sphinx_diagnostics.debug(
            f"Blogs directory exists: {self.blogs_directory}"
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
