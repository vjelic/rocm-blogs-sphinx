"""
File: __main__.py

Main entry-point for ROCmBlogs package.
"""

import argparse
import cProfile
import os
import sys
import time
import traceback
from pathlib import Path
from sphinx.util import logging as sphinx_logging

from rocm_blogs import ROCmBlogs, metadata_generator
from rocm_blogs._version import __version__

logger = sphinx_logging.getLogger(__name__)

def create_features_template(blogs_dir=None):
    """Create a template features.csv file with all available blog titles."""
    try:
        logger.info("Creating features template file...")
        
        # Initialize ROCmBlogs
        rocmblogs = ROCmBlogs()
        
        # Find blogs directory if not provided
        if not blogs_dir:
            current_file = Path(__file__).resolve()
            src_dir = current_file.parent.parent
            project_root = src_dir.parent
            blogs_dir = project_root / "blogs"
        
        # Set blogs directory
        rocmblogs.blogs_directory = str(blogs_dir)
        logger.info(f"Using blogs directory: {blogs_dir}")
        
        # Find and process blogs
        readme_count = rocmblogs.find_readme_files()
        logger.info(f"Found {readme_count} README files")
        
        rocmblogs.create_blog_objects()
        logger.info(f"Created {len(rocmblogs.blogs)} blog objects")
        
        # Create features template
        template_path = os.path.join(blogs_dir, "features_template.csv")
        rocmblogs.blogs.create_features_template(template_path)
        
        logger.info(f"Features template created at: {template_path}")
        logger.info("To use this template:")
        logger.info("1. Open the file and remove the comment lines")
        logger.info("2. Uncomment the blog titles you want to feature")
        logger.info("3. Save the file as 'features.csv' in the same directory")
        
        return True
    except Exception as e:
        logger.error(f"Error creating features template: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return False

def run_metadata_generation():
    """Run the metadata generator."""
    try:
        logger.info("Starting metadata generation...")
        
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
        metadata_generator(rocmblogs)
        logger.info("Metadata generation completed")
        
        # Log execution time
        execution_time = time.time() - start_time
        logger.info(f"Total execution time: {execution_time:.2f} seconds")
        
        # Log blog count
        blog_count = len(rocmblogs.blogs) if hasattr(rocmblogs.blogs, "__len__") else 0
        logger.info(f"Total blogs processed: {blog_count}")
        logger.debug(f"Blog holder contents: {rocmblogs.blogs}")
        
        return True
    except Exception as e:
        logger.error(f"Error running metadata generation: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main entry-point for ROCmBlogs package."""
    parser = argparse.ArgumentParser(description=f"ROCm Blogs Utilities v{__version__}")
    
    # Add command-line arguments
    parser.add_argument('--create-features-template', action='store_true',
                        help='Create a template features.csv file with all available blog titles')
    parser.add_argument('--metadata', action='store_true',
                        help='Run metadata generation')
    parser.add_argument('--blogs-dir', type=str,
                        help='Path to blogs directory (optional)')
    parser.add_argument('--version', action='store_true',
                        help='Show version information')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Show version and exit if requested
    if args.version:
        print(f"ROCm Blogs version: {__version__}")
        return 0
    
    # Print header
    logger.info(f"ROCm Blogs version: {__version__}")
    logger.info("=" * 50)
    
    # Determine blogs directory if provided
    blogs_dir = None
    if args.blogs_dir:
        blogs_dir = Path(args.blogs_dir)
        if not blogs_dir.exists():
            logger.error(f"Blogs directory not found: {blogs_dir}")
            return 1
    
    # Process commands
    if args.create_features_template:
        success = create_features_template(blogs_dir)
        return 0 if success else 1
    
    elif args.metadata:
        success = run_metadata_generation()
        return 0 if success else 1
    
    else:
        # Default behavior: run metadata generation
        logger.info("No specific command provided, running metadata generation...")
        success = run_metadata_generation()
        return 0 if success else 1


if __name__ == "__main__":
    try:
        # Parse command line arguments first to check if we're just showing version
        if '--version' in sys.argv:
            print(f"ROCm Blogs version: {__version__}")
            sys.exit(0)
        
        # Check if we're creating features template (no need for profiling)
        if '--create-features-template' in sys.argv:
            logger.info("Creating features template...")
            sys.exit(main())
        
        # For other operations, run with profiling
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
        exit_code = main()
        logger.info("ROCm Blogs execution completed")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
