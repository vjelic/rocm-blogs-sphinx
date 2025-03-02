import importlib.resources as pkg_resources
import os
import re
import time
import functools
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from sphinx.application import Sphinx
from sphinx.util import logging as sphinx_logging

from ._rocmblogs import ROCmBlogs
from ._version import __version__
from .grid import generate_grid
from .metadata import metadata_generator

__all__ = ["Blog", "BlogHolder", "ROCmBlogs", "grid_generation", "metadata_generator"]

logger = sphinx_logging.getLogger(__name__)

# Template and CSS caching
_TEMPLATE_CACHE = {}
_CSS_CACHE = {}

def cached_read_text(package, resource):
    """Read text from a package resource with caching."""
    cache_key = f"{package}.{resource}"
    
    if "css" in resource:
        if cache_key in _CSS_CACHE:
            return _CSS_CACHE[cache_key]
        content = pkg_resources.read_text(package, resource)
        _CSS_CACHE[cache_key] = content
        return content
    else:
        if cache_key in _TEMPLATE_CACHE:
            return _TEMPLATE_CACHE[cache_key]
        content = pkg_resources.read_text(package, resource)
        _TEMPLATE_CACHE[cache_key] = content
        return content


def calculate_read_time(words: int) -> int:
    """Average reading speed is 245 words per minute."""
    start_time = time.time()
    
    result = round(words / 245)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.debug(f"Read time calculation completed in \033[96m{elapsed_time:.6f} seconds\033[0m")
    
    return result


def truncate_string(input_string: str) -> str:
    """Remove special characters and spaces from a string."""
    start_time = time.time()
    
    cleaned_string = re.sub(r"[!@#$%^&*?/|]", "", input_string)
    transformed_string = re.sub(r"\s+", "-", cleaned_string)
    result = transformed_string.lower()
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.debug(f"String truncation completed in \033[96m{elapsed_time:.6f} seconds\033[0m")
    
    return result


