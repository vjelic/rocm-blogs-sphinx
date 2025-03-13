import importlib.resources as pkg_resources
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sphinx.application import Sphinx
from sphinx.util import logging as sphinx_logging

from ._rocmblogs import ROCmBlogs
from ._version import __version__
from .grid import generate_grid
from .metadata import metadata_generator

def log_time(func):
    """Decorator to log execution time of functions"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"{func.__name__} completed in \033[96m{elapsed_time:.4f} seconds\033[0m")
        return result
    return wrapper

__all__ = ["Blog", "BlogHolder", "ROCmBlogs", "grid_generation", "metadata_generator"]

logger = sphinx_logging.getLogger(__name__)

def import_file(package, resource):
    """Read text from a package resource directly without caching."""
    return pkg_resources.read_text(package, resource)


def calculate_read_time(words: int) -> int:

    start_time = time.time()

    result = round(words / 245)

    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.debug(
        f"Read time calculation completed in \033[96m{elapsed_time:.6f} milliseconds\033[0m"
    )

    return result


def truncate_string(input_string: str) -> str:

    start_time = time.time()

    cleaned_string = re.sub(r"[!@#$%^&*?/|]", "", input_string)
    transformed_string = re.sub(r"\s+", "-", cleaned_string)
    result = transformed_string.lower()

    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.debug(
        f"String truncation completed in \033[96m{elapsed_time:.6f} milliseconds\033[0m"
    )

    return result


def update_index_file(app: Sphinx) -> None:

    phase_start_time = time.time()

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

# ROCm Blogs

<style>
{CSS}
</style>
{HTML}
"""

        # load index.html template
        template_html = import_file("rocm_blogs.templates", "index.html")

        # load index.css template
        css_content = import_file("rocm_blogs.static.css", "index.css")

        index_template = index_template.format(
            CSS=css_content, 
            HTML=template_html
        )

        index_template = index_template[1:]

        rocmblogs = ROCmBlogs()

        # Assume the blogs directory is the sibling of srcdir.
        blogs_dir = rocmblogs.find_blogs_directory(app.srcdir)
        rocmblogs.blogs_directory = str(blogs_dir)
        rocmblogs.find_readme_files()
        rocmblogs.create_blog_objects()
        rocmblogs.blogs.sort_blogs_by_date()
        rocmblogs.blogs.sort_blogs_by_category(rocmblogs.categories)

        all_blogs = rocmblogs.blogs.get_blogs()

        used = []
        grid_items = []
        eco_grid_items = []
        application_grid_items = []
        software_grid_items = []

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
        
        logger.info("Generating grid items in parallel")

        grid_items = generate_grid_items(all_blogs, 4, used)

        eco_blogs = rocmblogs.blogs.blogs_categories.get("Ecosystems and Partners", [])
        eco_grid_items = generate_grid_items(eco_blogs, 4, used)

        app_blogs = rocmblogs.blogs.blogs_categories.get("Applications & models", [])
        application_grid_items = generate_grid_items(app_blogs, 4, used)

        sw_blogs = rocmblogs.blogs.blogs_categories.get(
            "Software tools & optimizations", []
        )
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
        elapsed_time = end_time - phase_start_time
        # Store the time in the build phases dictionary
        _BUILD_PHASES['update_index'] = elapsed_time
        logger.info(
            f"Successfully updated {output_path} with new grid items in \033[96m{elapsed_time:.2f} milliseconds\033[0m."
        )
    except Exception as error:
        logger.critical(f"Failed to update index file: {error}")
        # Even on error, record the time spent
        _BUILD_PHASES['update_index'] = time.time() - phase_start_time


def quickshare(blog):

    start_time = time.time()

    css = import_file("rocm_blogs.static.css", "social-bar.css")
    html = import_file("rocm_blogs.templates", "social-bar.html")

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

    if "test" in str(blog.file_path).lower():
        social_bar += f"\n<!-- {title_with_suffix} -->\n<!-- {description} -->\n"

    social_bar = (
        social_bar.replace("{URL}", url)
        .replace("{TITLE}", title_with_suffix)
        .replace("{TEXT}", description)
    )

    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.debug(
        f"Quickshare generation for {getattr(blog, 'blog_title', 'Unknown')} completed in \033[96m{elapsed_time:.4f} milliseconds\033[0m"
    )

    return social_bar


