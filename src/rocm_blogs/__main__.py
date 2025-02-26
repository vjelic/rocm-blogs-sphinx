"""
File: __main__.py

Main entry-point for ROCmBlogs package.

find_readme_files() - Find all 'readme.md' files in the blogs directory.
create_blog_objects() - Create Blog objects from the metadata.
sort_blogs_by_date() - Sort the blogs by date.
sort_blogs_by_category() - Sort the blogs by category.
generate_grid() - Generate a grid of blog posts.
"""

import os
import time
import cProfile
import re
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from rocm_blogs import ROCmBlogs
from rocm_blogs import metadata_generator


def main():
    """Main entry-point for ROCmBlogs package."""

    start_time = time.time()

    rocmblogs = ROCmBlogs()

    print("Current working directory: ", os.getcwd())

    current_file = Path(__file__).resolve()
    print("Current file:", current_file)

    src_dir = current_file.parent.parent
    print("src_dir:", src_dir)

    project_root = src_dir.parent
    print("project_root:", project_root)

    blogs_dir = project_root / "blogs"
    print("Absolute path to blogs:", blogs_dir)

    metadata_generator(rocmblogs)

    print(f"Time taken: {time.time() - start_time} seconds")

    print(rocmblogs.blogs)


if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.runcall(main)
    profiler.print_stats()

    main()