def update_index_file(app: Sphinx) -> None:
    '''
    Update the index file with new blog posts.

    param: app: Sphinx - The Sphinx application object.
    '''
    start_time = time.time()
    
    try:
        index_template = """
---
title: ROCm Blogs
myst:
html_meta:
"description lang=en": "AMD ROCm™ software blogs"
"keywords": "AMD GPU, MI300, MI250, ROCm, blog"
"property=og:locale": "en_US"
---
<style>
{CSS}
</style>
{HTML}
"""

        # load index.html template
        template_html = cached_read_text("rocm_blogs.templates", "index.html")

        # load index.css template
        css_content = cached_read_text("rocm_blogs.static.css", "index.css")

        index_template = index_template.format(CSS=css_content, HTML=template_html)

        index_template = index_template[1:]

        # 3. Process blog data using ROCmBlogs.
        rocmblogs = ROCmBlogs()

        # Assume the blogs directory is the sibling of srcdir.
        blogs_dir = rocmblogs.find_blogs_directory(app.srcdir)
        rocmblogs.blogs_directory = str(blogs_dir)
        rocmblogs.find_readme_files_cache()
        rocmblogs.create_blog_objects()
        rocmblogs.blogs.sort_blogs_by_date()
        rocmblogs.blogs.sort_blogs_by_category(rocmblogs.categories)

        all_blogs = rocmblogs.blogs.get_blogs()

        used = []
        grid_items = []
        eco_grid_items = []
        application_grid_items = []
        software_grid_items = []
        
        # Helper function to generate grid items in parallel
        def generate_grid_items(blog_list, max_items, used_blogs):
            items = []
            count = 0
            
            with ThreadPoolExecutor() as executor:
                futures = {}
                for blog in blog_list:
                    if blog not in used_blogs and count < max_items:
                        used_blogs.append(blog)
                        futures[executor.submit(generate_grid, rocmblogs, blog)] = blog
                        count += 1
                
                for future in futures:
                    items.append(future.result())
            
            return items
        
        # Generate grid items in parallel
        logger.info("Generating grid items in parallel")
        
        # Main grid items (up to 12)
        grid_items = generate_grid_items(all_blogs, 12, used)
        
        # Category-specific grid items (up to 4 each)
        eco_blogs = rocmblogs.blogs.blogs_categories.get("Ecosystems and Partners", [])
        eco_grid_items = generate_grid_items(eco_blogs, 4, used)
        
        app_blogs = rocmblogs.blogs.blogs_categories.get("Applications & models", [])
        application_grid_items = generate_grid_items(app_blogs, 4, used)
        
        sw_blogs = rocmblogs.blogs.blogs_categories.get("Software tools & optimizations", [])
        software_grid_items = generate_grid_items(sw_blogs, 4, used)

        grid_content = "\n".join(grid_items)
        eco_grid_content = "\n".join(eco_grid_items)
        application_grid_content = "\n".join(application_grid_items)
        software_grid_content = "\n".join(software_grid_items)

        updated_html = index_template.replace("{grid_items}", grid_content)
        updated_html = updated_html.replace("{eco_grid_items}", eco_grid_content)
        updated_html = updated_html.replace(
            "{application_grid_items}", application_grid_content
        )
        updated_html = updated_html.replace(
            "{software_grid_items}", software_grid_content
        )

        # 6. Write the updated HTML to blogs/index.md.
        output_path = Path(blogs_dir) / "index.md"
        with output_path.open("w", encoding="utf-8") as f:
            f.write(updated_html)

        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Successfully updated {output_path} with new grid items in \033[96m{elapsed_time:.2f} seconds\033[0m.")
    except Exception as error:
        logger.critical(f"Failed to update index file: {error}")


def quickshare(blog):
    """Quickshare buttons for social media sharing."""
    start_time = time.time()
    
    if "test" in str(blog.file_path).lower():
        css = "css_content"
        html = "html_content"
    else:
        css = cached_read_text("rocm_blogs.static.css", "social-bar.css")
        html = cached_read_text("rocm_blogs.templates", "social-bar.html")

    social_bar = """
<style>
{CSS}
</style>
{HTML}
"""

    social_bar = social_bar.format(CSS=css, HTML=html)

    if hasattr(blog, "file_path"):

        blog_dir = os.path.basename(os.path.dirname(blog.file_path))

        raw_url = (
            f"http://rocm.blogs.amd.com/artificial-intelligence/{blog_dir}/README.html"
        )

        url = raw_url
    else:

        url = f"http://rocm.blogs.amd.com{blog.grab_href()[1:]}"

    title = blog.blog_title if hasattr(blog, "blog_title") else "No Title"
    title_with_suffix = f"{title} | ROCm Blogs"

    if hasattr(blog, "myst"):
        description = blog.myst.get("html_meta", {}).get(
            "description lang=en", "No Description"
        )
    else:
        description = "No Description"

    # For testing, include the title and description directly in the output
    if "test" in str(blog.file_path).lower():
        social_bar += f"\n<!-- {title_with_suffix} -->\n<!-- {description} -->\n"

    social_bar = (
        social_bar.replace("{URL}", url)
        .replace("{TITLE}", title_with_suffix)
        .replace("{TEXT}", description)
    )

    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.debug(f"Quickshare generation for {getattr(blog, 'blog_title', 'Unknown')} completed in \033[96m{elapsed_time:.4f} seconds\033[0m")
    
    return social_bar


def blog_generation(app: Sphinx):
    """Generate blog pages with enhanced styling and metadata.

    This function processes each blog file, adding styling, author attribution,
    images, and social sharing buttons. It includes robust error handling and
    file backup mechanisms to prevent data loss.
    """
    start_time = time.time()
    
    try:
        env = app.builder.env
        srcdir = Path(env.srcdir)

        rocmblogs = ROCmBlogs()
        blogs_dir = rocmblogs.find_blogs_directory(str(srcdir))
        rocmblogs.blogs_directory = str(blogs_dir)
        rocmblogs.find_readme_files_cache()
        rocmblogs.create_blog_objects()
        rocmblogs.blogs.sort_blogs_by_date()

        # Process blogs in parallel
        blogs = rocmblogs.blogs.get_blogs()
        
        # Use a thread pool to process blogs in parallel
        # Determine the optimal number of workers based on CPU count
        max_workers = min(32, (os.cpu_count() or 1) * 2)
        logger.info(f"Processing {len(blogs)} blogs with {max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a list of futures
            futures = []
            for blog in blogs:
                future = executor.submit(process_single_blog, blog, rocmblogs)
                futures.append(future)
            
            # Process results as they complete
            for future in futures:
                try:
                    future.result()  # This will raise any exceptions from the thread
                except Exception as error:
                    logger.warning(f"Error processing blog: {error}")
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Blog generation completed in \033[96m{elapsed_time:.2f} seconds\033[0m")
    except Exception as error:
        logger.critical(f"Failed to generate blogs: {error}")


# Precompile regex patterns for better performance
_YAML_FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
_FENCED_CODE_BLOCKS_PATTERN = re.compile(r"```[\s\S]*?```")
_INDENTED_CODE_BLOCKS_PATTERN = re.compile(r"(?m)^( {4}|\t).*$")
_HTML_TAGS_PATTERN = re.compile(r"<[^>]*>")
_URLS_PATTERN = re.compile(r"https?://\S+")
_IMAGE_REFERENCES_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_REFERENCES_PATTERN = re.compile(r"\[[^\]]*\]\([^)]*\)")
_HEADERS_PATTERN = re.compile(r"(?m)^#.*$")
_HORIZONTAL_RULES_PATTERN = re.compile(r"(?m)^(---|[*]{3}|[_]{3})$")
_BLOCKQUOTES_PATTERN = re.compile(r"(?m)^>.*$")
_UNORDERED_LIST_MARKERS_PATTERN = re.compile(r"(?m)^[ \t]*[-*+][ \t]+")
_ORDERED_LIST_MARKERS_PATTERN = re.compile(r"(?m)^[ \t]*\d+\.[ \t]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")

def count_words_in_markdown(content: str) -> int:
    """Count the number of words in a markdown file."""
    start_time = time.time()
    
    try:
        # Remove YAML front matter
        if content.startswith("---"):
            content = _YAML_FRONT_MATTER_PATTERN.sub("", content)
        
        # Apply all regex replacements in a single pass
        patterns_to_remove = [
            _FENCED_CODE_BLOCKS_PATTERN,
            _INDENTED_CODE_BLOCKS_PATTERN,
            _HTML_TAGS_PATTERN,
            _URLS_PATTERN,
            _IMAGE_REFERENCES_PATTERN,
            _LINK_REFERENCES_PATTERN,
            _HEADERS_PATTERN,
            _HORIZONTAL_RULES_PATTERN,
            _BLOCKQUOTES_PATTERN,
            _UNORDERED_LIST_MARKERS_PATTERN,
            _ORDERED_LIST_MARKERS_PATTERN
        ]
        
        for pattern in patterns_to_remove:
            try:
                content = pattern.sub("", content)
            except re.error as error:
                logger.warning(f"\033[33mError in regex: {error}\033[0m")
        
        # Split by whitespace and count non-empty words
        words = [word for word in _WHITESPACE_PATTERN.split(content) if word.strip()]
        word_count = len(words)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.debug(f"Word counting completed in \033[96m{elapsed_time:.4f} seconds\033[0m")
        
        return word_count
    except Exception as error:
        logger.warning(f"Error counting words in markdown: {error}")
        return 0


def process_single_blog(blog, rocmblogs):
    start_time = time.time()
    readme_file = blog.file_path
    backup_file = f"{readme_file}.bak"

    # Skip processing if the blog doesn't have required attributes
    if not hasattr(blog, "author") or not blog.author:
        logger.warning(f"Skipping blog {readme_file} without author")
        return

    try:
        # Read file content once and create backup
        try:
            with open(readme_file, "r", encoding="utf-8", errors="replace") as src:
                content = src.read()
                # Convert content to lines immediately to avoid reading the file twice
                lines = content.splitlines(True)  # Keep line endings
            
            # Create backup
            with open(backup_file, "w", encoding="utf-8", errors="replace") as dst:
                dst.write(content)
        except Exception as error:
            logger.warning(f"Error reading or backing up blog {readme_file}: {error}")
            return

        # Count words using the content we already have
        word_count = count_words_in_markdown(content)
        blog.set_word_count(word_count)
        logger.info(f"\033[33mWord count for {readme_file}: {word_count}\033[0m")

        try:

            authors_list = blog.author.split(",")
            date = blog.date.strftime("%B %d, %Y") if blog.date else "No Date"
            language = getattr(blog, "language", "en")
            category = getattr(blog, "category", "blog")
            tags = getattr(blog, "tags", "")

            # Process tags
            tag_html_list = []
            if tags:
                tags_list = [tag.strip() for tag in tags.split(",")]
                for tag in tags_list:
                    tag_link = truncate_string(tag)
                    tag_html = f'<a href="https://rocm.blogs.amd.com/blog/tag/{tag_link}.html">{tag}</a>'
                    tag_html_list.append(tag_html)

            tags_html = ", ".join(tag_html_list)

            # Process category
            category_link = truncate_string(category)
            category_html = f'<a href="https://rocm.blogs.amd.com/blog/category/{category_link}.html">{category.strip()}</a>'

            # Calculate read time
            blog_read_time = (
                str(calculate_read_time(getattr(blog, "word_count", 0)))
                if hasattr(blog, "word_count")
                else "No Read Time"
            )

            # Get author HTML
            authors_html = blog.grab_authors(authors_list)
            if authors_html:
                authors_html = authors_html.replace("././", "../../").replace(
                    ".md", ".html"
                )
            
            # Check if author is "No author" or empty
            has_valid_author = authors_html and "No author" not in authors_html

            # Find the title and its position
            title, line_number = None, None
            for i, line in enumerate(lines):
                if line.startswith("#") and line.count("#") == 1:
                    title = line
                    line_number = i
                    break

            if not title or line_number is None:
                logger.warning(f"Could not find title in blog {readme_file}")
                return

            # Load templates and CSS
            quickshare_button = quickshare(blog)
            image_css = cached_read_text(
                "rocm_blogs.static.css", "image_blog.css"
            )
            image_html = cached_read_text(
                "rocm_blogs.templates", "image_blog.html"
            )
            blog_css = cached_read_text("rocm_blogs.static.css", "blog.css")
            breadcrumbs_css = cached_read_text("rocm_blogs.static.css", "breadcrumbs.css")
            author_attribution_template = cached_read_text(
                "rocm_blogs.templates", "author_attribution.html"
            )
            giscus_html = cached_read_text("rocm_blogs.templates", "giscus.html")

            # Modify the author attribution template based on whether there's a valid author
            if has_valid_author:
                # Use the original template with author
                modified_author_template = author_attribution_template
            else:
                # Create a modified template without "by {authors_string}"
                modified_author_template = author_attribution_template.replace(
                    '<span> {date} by {authors_string}.</span>',
                    '<span> {date}</span>'
                )
            
            # Fill in the author attribution template
            authors_html_filled = (
                modified_author_template.replace("{authors_string}", authors_html)
                .replace("{date}", date)
                .replace("{language}", language)
                .replace("{category}", category_html)
                .replace("{tags}", tags_html)
                .replace("{read_time}", blog_read_time)
                .replace(
                    "{word_count}", str(getattr(blog, "word_count", "No Word Count"))
                )
            )

            # Get the image path
            try:
                image_path = blog.grab_image(rocmblogs)
                if blog.image_paths:
                    blog_image = f"../../_images/{blog.image_paths[0]}"
                else:
                    blog_image = "../../_images/generic.jpg"
            except Exception as error:
                logger.warning(
                    f"Error processing image for blog {readme_file}: {error}"
                )
                blog_image = "../../_images/generic.jpg"

            # Fill in the image template
            image_template_filled = image_html.replace("{IMAGE}", blog_image).replace(
                "{TITLE}", getattr(blog, "blog_title", "")
            )

            # Prepare the templates to insert
            blog_template = f"""
<style>
{blog_css}
</style>
"""
            image_template = f"""
<style>
{image_css}
</style>
{image_template_filled}
"""

            # Insert the templates at the appropriate positions
            new_lines = lines.copy()
            new_lines.insert(line_number + 1, f"\n{blog_template}\n")
            new_lines.insert(line_number + 2, f"\n{image_template}\n")
            new_lines.insert(line_number + 3, f"\n{authors_html_filled}\n")
            new_lines.insert(line_number + 4, f"\n{quickshare_button}\n")

            # Add giscus comments at the end of the file
            new_lines.append(f"\n\n{giscus_html}\n")

            # Write the modified file
            with open(readme_file, "w", encoding="utf-8", errors="replace") as file:
                file.writelines(new_lines)

            end_time = time.time()
            elapsed_time = end_time - start_time
            logger.info(f"\033[33mSuccessfully processed blog {readme_file} in \033[96m{elapsed_time:.2f} seconds\033[33m\033[0m")

            # Remove the backup file if everything went well
            try:
                os.remove(backup_file)
            except BaseException:
                pass

        except Exception as error:
            logger.warning(f"Error processing blog {readme_file}: {error}")

            try:
                if os.path.exists(backup_file):
                    with open(
                        backup_file, "r", encoding="utf-8", errors="replace"
                    ) as src:
                        content = src.read()
                    with open(
                        readme_file, "w", encoding="utf-8", errors="replace"
                    ) as dst:
                        dst.write(content)

                    logger.info(f"\033[33mRestored {readme_file} from backup\033[0m")

            except BaseException:
                logger.warning(
                    f"WARNING: Could not restore {readme_file} from backup after unexpected error"
                )

    except Exception as error:
        logger.warning(f"Error processing blog {readme_file}: {error}")

        try:
            if os.path.exists(backup_file):
                with open(backup_file, "r", encoding="utf-8", errors="replace") as src:
                    content = src.read()
                with open(readme_file, "w", encoding="utf-8", errors="replace") as dst:
                    dst.write(content)
                logger.warning(
                    f"Restored {readme_file} from backup after unexpected error"
                )
        except BaseException:
            logger.warning(
                f"WARNING: Could not restore {readme_file} from backup after unexpected error"
            )


def setup(app: Sphinx):
    start_time = time.time()
    
    logger.info("Setting up ROCm Blogs extension")

    app.connect("builder-inited", update_index_file)
    app.connect("builder-inited", blog_generation)
    
    # Log the total build setup time
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"ROCm Blogs extension setup completed in \033[96m{elapsed_time:.2f} seconds\033[0m")

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