def blog_generation(app: Sphinx):
    phase_start_time = time.time()

    try:
        env = app.builder.env
        srcdir = Path(env.srcdir)

        rocmblogs = ROCmBlogs()
        blogs_dir = rocmblogs.find_blogs_directory(str(srcdir))
        rocmblogs.blogs_directory = str(blogs_dir)
        rocmblogs.find_readme_files()
        rocmblogs.create_blog_objects()
        rocmblogs.blogs.sort_blogs_by_date()

        blogs = rocmblogs.blogs.get_blogs()

        max_workers = min(32, (os.cpu_count() or 1) * 2)
        logger.info(f"Processing {len(blogs)} blogs with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            
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
        elapsed_time = end_time - phase_start_time
        # Store the time in the build phases dictionary
        _BUILD_PHASES['blog_generation'] = elapsed_time
        logger.info(
            f"Blog generation completed in \033[96m{elapsed_time:.2f} seconds\033[0m"
        )
    except Exception as error:
        logger.critical(f"Failed to generate blogs: {error}")
        # Even on error, record the time spent
        _BUILD_PHASES['blog_generation'] = time.time() - phase_start_time


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

    start_time = time.time()

    try:
        if content.startswith("---"):
            content = _YAML_FRONT_MATTER_PATTERN.sub("", content)

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
            _ORDERED_LIST_MARKERS_PATTERN,
        ]

        for pattern in patterns_to_remove:
            try:
                content = pattern.sub("", content)
            except re.error as error:
                logger.warning(f"\033[33mError in regex: {error}\033[0m")

        words = [word for word in _WHITESPACE_PATTERN.split(content) if word.strip()]
        word_count = len(words)

        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.debug(
            f"Word counting completed in \033[96m{elapsed_time:.4f} milliseconds\033[0m"
        )

        return word_count
    except Exception as error:
        logger.warning(f"Error counting words in markdown: {error}")
        return 0


def optimize_image(image_path):

    try:
        from PIL import Image
        import os
        
        # Get file extension
        _, file_ext = os.path.splitext(image_path)
        file_ext = file_ext.lower()
        
        # Record original file size
        original_size = os.path.getsize(image_path)
        
        with Image.open(image_path) as img:
            # Get original dimensions and format
            original_width, original_height = img.size
            original_format = img.format
            
            # Strip EXIF and other metadata to reduce file size
            img_data = list(img.getdata())
            img_without_exif = Image.new(img.mode, img.size)
            img_without_exif.putdata(img_data)
            
            # Regular content images
            max_width, max_height = (1280, 720)
            
            # Calculate scaling factor to maintain aspect ratio
            scaling_factor = min(
                max_width / original_width, 
                max_height / original_height
            )
            
            # Only resize if the image is larger than our max dimensions
            if scaling_factor < 1:
                new_width = int(original_width * scaling_factor)
                new_height = int(original_height * scaling_factor)
                
                # Resize the image using high-quality Lanczos resampling
                img_without_exif = img_without_exif.resize((new_width, new_height), resample=Image.LANCZOS)
                logger.info(f"Resized image: {original_width}x{original_height} → {new_width}x{new_height}")
            
            # Optimize based on image format
            if file_ext in ['.jpg', '.jpeg']:
                img_without_exif.save(
                    image_path, 
                    format="JPEG", 
                    optimize=True, 
                    quality=85
                )
            elif file_ext == '.png':
                img_without_exif.save(
                    image_path, 
                    format="PNG", 
                    optimize=True, 
                    compress_level=9
                )
            else:
                # For other formats, just save with default settings
                img_without_exif.save(image_path)
            
            # Get new file size for logging
            new_size = os.path.getsize(image_path)
            size_reduction = (1 - new_size / original_size) * 100 if original_size > 0 else 0
            
            logger.info(
                f"Optimized {os.path.basename(image_path)}: "
                f"{original_format} {original_size/1024:.1f}KB → {new_size/1024:.1f}KB "
                f"({size_reduction:.1f}% reduction)"
            )
            
            # Create WebP version as well (but don't replace the original in HTML)
            try:
                webp_path = os.path.splitext(image_path)[0] + '.webp'
                
                # Convert to RGB mode if needed (WebP doesn't support CMYK or other modes)
                if img_without_exif.mode not in ('RGB', 'RGBA'):
                    webp_img = img_without_exif.convert('RGB')
                else:
                    webp_img = img_without_exif
                
                # Save as WebP with high quality
                webp_img.save(
                    webp_path,
                    format="WEBP",
                    quality=85,  # High quality WebP
                    method=6,    # Highest compression method (slower but better)
                    lossless=False
                )
                
                # Get WebP file size for logging
                webp_size = os.path.getsize(webp_path)
                webp_reduction = (1 - webp_size / original_size) * 100 if original_size > 0 else 0
                
                logger.info(
                    f"Created WebP version: {os.path.basename(webp_path)}: "
                    f"{webp_size/1024:.1f}KB ({webp_reduction:.1f}% reduction from original)"
                )
            except Exception as webp_error:
                logger.warning(f"Error creating WebP version of {os.path.basename(image_path)}: {webp_error}")
            
            return True
    except Exception as error:
        logger.warning(f"Error optimizing image {os.path.basename(image_path)}: {error}")
        return False


