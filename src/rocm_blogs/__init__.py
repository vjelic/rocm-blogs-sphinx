"""
__init__.py for the rocm_blogs package.

"""

from datetime import datetime
import importlib.resources as pkg_resources
import os
import time
import functools
import traceback
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sphinx.application import Sphinx
from sphinx.util import logging as sphinx_logging
from sphinx.errors import SphinxError

from ._rocmblogs import ROCmBlogs
from ._version import __version__
from .metadata import *
from .constants import *
from .images import *
from .utils import *
from .process import _generate_grid_items, _generate_lazy_loaded_grid_items, _create_pagination_controls, process_single_blog, _process_category

__all__ = ["Blog", "BlogHolder", "ROCmBlogs", "grid_generation", "metadata_generator", "utils",]

def setup_file_logging():
    """Set up file logging for debug messages while preserving Sphinx logging."""
    try:
        # Create logs directory if it doesn't exist
        logs_dir = Path("../logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Create a file handler that logs debug and higher level messages
        log_file = logs_dir / "rocm_blogs_debug.log"
        file_handler = logging.FileHandler(str(log_file), mode='w')
        file_handler.setLevel(logging.DEBUG)
        
        # Create a formatter and set it for the handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Add handler to the root logger to capture all logs
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

        for _, logger in logging.Logger.manager.loggerDict.items():
            if isinstance(logger, logging.Logger):
                logger.propagate = True

        # Return the log file path
        return log_file
    except Exception as error:
        print(f"Error setting up file logging: {error}")
        traceback.print_exc()
        return None

# Set up the logger
sphinx_diagnostics = sphinx_logging.getLogger(__name__)
log_file = setup_file_logging()
if log_file:
    sphinx_diagnostics.info(
        f"Debug logs will be written to {log_file} while maintaining Sphinx console output"
    )

_CRITICAL_ERROR_OCCURRED = False

_BUILD_START_TIME = time.time()

_BUILD_PHASES = {"setup": 0, "update_index": 0, "blog_generation": 0, "other": 0}

def log_total_build_time(sphinx_app, build_exception):
    """Log the total time taken for the entire build process."""
    try:
        global _CRITICAL_ERROR_OCCURRED
        
        build_end_time = time.time()
        total_elapsed_time = build_end_time - _BUILD_START_TIME

        accounted_time = sum(_BUILD_PHASES.values())
        _BUILD_PHASES["other"] = max(0, total_elapsed_time - accounted_time)

        # Format and log the timing summary
        _log_timing_summary(total_elapsed_time)

        if build_exception:
            sphinx_diagnostics.error(
                f"Build completed with errors: {build_exception}"
            )

        if _CRITICAL_ERROR_OCCURRED:
            sphinx_diagnostics.critical(
                "Critical errors occurred during the build process"
            )
            raise ROCmBlogsError("Critical errors occurred during the build process")
    except Exception as error:
        sphinx_diagnostics.critical(
            f"Error in log_total_build_time: {error}"
        )
        sphinx_diagnostics.debug(
            f"Traceback: {traceback.format_exc()}"
        )
        raise


def _log_timing_summary(total_elapsed_time):
    """Format and log the timing summary for all build phases."""
    try:
        # Define the phases to display and their display names
        phases_to_display = [
            ("setup", "Setup phase"),
            ("update_index", "Index update phase"),
            ("blog_generation", "Blog generation phase"),
            ("metadata_generation", "Metadata generation"),
            ("update_posts", "Posts generation"),
            ("update_category_pages", "Category pages generation"),
            ("other", "Other processing")
        ]
        
        # Log the header
        sphinx_diagnostics.info(
            "=" * 80
        )
        sphinx_diagnostics.info(
            "BUILD PROCESS TIMING SUMMARY:"
        )
        sphinx_diagnostics.info(
            "-" * 80
        )
        
        # Log each phase
        for phase_key, phase_display_name in phases_to_display:
            if phase_key in _BUILD_PHASES:
                phase_duration = _BUILD_PHASES[phase_key]
                percentage = (phase_duration / total_elapsed_time * 100) if total_elapsed_time > 0 else 0
                # Format the phase name to align all timing values
                padded_name = f"{phase_display_name}:".ljust(30)
                sphinx_diagnostics.info(
                    f"{padded_name} \033[96m{phase_duration:.2f} seconds\033[0m ({percentage:.1f}%)"
                )
        
        # Log the footer and total time
        sphinx_diagnostics.info(
            "-" * 80
        )
        sphinx_diagnostics.info(
            f"Total build process completed in \033[92m{total_elapsed_time:.2f} seconds\033[0m"
        )
        sphinx_diagnostics.info(
            "=" * 80
        )
    except Exception as error:
        sphinx_diagnostics.error(
            f"Error logging timing summary: {error}"
        )
        sphinx_diagnostics.debug(
            f"Traceback: {traceback.format_exc()}"
        )

def log_time(func):
    """Decorator to log execution time of functions."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            function_start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - function_start_time
            sphinx_diagnostics.info(
                f"{func.__name__} completed in \033[96m{execution_time:.4f} seconds\033[0m"
            )
            return result
        except Exception as error:
            sphinx_diagnostics.error(
                f"Error in {func.__name__}: {error}"
            )
            sphinx_diagnostics.debug(
                f"Traceback: {traceback.format_exc()}"
            )
            raise
    return wrapper

def update_index_file(sphinx_app: Sphinx) -> None:
    """Update the index file with new blog posts."""
    global _CRITICAL_ERROR_OCCURRED
    phase_start_time = time.time()
    phase_name = "update_index"
    
    # Create a log file for this step
    log_filepath, log_file_handle = create_step_log_file(phase_name)
    
    # Track statistics for summary
    total_blogs_processed = 0
    total_blogs_successful = 0
    total_blogs_error = 0
    total_blogs_warning = 0
    total_blogs_skipped = 0
    all_error_details = []

    try:
        if log_file_handle:
            log_file_handle.write("Starting index file update process\n")
            log_file_handle.write("-" * 80 + "\n\n")
        
        # Load templates and styles
        template_html = import_file("rocm_blogs.templates", "index.html")
        css_content = import_file("rocm_blogs.static.css", "index.css")

        if log_file_handle:
            log_file_handle.write("Successfully loaded templates and styles\n")
        
        # Initialize ROCmBlogs and load blog data
        rocm_blogs = ROCmBlogs()
        blogs_directory = rocm_blogs.find_blogs_directory(sphinx_app.srcdir)
        
        if not blogs_directory:
            error_message = "Could not find blogs directory"
            sphinx_diagnostics.error(error_message)
            sphinx_diagnostics.debug(f"Traceback: {traceback.format_exc()}")
            
            if log_file_handle:
                log_file_handle.write(f"ERROR: {error_message}\n")
                log_file_handle.write(f"Traceback: {traceback.format_exc()}\n")
                
            _CRITICAL_ERROR_OCCURRED = True
            raise ROCmBlogsError(error_message)
            
        rocm_blogs.blogs_directory = str(blogs_directory)
        
        if log_file_handle:
            log_file_handle.write(f"Found blogs directory: {blogs_directory}\n")
        
        readme_count = rocm_blogs.find_readme_files()
        
        if log_file_handle:
            log_file_handle.write(f"Found {readme_count} README files\n")
            
        rocm_blogs.create_blog_objects()

        rocm_blogs.blogs.write_to_file()
        
        if log_file_handle:
            log_file_handle.write(f"Created blog objects\n")
        
        # Write blogs to CSV file for reference
        blogs_csv_path = Path(blogs_directory) / "blogs.csv"
        rocm_blogs.blogs.write_to_file(str(blogs_csv_path))
        
        if log_file_handle:
            log_file_handle.write(f"Wrote blog information to {blogs_csv_path}\n")
        
        # Check for features.csv file
        features_csv_path = Path(blogs_directory) / "features.csv"
        featured_blogs = []
        
        if features_csv_path.exists():
            if log_file_handle:
                log_file_handle.write(f"Found features.csv file at {features_csv_path}\n")
                
            featured_blogs = rocm_blogs.blogs.load_featured_blogs_from_csv(str(features_csv_path))
            
            if log_file_handle:
                log_file_handle.write(f"Loaded {len(featured_blogs)} featured blogs from {features_csv_path}\n")
        else:
            if log_file_handle:
                log_file_handle.write(f"Features.csv file not found at {features_csv_path}, no featured blogs will be displayed\n")
        
        # Sort the blogs (this happens on all blogs before filtering)
        rocm_blogs.blogs.sort_blogs_by_date()
        
        if log_file_handle:
            log_file_handle.write("Sorted blogs by date\n")
        
        # Extract category keys from BLOG_CATEGORIES to use for sorting
        category_keys = [category_info.get("category_key", category_info["name"]) for category_info in BLOG_CATEGORIES]
        sphinx_diagnostics.info(
            f"Using category keys for sorting: {category_keys}"
        )
        
        if log_file_handle:
            log_file_handle.write(f"Using category keys for sorting: {category_keys}\n")
            
        rocm_blogs.blogs.sort_blogs_by_category(category_keys)
        
        if log_file_handle:
            log_file_handle.write("Sorted blogs by category\n")
        
        # Get all blogs
        all_blogs = rocm_blogs.blogs.get_blogs()
        
        if log_file_handle:
            log_file_handle.write(f"Retrieved {len(all_blogs)} total blogs\n")
        
        # Filter blogs to only include real blog posts
        filtered_blogs = []
        skipped_count = 0
        
        for blog in all_blogs:
            # Check if this is a genuine blog post (has the blogpost flag set to true)
            if hasattr(blog, "blogpost") and blog.blogpost:
                filtered_blogs.append(blog)
                total_blogs_processed += 1
                if log_file_handle:
                    log_file_handle.write(f"Including blog: {getattr(blog, 'file_path', 'Unknown')}\n")
            else:
                skipped_count += 1
                total_blogs_skipped += 1
                sphinx_diagnostics.debug(
                    f"Skipping non-blog README file for index page: {getattr(blog, 'file_path', 'Unknown')}"
                )
                if log_file_handle:
                    log_file_handle.write(f"Skipping non-blog README file: {getattr(blog, 'file_path', 'Unknown')}\n")
        
        sphinx_diagnostics.info(
            f"Filtered out {skipped_count} non-blog README files for index page, kept {len(filtered_blogs)} genuine blog posts"
        )
        
        if log_file_handle:
            log_file_handle.write(f"Filtered out {skipped_count} non-blog README files, kept {len(filtered_blogs)} genuine blog posts\n")
        
        # Replace all_blogs with filtered_blogs
        all_blogs = filtered_blogs
        
        if not all_blogs:
            warning_message = "No valid blogs found to display on index page"
            sphinx_diagnostics.warning(warning_message)
            
            if log_file_handle:
                log_file_handle.write(f"WARNING: {warning_message}\n")
                
            total_blogs_warning += 1
            return
        
        # Track blogs that have been used to avoid duplication
        used_blogs = []
        
        # Generate grid items for different sections
        sphinx_diagnostics.info(
            "Generating grid items for index page sections"
        )
        
        if log_file_handle:
            log_file_handle.write("Generating grid items for index page sections\n")

        # Create a list of featured blog IDs to exclude them from the main grid
        featured_blog_ids = [id(blog) for blog in featured_blogs]
        
        if log_file_handle:
            log_file_handle.write(f"Generating main grid items with up to {MAIN_GRID_BLOGS_COUNT} blogs\n")
            log_file_handle.write(f"Excluding {len(featured_blog_ids)} featured blogs from main grid\n")
            
        # Filter out featured blogs from the main grid
        non_featured_blogs = [blog for blog in all_blogs if id(blog) not in featured_blog_ids]
        main_grid_items = _generate_grid_items(rocm_blogs, non_featured_blogs, MAIN_GRID_BLOGS_COUNT, used_blogs)
        
        if log_file_handle:
            log_file_handle.write(f"Generated {len(main_grid_items)} main grid items\n")
        
        # Filter blogs by category and ensure they're all blog posts
        ecosystem_blogs = [blog for blog in all_blogs if hasattr(blog, "category") and blog.category == "Ecosystems and Partners"]
        application_blogs = [blog for blog in all_blogs if hasattr(blog, "category") and blog.category == "Applications & models"]
        software_blogs = [blog for blog in all_blogs if hasattr(blog, "category") and blog.category == "Software tools & optimizations"]
        
        if log_file_handle:
            log_file_handle.write(f"Filtered blogs by category:\n")
            log_file_handle.write(f"  - Ecosystems and Partners: {len(ecosystem_blogs)} blogs\n")
            log_file_handle.write(f"  - Applications & models: {len(application_blogs)} blogs\n")
            log_file_handle.write(f"  - Software tools & optimizations: {len(software_blogs)} blogs\n")
        
        # Generate grid items for each category
        if log_file_handle:
            log_file_handle.write(f"Generating category grid items with up to {CATEGORY_GRID_BLOGS_COUNT} blogs per category\n")
            
        ecosystem_grid_items = _generate_grid_items(rocm_blogs, ecosystem_blogs, CATEGORY_GRID_BLOGS_COUNT, used_blogs)
        application_grid_items = _generate_grid_items(rocm_blogs, application_blogs, CATEGORY_GRID_BLOGS_COUNT, used_blogs)
        software_grid_items = _generate_grid_items(rocm_blogs, software_blogs, CATEGORY_GRID_BLOGS_COUNT, used_blogs)
        
        if log_file_handle:
            log_file_handle.write(f"Generated category grid items:\n")
            log_file_handle.write(f"  - Ecosystems and Partners: {len(ecosystem_grid_items)} grid items\n")
            log_file_handle.write(f"  - Applications & models: {len(application_grid_items)} grid items\n")
            log_file_handle.write(f"  - Software tools & optimizations: {len(software_grid_items)} grid items\n")
        
        # Generate featured grid items if we have featured blogs
        featured_grid_items = []
        if featured_blogs:
            if log_file_handle:
                log_file_handle.write(f"Generating featured grid items with {len(featured_blogs)} featured blogs\n")
                
            try:
                # Only generate grid items if we have at least one featured blog
                if len(featured_blogs) > 0:
                    # Generate grid items for featured blogs
                    # Set skip_used=False to ensure all featured blogs are included
                    # even if they've been used in other sections
                    featured_grid_items = _generate_grid_items(rocm_blogs, featured_blogs, len(featured_blogs), used_blogs, skip_used=False)
                    
                    if log_file_handle:
                        log_file_handle.write(f"Generated {len(featured_grid_items)} featured grid items\n")
                else:
                    if log_file_handle:
                        log_file_handle.write("Featured blogs list is empty, skipping grid item generation\n")
            except Exception as featured_error:
                # Log the error but continue with the build
                sphinx_diagnostics.warning(
                    f"Error generating featured grid items: {featured_error}. Continuing without featured blogs."
                )
                sphinx_diagnostics.debug(
                    f"Traceback: {traceback.format_exc()}"
                )
                
                if log_file_handle:
                    log_file_handle.write(f"WARNING: Error generating featured grid items: {featured_error}\n")
                    log_file_handle.write(f"Traceback: {traceback.format_exc()}\n")
                    log_file_handle.write("Continuing without featured blogs\n")
        else:
            if log_file_handle:
                log_file_handle.write("No featured blogs to display\n")
        
        # Replace placeholders in the template
        if log_file_handle:
            log_file_handle.write("Replacing placeholders in the template\n")
            
        updated_html = (
            index_template
            .replace("{grid_items}", "\n".join(main_grid_items))
            .replace("{eco_grid_items}", "\n".join(ecosystem_grid_items))
            .replace("{application_grid_items}", "\n".join(application_grid_items))
            .replace("{software_grid_items}", "\n".join(software_grid_items))
            .replace("{featured_grid_items}", "\n".join(featured_grid_items))
        )
        
        # Write the updated HTML to blogs/index.md
        output_path = Path(blogs_directory) / "index.md"
        
        if log_file_handle:
            log_file_handle.write(f"Writing updated HTML to {output_path}\n")
            
        with output_path.open("w", encoding="utf-8") as output_file:
            output_file.write(updated_html)
            
        total_blogs_successful += 1
        
        # Record timing information
        phase_duration = time.time() - phase_start_time
        _BUILD_PHASES[phase_name] = phase_duration
        sphinx_diagnostics.info(
            f"Successfully updated {output_path} with new content in \033[96m{phase_duration:.2f} seconds\033[0m"
        )
        
        if log_file_handle:
            log_file_handle.write(f"Successfully updated {output_path} with new content in {phase_duration:.2f} seconds\n")
        
    except ROCmBlogsError:
        # Re-raise ROCmBlogsError to stop the build
        _BUILD_PHASES[phase_name] = time.time() - phase_start_time
        
        if log_file_handle:
            log_file_handle.write(f"ERROR: ROCmBlogsError occurred\n")
            log_file_handle.write(f"Traceback: {traceback.format_exc()}\n")
            
        raise
    except Exception as error:
        error_message = f"Error updating index file: {error}"
        sphinx_diagnostics.critical(error_message)
        sphinx_diagnostics.debug(f"Traceback: {traceback.format_exc()}")
        
        if log_file_handle:
            log_file_handle.write(f"CRITICAL ERROR: {error_message}\n")
            log_file_handle.write(f"Traceback: {traceback.format_exc()}\n")
            
        _BUILD_PHASES[phase_name] = time.time() - phase_start_time
        _CRITICAL_ERROR_OCCURRED = True
        raise ROCmBlogsError(error_message) from error
    finally:
        # Write summary to log file
        if log_file_handle:
            end_time = time.time()
            total_duration = end_time - phase_start_time
            
            log_file_handle.write("\n" + "=" * 80 + "\n")
            log_file_handle.write("INDEX UPDATE SUMMARY\n")
            log_file_handle.write("-" * 80 + "\n")
            log_file_handle.write(f"Total blogs processed: {total_blogs_processed}\n")
            log_file_handle.write(f"Successful: {total_blogs_successful}\n")
            log_file_handle.write(f"Errors: {total_blogs_error}\n")
            log_file_handle.write(f"Warnings: {total_blogs_warning}\n")
            log_file_handle.write(f"Skipped: {total_blogs_skipped}\n")
            log_file_handle.write(f"Total time: {total_duration:.2f} seconds\n")
            
            if all_error_details:
                log_file_handle.write("\nERROR DETAILS:\n")
                log_file_handle.write("-" * 80 + "\n")
                for index, error_detail in enumerate(all_error_details):
                    log_file_handle.write(f"{index+1}. Blog: {error_detail['blog']}\n")
                    log_file_handle.write(f"   Error: {error_detail['error']}\n\n")
            
            log_file_handle.close()

def blog_generation(sphinx_app: Sphinx) -> None:
    """Generate blog pages with styling and metadata."""
    global _CRITICAL_ERROR_OCCURRED
    phase_start_time = time.time()
    processed_count = 0
    error_count = 0

    try:
        # Initialize ROCmBlogs and load blog data
        build_env = sphinx_app.builder.env
        source_dir = Path(build_env.srcdir)
        rocm_blogs = ROCmBlogs()
        
        # Find and process blogs
        blogs_directory = rocm_blogs.find_blogs_directory(str(source_dir))
        if not blogs_directory:
            sphinx_diagnostics.error(
                "Could not find blogs directory"
            )
            sphinx_diagnostics.debug(
                f"Traceback: {traceback.format_exc()}"
            )
            _CRITICAL_ERROR_OCCURRED = True
            raise ROCmBlogsError("Could not find blogs directory")
            
        rocm_blogs.blogs_directory = str(blogs_directory)
        rocm_blogs.find_readme_files()
        rocm_blogs.create_blog_objects()
        rocm_blogs.blogs.sort_blogs_by_date()
        
        # Get all blogs
        blog_list = rocm_blogs.blogs.get_blogs()
        total_blogs = len(blog_list)
        
        if not blog_list:
            sphinx_diagnostics.warning(
                "No blogs found to process"
            )
            return
            
        max_workers = os.cpu_count()
        sphinx_diagnostics.info(
            f"Processing {total_blogs} blogs with {max_workers} workers"
        )

        # Process blogs with thread pool
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a list of futures
            processing_futures = []
            for blog in blog_list:
                future = executor.submit(process_single_blog, blog, rocm_blogs)
                processing_futures.append(future)

            # Process results as they complete
            for future in processing_futures:
                try:
                    future.result()  # This will raise any exceptions from the thread
                except Exception as processing_error:
                    sphinx_diagnostics.warning(
                        f"Error processing blog: {processing_error}"
                    )

        # Log completion statistics
        phase_end_time = time.time()
        phase_duration = phase_end_time - phase_start_time
        _BUILD_PHASES["blog_generation"] = phase_duration

        # If total errors account for more than 25% of total blogs, raise a critical error
        error_threshold = total_blogs * 0.25
        if error_count > error_threshold:
            sphinx_diagnostics.critical(
                f"Too many errors occurred during blog generation: {error_count} errors"
            )
            sphinx_diagnostics.debug(
                f"Traceback: {traceback.format_exc()}"
            )
            _CRITICAL_ERROR_OCCURRED = True
            raise ROCmBlogsError(f"Too many errors occurred during blog generation: {error_count} errors")
        
        sphinx_diagnostics.info(
            f"Blog generation completed: {processed_count} successful, {error_count} failed, "
            f"in \033[96m{phase_duration:.2f} seconds\033[0m"
        )
    except ROCmBlogsError:
        _BUILD_PHASES["blog_generation"] = time.time() - phase_start_time
        sphinx_diagnostics.debug(
            f"Traceback: {traceback.format_exc()}"
        )
        raise
    except Exception as generation_error:
        sphinx_diagnostics.critical(
            f"Error generating blog pages: {generation_error}"
        )
        sphinx_diagnostics.debug(
            f"Traceback: {traceback.format_exc()}"
        )
        _BUILD_PHASES["blog_generation"] = time.time() - phase_start_time
        _CRITICAL_ERROR_OCCURRED = True
        raise ROCmBlogsError(f"Error generating blog pages: {generation_error}") from generation_error

def run_metadata_generator(sphinx_app: Sphinx) -> None:
    """Run the metadata generator during the build process."""
    global _CRITICAL_ERROR_OCCURRED
    phase_start_time = time.time()
    phase_name = "metadata_generation"

    try:
        sphinx_diagnostics.info(
            "Running metadata generator..."
        )

        # Initialize ROCmBlogs and load blog data
        rocm_blogs = ROCmBlogs()
        blogs_directory = rocm_blogs.find_blogs_directory(sphinx_app.srcdir)
        
        if not blogs_directory:
            sphinx_diagnostics.error(
                "Could not find blogs directory"
            )
            _CRITICAL_ERROR_OCCURRED = True
            raise ROCmBlogsError("Could not find blogs directory")
            
        rocm_blogs.blogs_directory = str(blogs_directory)
        
        # Find and process readme files
        readme_count = rocm_blogs.find_readme_files()
        sphinx_diagnostics.info(
            f"Found {readme_count} readme files to process"
        )
        
        # Generate metadata
        metadata_generator(rocm_blogs)
        
        # Record timing information
        phase_duration = time.time() - phase_start_time
        _BUILD_PHASES[phase_name] = phase_duration
        sphinx_diagnostics.info(
            f"Metadata generation completed in \033[96m{phase_duration:.2f} seconds\033[0m"
        )
        
    except ROCmBlogsError:
        # Re-raise ROCmBlogsError to stop the build
        _BUILD_PHASES[phase_name] = time.time() - phase_start_time
        raise
    except Exception as metadata_error:
        sphinx_diagnostics.critical(
            f"Failed to generate metadata: {metadata_error}"
        )
        sphinx_diagnostics.debug(
            f"Traceback: {traceback.format_exc()}"
        )
        _BUILD_PHASES[phase_name] = time.time() - phase_start_time
        _CRITICAL_ERROR_OCCURRED = True
        raise ROCmBlogsError(f"Failed to generate metadata: {metadata_error}") from metadata_error

def update_posts_file(sphinx_app: Sphinx) -> None:
    """Generate paginated posts.md files with lazy-loaded grid items for performance."""
    phase_start_time = time.time()

    # Configuration
    BLOGS_PER_PAGE = POST_BLOGS_PER_PAGE
    
    try:
        # Load templates and styles
        template_html = import_file("rocm_blogs.templates", "posts.html")
        pagination_template = import_file("rocm_blogs.templates", "pagination.html")
        css_content = import_file("rocm_blogs.static.css", "index.css")
        pagination_css = import_file("rocm_blogs.static.css", "pagination.css")
        
        # Initialize ROCmBlogs and load blog data
        rocm_blogs = ROCmBlogs()
        blogs_directory = rocm_blogs.find_blogs_directory(sphinx_app.srcdir)
        rocm_blogs.blogs_directory = str(blogs_directory)
        rocm_blogs.find_readme_files()
        rocm_blogs.create_blog_objects()
        
        # Get all blogs first
        all_blogs = rocm_blogs.blogs.get_blogs()
        
        # Filter blogs to only include real blog posts
        filtered_blogs = []
        skipped_count = 0
        for blog in all_blogs:
            # Check if this is a genuine blog post (has the blogpost flag set to true)
            if hasattr(blog, "blogpost") and blog.blogpost:
                filtered_blogs.append(blog)
            else:
                skipped_count += 1
                sphinx_diagnostics.debug(
                    f"Skipping non-blog README file: {getattr(blog, 'file_path', 'Unknown')}"
                )
        
        sphinx_diagnostics.info(
            f"Filtered out {skipped_count} non-blog README files, kept {len(filtered_blogs)} genuine blog posts"
        )

        sorted_blogs = sorted(filtered_blogs, 
                             key=lambda blog: getattr(blog, 'date', datetime.now()), 
                             reverse=True)
        
        # Get all filtered blogs and calculate pagination
        all_blogs = sorted_blogs
        total_blogs = len(all_blogs)
        total_pages = max(1, (total_blogs + BLOGS_PER_PAGE - 1) // BLOGS_PER_PAGE)
        
        sphinx_diagnostics.info(
            f"Generating {total_pages} paginated posts pages with {BLOGS_PER_PAGE} blogs per page"
        )
        
        # Generate all grid items in parallel with lazy loading
        all_grid_items = _generate_lazy_loaded_grid_items(rocm_blogs, all_blogs)
        
        # Current datetime for template
        current_datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        # Generate each page
        for page_num in range(1, total_pages + 1):
            # Get grid items for this page
            start_index = (page_num - 1) * BLOGS_PER_PAGE
            end_index = min(start_index + BLOGS_PER_PAGE, len(all_grid_items))
            page_grid_items = all_grid_items[start_index:end_index]
            grid_content = "\n".join(page_grid_items)
            
            # Create pagination controls
            pagination_controls = _create_pagination_controls(
                pagination_template, page_num, total_pages, "posts"
            )
            
            # Add page suffix for pages after the first
            page_title_suffix = f" - Page {page_num}" if page_num > 1 else ""
            page_description_suffix = f" (Page {page_num} of {total_pages})" if page_num > 1 else ""
            
            # Create the final page content
            page_content = POSTS_TEMPLATE.format(
                CSS=css_content,
                PAGINATION_CSS=pagination_css,
                HTML=template_html.replace("{grid_items}", grid_content).replace("{datetime}", current_datetime),
                pagination_controls=pagination_controls,
                page_title_suffix=page_title_suffix,
                page_description_suffix=page_description_suffix,
                current_page=page_num,
            )
            
            # Determine output filename and write the file
            output_filename = "posts.md" if page_num == 1 else f"posts-page{page_num}.md"
            output_path = Path(blogs_directory) / output_filename
            
            with output_path.open("w", encoding="utf-8") as output_file:
                output_file.write(page_content)
            
            sphinx_diagnostics.info(
                f"Created {output_path} with {len(page_grid_items)} grid items (page {page_num}/{total_pages})"
            )
        
        # Record timing information
        phase_duration = time.time() - phase_start_time
        _BUILD_PHASES["update_posts"] = phase_duration
        sphinx_diagnostics.info(
            f"Successfully created {total_pages} paginated posts pages in \033[96m{phase_duration:.2f} seconds\033[0m"
        )
        
    except Exception as page_error:
        sphinx_diagnostics.critical(
            f"Failed to create posts files: {page_error}"
        )
        sphinx_diagnostics.debug(
            f"Traceback: {traceback.format_exc()}"
        )
        _BUILD_PHASES["update_posts"] = time.time() - phase_start_time
        raise ROCmBlogsError(f"Failed to create posts files: {page_error}") from page_error

def update_category_pages(sphinx_app: Sphinx) -> None:
    """Generate paginated category pages with lazy-loaded grid items for performance."""
    phase_start_time = time.time()
    
    try:
        # Load templates and styles
        pagination_template = import_file("rocm_blogs.templates", "pagination.html")
        css_content = import_file("rocm_blogs.static.css", "index.css")
        pagination_css = import_file("rocm_blogs.static.css", "pagination.css")
        
        # Initialize ROCmBlogs and load blog data
        rocm_blogs = ROCmBlogs()
        blogs_directory = rocm_blogs.find_blogs_directory(sphinx_app.srcdir)
        rocm_blogs.blogs_directory = str(blogs_directory)
        rocm_blogs.find_readme_files()
        rocm_blogs.create_blog_objects()
        rocm_blogs.blogs.sort_blogs_by_date()
        rocm_blogs.blogs.sort_blogs_by_category(rocm_blogs.categories)
        
        # Current datetime for template
        current_datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        # Process each category
        for category_info in BLOG_CATEGORIES:
            _process_category(
                category_info, 
                rocm_blogs, 
                blogs_directory, 
                pagination_template, 
                css_content, 
                pagination_css, 
                current_datetime,
                CATEGORY_TEMPLATE
            )
        
        # Record timing information
        phase_duration = time.time() - phase_start_time
        _BUILD_PHASES["update_category_pages"] = phase_duration
        sphinx_diagnostics.info(
            f"Category pages generation completed in \033[96m{phase_duration:.2f} seconds\033[0m"
        )
        
    except Exception as category_error:
        sphinx_diagnostics.critical(
            f"Failed to generate category pages: {category_error}"
        )
        sphinx_diagnostics.debug(
            f"Traceback: {traceback.format_exc()}"
        )
        _BUILD_PHASES["update_category_pages"] = time.time() - phase_start_time
        raise ROCmBlogsError(f"Failed to generate category pages: {category_error}") from category_error

def setup(sphinx_app: Sphinx) -> dict:
    """Set up the ROCm Blogs extension."""
    global _CRITICAL_ERROR_OCCURRED
    phase_start_time = time.time()
    phase_name = "setup"

    sphinx_diagnostics.info(
        f"Setting up ROCm Blogs extension, version: {__version__}"
    )
    sphinx_diagnostics.info(
        f"Build process started at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(_BUILD_START_TIME))}"
    )

    try:
        sphinx_diagnostics.info(
            "Setting up ROCm Blogs extension..."
        )
        
        # Set up static files
        _setup_static_files(sphinx_app)
        
        # Register event handlers
        _register_event_handlers(sphinx_app)
        
        # Record timing information
        phase_duration = time.time() - phase_start_time
        _BUILD_PHASES[phase_name] = phase_duration
        sphinx_diagnostics.info(
            f"ROCm Blogs extension setup completed in \033[96m{phase_duration:.2f} seconds\033[0m"
        )
        
        # Return extension metadata
        return {
            "version": __version__,
            "parallel_read_safe": True,
            "parallel_write_safe": False,
        }
        
    except Exception as setup_error:
        sphinx_diagnostics.critical(
            f"Failed to set up ROCm Blogs extension: {setup_error}"
        )
        sphinx_diagnostics.debug(
            f"Traceback: {traceback.format_exc()}"
        )
        _BUILD_PHASES[phase_name] = time.time() - phase_start_time
        _CRITICAL_ERROR_OCCURRED = True
        raise ROCmBlogsError(f"Failed to set up ROCm Blogs extension: {setup_error}") from setup_error


def _setup_static_files(sphinx_app: Sphinx) -> None:
    """Set up static files for the ROCm Blogs extension."""
    try:
        # Add static directory to Sphinx
        static_directory = (Path(__file__).parent / "static").resolve()
        sphinx_app.config.html_static_path.append(str(static_directory))
        
        # Add JavaScript files
        sphinx_app.add_js_file("js/performance.js")

        try:
            generic_img_path = static_directory / "images" / "generic.jpg"
            if generic_img_path.exists():
                optimize_generic_image(str(generic_img_path))
            else:
                sphinx_diagnostics.warning(
                    f"Generic image not found at {generic_img_path}"
                )
        except Exception as image_error:
            sphinx_diagnostics.warning(
                f"Error optimizing generic image: {image_error}"
            )
            sphinx_diagnostics.debug(
                f"Traceback: {traceback.format_exc()}"
            )
            
        sphinx_diagnostics.info(
            "Static files setup completed"
        )
        
    except Exception as static_files_error:
        sphinx_diagnostics.error(
            f"Error setting up static files: {static_files_error}"
        )
        sphinx_diagnostics.debug(
            f"Traceback: {traceback.format_exc()}"
        )
        raise


def _register_event_handlers(sphinx_app: Sphinx) -> None:
    """Register event handlers for the ROCm Blogs extension."""
    try:
        # Register event handlers
        sphinx_app.connect("builder-inited", update_index_file)
        sphinx_app.connect("builder-inited", blog_generation)
        sphinx_app.connect("builder-inited", update_posts_file)
        sphinx_app.connect("builder-inited", update_category_pages)
        sphinx_app.connect("builder-inited", run_metadata_generator)
        sphinx_app.connect("build-finished", log_total_build_time)
        
        sphinx_diagnostics.info(
            "Event handlers registered"
        )
        
    except Exception as handler_error:
        sphinx_diagnostics.error(
            f"Error registering event handlers: {handler_error}"
        )
        sphinx_diagnostics.debug(
            f"Traceback: {traceback.format_exc()}"
        )
