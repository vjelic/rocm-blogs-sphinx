"""
File: __main__.py

Main entry-point for ROCmBlogs package.
"""

import cProfile
import os
import time
from pathlib import Path
from sphinx.util import logging as sphinx_logging

from rocm_blogs import ROCmBlogs, metadata_generator
from rocm_blogs._version import __version__


logger = sphinx_logging.getLogger(__name__)

def main():
    """Main entry-point for ROCmBlogs package."""
    logger.info(f"ROCm Blogs version: {__version__}")
    logger.info("=" * 50)

    start_time = time.time()

    rocmblogs = ROCmBlogs()
    logger.info("Initialized ROCmBlogs instance")

    current_working_dir = os.getcwd()
    logger.debug(f"Current working directory: {current_working_dir}")

    current_file = Path(__file__).resolve()
    logger.debug(f"Current file: {current_file}")

    src_dir = current_file.parent.parent
    logger.debug(f"Source directory: {src_dir}")

    project_root = src_dir.parent
    logger.debug(f"Project root: {project_root}")

    blogs_dir = project_root / "blogs"
    logger.info(f"Absolute path to blogs: {blogs_dir}")

    # Run metadata generator
    logger.info("Starting metadata generation...")
    metadata_generator(rocmblogs)
    logger.info("Metadata generation completed")

    # Log execution time
    execution_time = time.time() - start_time
    logger.info(f"Total execution time: {execution_time:.2f} seconds")

    # Log blog count
    blog_count = len(rocmblogs.blogs) if hasattr(rocmblogs.blogs, "__len__") else 0
    logger.info(f"Total blogs processed: {blog_count}")
    logger.debug(f"Blog holder contents: {rocmblogs.blogs}")


if __name__ == "__main__":
    logger.info("Starting ROCm Blogs with profiling enabled")
    
    # Run with profiling first
    profiler = cProfile.Profile()
    profiler.runcall(main)
    
    # Log profiling results
    import io
    import pstats
    
    # Capture profiler stats to string buffer
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # Print top 20 functions by cumulative time
    
    # Log the profiler results
    logger.info("Profiling results (top 20 functions by cumulative time):")
    for line in s.getvalue().splitlines():
        if line.strip():
            logger.info(line)
    
    # Run normally
    logger.info("Starting ROCm Blogs main execution")
    main()
    logger.info("ROCm Blogs execution completed")