def process_single_blog(blog, rocmblogs):
    """Process a single blog file without creating backups."""
    start_time = time.time()
    readme_file = blog.file_path
    blog_dir = os.path.dirname(readme_file)

    if not hasattr(blog, "author") or not blog.author:
        logger.warning(f"Skipping blog {readme_file} without author")
        return

    try:

        with open(readme_file, "r", encoding="utf-8", errors="replace") as src:
            content = src.read()

            lines = content.splitlines(True)

        if hasattr(blog, "thumbnail") and blog.thumbnail:
            blog.grab_image(rocmblogs)
            logger.info(
                f"Found thumbnail image: {blog.image_paths[0] if blog.image_paths else 'None'}"
            )

            thumbnails = [os.path.basename(path) for path in blog.image_paths] if blog.image_paths else []

            if thumbnails:
                for image_name in thumbnails:
                    possible_image_paths = []

                    blog_dir_img = os.path.join(blog_dir, image_name)
                    blog_dir_images_img = os.path.join(blog_dir, "images", image_name)

                    blogs_dir = rocmblogs.blogs_directory
                    global_img = os.path.join(blogs_dir, "images", image_name)
                    
                    possible_image_paths.extend([blog_dir_img, blog_dir_images_img, global_img])

                    for img_path in possible_image_paths:
                        if os.path.exists(img_path) and os.path.isfile(img_path):
                            logger.info(f"Optimizing image from image_paths: {img_path}")
                            optimize_image(img_path, thumbnails)
                            break

            blog_images_dir = os.path.join(blog_dir, "images")
            if os.path.exists(blog_images_dir) and os.path.isdir(blog_images_dir):
                logger.info(f"Checking for images in blog images directory: {blog_images_dir}")
                for filename in os.listdir(blog_images_dir):
                    img_path = os.path.join(blog_images_dir, filename)
                    if os.path.isfile(img_path):
                        _, ext = os.path.splitext(filename)
                        if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif']:
                            logger.info(f"Optimizing image from blog/images directory: {img_path}")
                            optimize_image(img_path, thumbnails)

        word_count = count_words_in_markdown(content)
        blog.set_word_count(word_count)
        logger.info(f"\033[33mWord count for {readme_file}: {word_count}\033[0m")

        authors_list = blog.author.split(",")
        date = blog.date.strftime("%B %d, %Y") if blog.date else "No Date"
        language = getattr(blog, "language", "en")
        category = getattr(blog, "category", "blog")
        tags = getattr(blog, "tags", "")

        tag_html_list = []
        if tags:
            tags_list = [tag.strip() for tag in tags.split(",")]
            for tag in tags_list:
                tag_link = truncate_string(tag)
                tag_html = f'<a href="https://rocm.blogs.amd.com/blog/tag/{tag_link}.html">{tag}</a>'
                tag_html_list.append(tag_html)

        tags_html = ", ".join(tag_html_list)

        category_link = truncate_string(category)
        category_html = f'<a href="https://rocm.blogs.amd.com/blog/category/{category_link}.html">{category.strip()}</a>'

        blog_read_time = (
            str(calculate_read_time(getattr(blog, "word_count", 0)))
            if hasattr(blog, "word_count")
            else "No Read Time"
        )

        authors_html = blog.grab_authors(authors_list)
        if authors_html:
            authors_html = authors_html.replace("././", "../../").replace(
                ".md", ".html"
            )

        has_valid_author = authors_html and "No author" not in authors_html

        title, line_number = None, None
        for i, line in enumerate(lines):
            if line.startswith("#") and line.count("#") == 1:
                title = line
                line_number = i
                break

        if not title or line_number is None:
            logger.warning(f"Could not find title in blog {readme_file}")
            return

        quickshare_button = quickshare(blog)
        image_css = import_file("rocm_blogs.static.css", "image_blog.css")
        image_html = import_file("rocm_blogs.templates", "image_blog.html")
        blog_css = import_file("rocm_blogs.static.css", "blog.css")
        author_attribution_template = import_file(
            "rocm_blogs.templates", "author_attribution.html"
        )
        giscus_html = import_file("rocm_blogs.templates", "giscus.html")

        if has_valid_author:
            modified_author_template = author_attribution_template
        else:
            modified_author_template = author_attribution_template.replace(
                "<span> {date} by {authors_string}.</span>", "<span> {date}</span>"
            )

        authors_html_filled = (
            modified_author_template.replace("{authors_string}", authors_html)
            .replace("{date}", date)
            .replace("{language}", language)
            .replace("{category}", category_html)
            .replace("{tags}", tags_html)
            .replace("{read_time}", blog_read_time)
            .replace("{word_count}", str(getattr(blog, "word_count", "No Word Count")))
        )

        blog_path = Path(blog.file_path)
        blogs_dir = Path(rocmblogs.blogs_directory)
        
        try:
            rel_path = blog_path.relative_to(blogs_dir)
            depth = len(rel_path.parts) - 1
            logger.info(f"Blog depth: {depth} for {blog.file_path}")
            
            parent_dirs = "../" * (depth + 1)

            logger.info(f"Blog path: {blog_path}")
            logger.info(f"Blogs dir: {blogs_dir}")
            logger.info(f"Relative path: {rel_path}")
            logger.info(f"Depth: {depth}")
            logger.info(f"Parent dirs: {parent_dirs}")

            if depth == 1 and parent_dirs == "../../":
                pass
            elif depth == 2 and parent_dirs == "../../../":
                pass
            elif depth == 3 and parent_dirs == "../../../../":
                parent_dirs = "../../../"
                logger.info(f"Corrected parent dirs for depth 3: {parent_dirs}")
            
            if blog.image_paths:
                blog_image = f"{parent_dirs}_images/{blog.image_paths[0]}"
            else:
                blog_image = f"{parent_dirs}_images/generic.jpg"
                
            logger.info(f"Using image path: {blog_image}")
        except ValueError:
            # If the blog is not relative to blogs_dir, fall back to default
            logger.warning(f"Could not determine relative path for {blog.file_path}, using default image path")
            if blog.image_paths:
                blog_image = f"../../_images/{blog.image_paths[0]}"
            else:
                blog_image = "../../_images/generic.jpg"

        image_template_filled = (
            image_html.replace("{IMAGE}", blog_image)
            .replace("{TITLE}", getattr(blog, "blog_title", ""))
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
        logger.info(
            f"\033[33mSuccessfully processed blog {readme_file} in \033[96m{elapsed_time:.2f} milliseconds\033[33m\033[0m"
        )

    except Exception as error:
        logger.warning(f"Error processing blog {readme_file}: {error}")

_BUILD_START_TIME = time.time()

_BUILD_PHASES = {
    'setup': 0,
    'update_index': 0,
    'blog_generation': 0,
    'other': 0
}

def log_total_build_time(app, exception):
    end_time = time.time()
    total_elapsed_time = end_time - _BUILD_START_TIME
    
    accounted_time = sum(_BUILD_PHASES.values())
    _BUILD_PHASES['other'] = total_elapsed_time - accounted_time
    
    logger.info("=" * 80)
    logger.info(f"BUILD PROCESS TIMING SUMMARY:")
    logger.info("-" * 80)
    logger.info(f"Setup phase:          \033[96m{_BUILD_PHASES['setup']:.2f} seconds\033[0m ({_BUILD_PHASES['setup']/total_elapsed_time*100:.1f}%)")
    logger.info(f"Index update phase:   \033[96m{_BUILD_PHASES['update_index']:.2f} seconds\033[0m ({_BUILD_PHASES['update_index']/total_elapsed_time*100:.1f}%)")
    logger.info(f"Blog generation phase: \033[96m{_BUILD_PHASES['blog_generation']:.2f} seconds\033[0m ({_BUILD_PHASES['blog_generation']/total_elapsed_time*100:.1f}%)")
    logger.info(f"Other processing:     \033[96m{_BUILD_PHASES['other']:.2f} seconds\033[0m ({_BUILD_PHASES['other']/total_elapsed_time*100:.1f}%)")
    logger.info("-" * 80)
    logger.info(f"Total build process completed in \033[92m{total_elapsed_time:.2f} seconds\033[0m")
    logger.info("=" * 80)

def update_posts_file(app: Sphinx) -> None:
    
    phase_start_time = time.time()

    try:
        posts_template = """---
title: All Posts{page_title_suffix}
myst:
html_meta:
"description lang=en": "All AMD ROCm™ software blogs{page_description_suffix}"
"keywords": "AMD GPU, MI300, MI250, ROCm, blog, posts, articles, page {current_page}"
"property=og:locale": "en_US"
---

# Recent Posts{page_title_suffix}

<style>
{CSS}
{PAGINATION_CSS}
</style>
{HTML}

{pagination_controls}
"""

        # Load posts.html template
        template_html = import_file("rocm_blogs.templates", "posts.html")
        
        # Load pagination template
        pagination_template = import_file("rocm_blogs.templates", "pagination.html")

        # Load CSS templates for styling
        css_content = import_file("rocm_blogs.static.css", "index.css")
        pagination_css = import_file("rocm_blogs.static.css", "pagination.css")

        # Process blog data using ROCmBlogs
        rocmblogs = ROCmBlogs()

        # Assume the blogs directory is the sibling of srcdir
        blogs_dir = rocmblogs.find_blogs_directory(app.srcdir)
        rocmblogs.blogs_directory = str(blogs_dir)
        rocmblogs.find_readme_files()
        rocmblogs.create_blog_objects()
        rocmblogs.blogs.sort_blogs_by_date()

        # Get all blogs
        all_blogs = rocmblogs.blogs.get_blogs()
        
        blogs_per_page = 12
        
        # Calculate total number of pages
        total_pages = max(1, (len(all_blogs) + blogs_per_page - 1) // blogs_per_page)
        
        logger.info(f"Generating {total_pages} paginated posts pages with {blogs_per_page} blogs per page")
        
        def optimize_grid_item(grid_item):
            """Add lazy loading to images in a grid item."""
            # Replace src with data-src for lazy loading
            if 'img' in grid_item and 'src="' in grid_item:
                # Add a tiny placeholder image (1x1 transparent pixel)
                grid_item = grid_item.replace('<img ', '<img loading="lazy" ')
                grid_item = grid_item.replace('src="', 'data-src="')
                grid_item = grid_item.replace('<img loading="lazy" data-src="', 
                                             '<img loading="lazy" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" data-src="')
            return grid_item
        
        all_grid_items = []
        with ThreadPoolExecutor() as executor:
            futures = {}
            for blog in all_blogs:
                futures[executor.submit(generate_grid, rocmblogs, blog)] = blog
                
            for future in futures:
                # Optimize the grid item for lazy loading
                grid_item = optimize_grid_item(future.result())
                all_grid_items.append(grid_item)
        
        current_datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        for page_num in range(1, total_pages + 1):
            # Calculate slice indices for this page
            start_idx = (page_num - 1) * blogs_per_page
            end_idx = min(start_idx + blogs_per_page, len(all_grid_items))
            
            # Get grid items for this page
            page_grid_items = all_grid_items[start_idx:end_idx]
            grid_content = "\n".join(page_grid_items)
            
            prev_button = ""
            if page_num > 1:
                prev_page = page_num - 1
                prev_file = f"posts-page{prev_page}.html" if prev_page > 1 else "posts.html"
                prev_button = f'<a href="{prev_file}" class="pagination-button previous"> Prev</a>'
            else:
                prev_button = '<span class="pagination-button disabled"> Prev</span>'
                
            next_button = ""
            if page_num < total_pages:
                next_page = page_num + 1
                next_file = f"posts-page{next_page}.html"
                next_button = f'<a href="{next_file}" class="pagination-button next">Next </a>'
            else:
                next_button = '<span class="pagination-button disabled">Next </span>'
            
            # Fill in pagination template
            pagination_controls = pagination_template.replace("{prev_button}", prev_button)
            pagination_controls = pagination_controls.replace("{current_page}", str(page_num))
            pagination_controls = pagination_controls.replace("{total_pages}", str(total_pages))
            pagination_controls = pagination_controls.replace("{next_button}", next_button)
            
            page_title_suffix = f" - Page {page_num}" if page_num > 1 else ""
            page_description_suffix = f" (Page {page_num} of {total_pages})" if page_num > 1 else ""
            
            updated_html = posts_template.format(
                CSS=css_content,
                PAGINATION_CSS=pagination_css,
                HTML=template_html,
                pagination_controls=pagination_controls,
                page_title_suffix=page_title_suffix,
                page_description_suffix=page_description_suffix,
                current_page=page_num
            )
            
            # Replace grid_items placeholder in the HTML
            updated_html = updated_html.replace("{grid_items}", grid_content)
            
            updated_html = updated_html.replace("{datetime}", current_datetime)
            
            if page_num == 1:
                output_filename = "posts.md"
            else:
                output_filename = f"posts-page{page_num}.md"
            
            # Write the updated HTML to blogs/posts.md or blogs/posts-page{n}.md
            output_path = Path(blogs_dir) / output_filename
            with output_path.open("w", encoding="utf-8") as f:
                f.write(updated_html)
                
            logger.info(
                f"Created {output_path} with {len(page_grid_items)} grid items (page {page_num} of {total_pages})"
            )
            
        end_time = time.time()
        elapsed_time = end_time - phase_start_time
        # Store the time in the build phases dictionary
        _BUILD_PHASES['update_posts'] = elapsed_time
        
        logger.info(
            f"Successfully created {total_pages} paginated posts pages in \033[96m{elapsed_time:.2f} seconds\033[0m."
        )
    except Exception as error:
        logger.critical(f"Failed to create posts files: {error}")
        # Even on error, record the time spent
        _BUILD_PHASES['update_posts'] = time.time() - phase_start_time


def run_metadata_generator(app: Sphinx) -> None:
    phase_start_time = time.time()
    
    try:
        logger.info("Running metadata generator...")
        
        rocmblogs = ROCmBlogs()
        
        blogs_dir = rocmblogs.find_blogs_directory(app.srcdir)
        rocmblogs.blogs_directory = str(blogs_dir)
        
        rocmblogs.find_readme_files()
        
        metadata_generator(rocmblogs)
        
        end_time = time.time()
        elapsed_time = end_time - phase_start_time
        # Store the time in the build phases dictionary
        _BUILD_PHASES['metadata_generation'] = elapsed_time
        logger.info(
            f"Metadata generation completed in \033[96m{elapsed_time:.2f} seconds\033[0m"
        )
    except Exception as error:
        logger.critical(f"Failed to generate metadata: {error}")
        # Even on error, record the time spent
        _BUILD_PHASES['metadata_generation'] = time.time() - phase_start_time


def update_category_pages(app: Sphinx) -> None:
    
    phase_start_time = time.time()

    try:
        categories = [
            {
                "name": "Applications & models",
                "template": "applications-models.html",
                "output_base": "applications-models",
                "category_key": "Applications & models",
                "title": "Applications & Models",
                "description": "AMD ROCm™ software blogs about applications and models",
                "keywords": "applications, models, AI, machine learning"
            },
            {
                "name": "Software tools & optimizations",
                "template": "software-tools.html",
                "output_base": "software-tools",
                "category_key": "Software tools & optimizations",
                "title": "Software Tools and Optimizations",
                "description": "AMD ROCm™ software blogs about tools and optimizations",
                "keywords": "software, tools, optimizations, performance"
            },
            {
                "name": "Ecosystems and Partners",
                "template": "ecosystem-partners.html",
                "output_base": "ecosystem-partners",
                "category_key": "Ecosystems and Partners",
                "title": "Ecosystem and Partners",
                "description": "AMD ROCm™ software blogs about ecosystem and partners",
                "keywords": "ecosystem, partners, integrations, collaboration"
            }
        ]
        
        pagination_template = import_file("rocm_blogs.templates", "pagination.html")

        css_content = import_file("rocm_blogs.static.css", "index.css")
        pagination_css = import_file("rocm_blogs.static.css", "pagination.css")
        
        blogs_per_page = 12
        
        # Process blog data using ROCmBlogs
        rocmblogs = ROCmBlogs()

        # Assume the blogs directory is the sibling of srcdir
        blogs_dir = rocmblogs.find_blogs_directory(app.srcdir)
        rocmblogs.blogs_directory = str(blogs_dir)
        rocmblogs.find_readme_files()
        rocmblogs.create_blog_objects()
        rocmblogs.blogs.sort_blogs_by_date()
        rocmblogs.blogs.sort_blogs_by_category(rocmblogs.categories)
        
        # Current datetime for template
        current_datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        def optimize_grid_item(grid_item):
            """Add lazy loading to images in a grid item."""
            # Replace src with data-src for lazy loading
            if 'img' in grid_item and 'src="' in grid_item:
                # Add a tiny placeholder image (1x1 transparent pixel)
                grid_item = grid_item.replace('<img ', '<img loading="lazy" ')
                grid_item = grid_item.replace('src="', 'data-src="')
                grid_item = grid_item.replace('<img loading="lazy" data-src="', 
                                             '<img loading="lazy" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" data-src="')
            return grid_item
        
        for category_info in categories:
            category_name = category_info["name"]
            template_name = category_info["template"]
            output_base = category_info["output_base"]
            category_key = category_info["category_key"]
            title = category_info["title"]
            description = category_info["description"]
            keywords = category_info["keywords"]
            
            logger.info(f"Generating paginated pages for category: {category_name}")
            
            template_html = import_file("rocm_blogs.templates", template_name)
            
            category_blogs = rocmblogs.blogs.blogs_categories.get(category_key, [])
            
            total_pages = max(1, (len(category_blogs) + blogs_per_page - 1) // blogs_per_page)
            
            logger.info(f"Category {category_name} has {len(category_blogs)} blogs, creating {total_pages} pages")
            
            all_grid_items = []
            with ThreadPoolExecutor() as executor:
                futures = {}
                for blog in category_blogs:
                    futures[executor.submit(generate_grid, rocmblogs, blog)] = blog
                    
                for future in futures:
                    # Optimize the grid item for lazy loading
                    grid_item = optimize_grid_item(future.result())
                    all_grid_items.append(grid_item)
            
            category_template = """---
title: {title}{page_title_suffix}
myst:
html_meta:
"description lang=en": "{description}{page_description_suffix}"
"keywords": "AMD GPU, MI300, MI250, ROCm, blog, {keywords}, page {current_page}"
"property=og:locale": "en_US"
---

# {title}{page_title_suffix}

<style>
{CSS}
{PAGINATION_CSS}
</style>
{HTML}

{pagination_controls}
"""
            
            for page_num in range(1, total_pages + 1):
                start_idx = (page_num - 1) * blogs_per_page
                end_idx = min(start_idx + blogs_per_page, len(all_grid_items))
                
                page_grid_items = all_grid_items[start_idx:end_idx]
                grid_content = "\n".join(page_grid_items)
                
                prev_button = ""
                if page_num > 1:
                    prev_page = page_num - 1
                    prev_file = f"{output_base}-page{prev_page}.html" if prev_page > 1 else f"{output_base}.html"
                    prev_button = f'<a href="{prev_file}" class="pagination-button previous"> Prev</a>'
                else:
                    prev_button = '<span class="pagination-button disabled"> Prev</span>'
                    
                next_button = ""
                if page_num < total_pages:
                    next_page = page_num + 1
                    next_file = f"{output_base}-page{next_page}.html"
                    next_button = f'<a href="{next_file}" class="pagination-button next">Next </a>'
                else:
                    next_button = '<span class="pagination-button disabled">Next </span>'
                
                # Fill in pagination template
                pagination_controls = pagination_template.replace("{prev_button}", prev_button)
                pagination_controls = pagination_controls.replace("{current_page}", str(page_num))
                pagination_controls = pagination_controls.replace("{total_pages}", str(total_pages))
                pagination_controls = pagination_controls.replace("{next_button}", next_button)
                
                page_title_suffix = f" - Page {page_num}" if page_num > 1 else ""
                page_description_suffix = f" (Page {page_num} of {total_pages})" if page_num > 1 else ""
                
                updated_html = template_html.replace("{grid_items}", grid_content)
                updated_html = updated_html.replace("{datetime}", current_datetime)
                
                # Create the final markdown content
                final_content = category_template.format(
                    title=title,
                    description=description,
                    keywords=keywords,
                    CSS=css_content,
                    PAGINATION_CSS=pagination_css,
                    HTML=updated_html,
                    pagination_controls=pagination_controls,
                    page_title_suffix=page_title_suffix,
                    page_description_suffix=page_description_suffix,
                    current_page=page_num
                )
                
                if page_num == 1:
                    output_filename = f"{output_base}.md"
                else:
                    output_filename = f"{output_base}-page{page_num}.md"
                
                # Write the updated HTML to blogs/category_file.md
                output_path = Path(blogs_dir) / output_filename
                with output_path.open("w", encoding="utf-8") as f:
                    f.write(final_content)
                    
                logger.info(
                    f"Created {output_path} with {len(page_grid_items)} grid items (page {page_num} of {total_pages})"
                )
            
        end_time = time.time()
        elapsed_time = end_time - phase_start_time
        # Store the time in the build phases dictionary
        _BUILD_PHASES['update_category_pages'] = elapsed_time
        
        logger.info(
            f"Category pages generation completed in \033[96m{elapsed_time:.2f} seconds\033[0m."
        )
    except Exception as error:
        logger.critical(f"Failed to create category pages: {error}")
        # Even on error, record the time spent
        _BUILD_PHASES['update_category_pages'] = time.time() - phase_start_time


def setup(app: Sphinx) -> dict:
    setup_start_time = time.time()

    logger.info(f"Setting up ROCm Blogs extension, version: {__version__}")
    logger.info(f"Build process started at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(_BUILD_START_TIME))}")
    
    app.connect("builder-inited", run_metadata_generator)
    app.connect("builder-inited", update_index_file)
    app.connect("builder-inited", update_posts_file)
    app.connect("builder-inited", update_category_pages)
    app.connect("builder-inited", blog_generation)
    
    app.connect("build-finished", log_total_build_time)

    setup_end_time = time.time()
    setup_elapsed_time = setup_end_time - setup_start_time
    # Store the setup time in the build phases dictionary
    _BUILD_PHASES['setup'] = setup_elapsed_time
    logger.info(
        f"ROCm Blogs extension setup completed in \033[96m{setup_elapsed_time:.2f} seconds\033[0m"
    )

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
