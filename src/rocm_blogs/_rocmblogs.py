import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from .blog import Blog
from .holder import BlogHolder


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
        """ Cache the README files in the 'blogs' directory. """
        cache_file = Path("readme_files_cache.txt")
        root = Path(self.blogs_directory)
        print("Current working directory:", os.getcwd())

        # Try to load the cached file paths if the cache file exists.
        if cache_file.exists():
            with cache_file.open("r", encoding="utf-8") as f:
                cached_paths = [line.strip() for line in f if line.strip()]
            # Verify that each cached file still exists.
            valid_paths = [path for path in cached_paths if Path(path).exists()]
            if valid_paths and len(valid_paths) == len(cached_paths):
                print(f"Loaded {len(valid_paths)} cached README file(s) from {cache_file}")
                self.blog_paths = valid_paths
                return
            else:
                print("Cache invalidated due to deleted or changed files. Rescanning directory.")

        # If no valid cache is available, perform a fresh scan.
        candidates = list(root.rglob("README.md"))

        # (Optional) Save out all candidates to a file for debugging purposes.
        with open("candidates.txt", "w", encoding="utf-8") as f:
            for candidate in candidates:
                f.write(str(candidate) + "\n")

        # Use a list comprehension to process candidates.
        readme_files = [str(path.resolve()) for path in candidates if path.is_file()]

        if not readme_files:
            raise FileNotFoundError("No 'README.md' files found.")

        print(f"Found {len(readme_files)} 'README.md' file(s).")
        self.blog_paths = readme_files

        # Update the cache file with the fresh scan.
        with cache_file.open("w", encoding="utf-8") as f:
            for path in readme_files:
                f.write(path + "\n")

    def find_readme_files(self) -> None:
        """Find all 'readme.md' files in the blogs directory."""

        root = Path(self.blogs_directory)

        print("Current working directory: ", os.getcwd())

        candidates = list(root.rglob("README.md"))

        def process_path(path: Path) -> str | None:
            """Check if the path is a file and return the path if it is."""

            if path.is_file():
                return str(path.resolve())
            return None

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(process_path, candidates))

        readme_files = [result for result in results if result is not None]

        if not readme_files:
            raise FileNotFoundError("No 'readme.md' files found.")

        print(f"Found {len(readme_files)} 'readme.md' file(s).")

        self.blog_paths = readme_files

    def find_blogs_directory(self, working_directory: str) -> Path:
        """Find the 'blogs' directory starting from the given working directory."""

        if not os.path.exists(working_directory):
            raise FileNotFoundError(f"The directory '{working_directory}' does not exist.")
        
        current_dir = Path(working_directory).resolve()

        while True:
            candidate = current_dir / "blogs"
            if candidate.is_dir():
                self.blogs_directory = candidate
                return candidate

            if current_dir == current_dir.parent:
                raise FileNotFoundError("No 'blogs' directory found in the parent hierarchy.")

            current_dir = current_dir.parent

    def extract_metadata(self) -> dict:
        """Extract metadata from the blog files."""

        print(f"Extracting metadata from {file_path}")

        for file_path in self.blog_paths:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()

            match = self.yaml_pattern.match(content)

            if match:
                yaml_content = match.group(1)

                try:
                    metadata = yaml.safe_load(yaml_content)

                    self.categories.append(metadata.get("category", ""))
                    self.tags.append(metadata.get("tags", ""))

                    return metadata
                except yaml.YAMLError as error:
                    raise ValueError(f"Error parsing YAML: {error}")
            else:
                print(
                    f"No YAML front matter found in {file_path}. Look at the guidelines for creating a blog."
                )

                return {}

    def extract_metadata_from_file(self, file_path: str) -> dict:
        """Extract metadata from a blog file."""

        print(f"Extracting metadata from {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="replace") as file:
            content = file.read()

        match = self.yaml_pattern.match(content)

        if match:
            yaml_content = match.group(1)

            try:
                metadata = yaml.safe_load(yaml_content)

                self.categories.append(metadata.get("category", ""))
                self.tags.append(metadata.get("tags", ""))

                return metadata
            except yaml.YAMLError as error:
                raise ValueError(
                    f"Error parsing YAML: {error}. Look at the metadata section in the Markdown file."
                )
        else:
            print(
                f"No YAML front matter found in {file_path}. Look at the guidelines for creating a blog."
            )

            return {}

    def process_blog(self, file_path) -> Blog | None:
        """Create Blog objects from the blog files."""

        metadata = self.extract_metadata_from_file(file_path)
        blog = Blog(file_path, metadata)
        blog.set_file_path(file_path)

        if hasattr(blog, "blog_title") and hasattr(blog, "date"):
            return blog
        return None

    def create_blog_objects(self) -> None:
        """Create Blog objects from the blog files."""

        if not hasattr(self, "_blog_lock"):
            self._blog_lock = threading.Lock()

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(self.process_blog, self.blog_paths))

        valid_blogs = [blog for blog in results if blog is not None]

        with self._blog_lock:
            for blog in valid_blogs:
                try:
                    self.blogs.add_blog(blog)
                except KeyError as error:
                    print(f"Error adding blog: {error}")

    def _setup(self) -> None:
        """Setup the blogs directory."""

        if not os.path.exists(self.blogs_directory):
            raise FileNotFoundError(
                f"The directory '{self.blogs_directory}' does not exist."
            )

    def __iter__(self) -> iter:
        """Iterate over the list of blogs."""

        return iter(self.blogs.get_blogs())

    def __len__(self) -> int:
        """Return the number of blogs."""

        return len(self.blogs)

    def __repr__(self) -> str:
        """Return a string representation of the class."""

        # return all blog objects
        return f"ROCmBlogs({(self.blogs)} blogs)"