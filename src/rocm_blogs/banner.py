"""
Banner slider generation for ROCm Blogs.
"""

import os
import re
import traceback

from PIL import Image
from sphinx.util import logging as sphinx_logging

from .logger.logger import *


def generate_banner_slide(blog, rocmblogs, index: int = 0, active: bool = False) -> str:
    """Generate a single banner slide for a blog in NVIDIA-inspired style."""

    log_message(
        "info",
        f"========== GENERATE_BANNER_SLIDE STARTED (index {index}) ==========",
        "slide_generation",
        "banner",
    )
    log_message(
        "info",
        f"Input parameters - Index: {index}, Active: {active}",
        "slide_generation",
        "banner",
    )
    log_message("info", f"Blog object type: {type(blog)}", "slide_generation", "banner")
    log_message(
        "info",
        f"Blog data - Title: '{getattr(blog, 'blog_title', 'None')}', Category: '{getattr(blog, 'category', 'None')}', Has thumbnail: {hasattr(blog, 'thumbnail')}",
        "slide_generation",
        "banner",
    )

    # Validate blog object
    if not blog:
        log_message(
            "error", "Blog object is None or empty!", "slide_generation", "banner"
        )
        return ""

    # Log all blog attributes for debugging
    blog_attrs = [attr for attr in dir(blog) if not attr.startswith("_")]
    log_message(
        "debug", f"Blog object attributes: {blog_attrs}", "slide_generation", "banner"
    )

    active_class = " active" if active else ""
    log_message(
        "info",
        f"Step 1: Setting active_class='{active_class}' for slide index {index}",
        "slide_generation",
        "banner",
    )

    # Initialize variables to prevent UnboundLocalError
    image = "./_images/generic.jpg"  # Default fallback
    href = "#"  # Default fallback
    description = "Explore the latest insights and developments in ROCm technology."  # Default fallback
    author = "."  # Default fallback

    slide_template = """
<div class="banner-slide{active_class}">
    <div class="banner-slide__text">
        <div class="banner-slide__category">
            <a href="{category_url}">
                {category}
            </a>
        </div>
        <div class="banner-slide__title">
            <a href="{href}">
                <h2 class="h--medium">
                    {title}
                </h2>
            </a>
        </div>
        <div class="banner-slide__description">
            <p>{description}</p>
        </div>
        <div class="banner-slide__author">
            <span>{author}</span>
        </div>
        <a href="{href}" class="cta--prim">
            <button id="banner-slide__title__link">
                See All
            </button>
        </a>
    </div>
    <div class="banner-slide__thumbnail">
        <a href="{href}">
            <div class="banner-slide__thumbnail-container">
                <img src="{image}" alt="{title}" title="{title}">
            </div>
        </a>
    </div>
</div>
"""

    log_message(
        "info",
        f"Step 2: Extracting title from blog object",
        "slide_generation",
        "banner",
    )
    title = blog.blog_title if hasattr(blog, "blog_title") else "No Title"
    log_message(
        "info",
        f"Banner slide title (original): '{title}'",
        "slide_generation",
        "banner",
    )

    if not title or title.strip() == "":
        log_message(
            "error", "Blog title is empty or None!", "slide_generation", "banner"
        )
        return ""

    # Escape HTML entities to prevent breaking the template
    log_message(
        "info", f"Step 3: Escaping HTML entities in title", "slide_generation", "banner"
    )
    import html

    title_escaped = html.escape(title)
    log_message(
        "info",
        f"Banner slide title (escaped): '{title_escaped}'",
        "slide_generation",
        "banner",
    )

    log_message(
        "info", f"Step 4: Processing category information", "slide_generation", "banner"
    )
    category = getattr(blog, "category", "ROCm Blog")
    category_link = category.lower().replace(" ", "-")

    # split, remove special characters, and convert to lowercase then join
    category_link = "-".join(
        re.sub(r"[^a-z0-9]+", "-", part.strip().lower()) for part in category.split("-")
    ).lower()

    category_url = f"./{category_link}.html"
    log_message(
        "info",
        f"Banner slide category: '{category}', URL: '{category_url}'",
        "slide_generation",
        "banner",
    )

    if hasattr(blog, "thumbnail") and blog.thumbnail:
        thumbnail_path = blog.thumbnail
        thumbnail_base = os.path.splitext(thumbnail_path)[0]

        # Try to find the best available thumbnail format
        thumbnail_found = False

        # Priority order: webp, jpg, jpeg, png (webp is preferred)
        extensions_to_try = [".webp", ".jpg", ".jpeg", ".png"]
        search_paths = [
            rocmblogs.blogs_directory,
            os.path.join(rocmblogs.blogs_directory, "images"),
            os.path.dirname(blog.file_path),
            os.path.join(os.path.dirname(blog.file_path), "images"),
        ]

        log_message(
            "info",
            f"Step 4a: Looking for thumbnail '{thumbnail_path}' with base name '{thumbnail_base}'",
            "slide_generation",
            "banner",
        )

        for ext in extensions_to_try:
            test_filename = thumbnail_base + ext
            for search_path in search_paths:
                test_path = os.path.join(search_path, test_filename)
                if os.path.exists(test_path):
                    log_message(
                        "info",
                        f"Step 4b: Found thumbnail: {test_filename} in {search_path}",
                        "slide_generation",
                        "banner",
                    )
                    blog.thumbnail = test_filename
                    thumbnail_found = True
                    break
            if thumbnail_found:
                break

        if not thumbnail_found:
            log_message(
                "warning",
                f"Step 4c: Thumbnail '{thumbnail_path}' not found in any format or location",
                "slide_generation",
                "banner",
            )

    log_message(
        "info",
        f"Step 5: Processing images for banner slide: '{title}'",
        "slide_generation",
        "banner",
    )

    # Log blog image state before grab_image
    log_message(
        "debug",
        f"Before grab_image - Has image_paths: {hasattr(blog, 'image_paths')}",
        "slide_generation",
        "banner",
    )
    if hasattr(blog, "image_paths"):
        log_message(
            "debug",
            f"Before grab_image - image_paths: {blog.image_paths}",
            "slide_generation",
            "banner",
        )

    try:
        blog.grab_image(rocmblogs)
        log_message(
            "info",
            f"Step 5a: grab_image() completed successfully",
            "slide_generation",
            "banner",
        )
    except Exception as img_error:
        log_message(
            "error",
            f"Step 5a: grab_image() failed: {img_error}",
            "slide_generation",
            "banner",
        )
        log_message(
            "error",
            f"Traceback: {traceback.format_exc()}",
            "slide_generation",
            "banner",
        )
        return ""

    # Log blog image state after grab_image
    log_message(
        "debug",
        f"After grab_image - Has image_paths: {hasattr(blog, 'image_paths')}",
        "slide_generation",
        "banner",
    )
    if hasattr(blog, "image_paths"):
        log_message(
            "debug",
            f"After grab_image - image_paths: {blog.image_paths}",
            "slide_generation",
            "banner",
        )

    log_message("info", f"Step 6: Processing image paths", "slide_generation", "banner")
    if blog.image_paths:
        log_message(
            "info",
            f"Step 6a: Found image_paths: {blog.image_paths}",
            "slide_generation",
            "banner",
        )
        image_filename = os.path.basename(blog.image_paths[0])
        log_message(
            "info",
            f"Step 6b: Using image filename: '{image_filename}'",
            "slide_generation",
            "banner",
        )

        if any(
            image_filename.lower().endswith(ext)
            for ext in (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")
        ):
            webp_filename = os.path.splitext(image_filename)[0] + ".webp"

            webp_exists = False

            if os.path.exists(
                os.path.join(os.path.dirname(blog.file_path), webp_filename)
            ):
                image_filename = webp_filename
                webp_exists = True
                log_message(
                    "info",
                    f"Using WebP version for banner slide image: {webp_filename}",
                    "general",
                    "banner",
                )

            elif os.path.exists(
                os.path.join(os.path.dirname(blog.file_path), "images", webp_filename)
            ):
                image_filename = webp_filename
                webp_exists = True
                log_message(
                    "info",
                    f"Using WebP version for banner slide image: {webp_filename}",
                    "general",
                    "banner",
                )

            elif os.path.exists(
                os.path.join(rocmblogs.blogs_directory, "images", webp_filename)
            ):
                image_filename = webp_filename
                webp_exists = True
                log_message(
                    "info",
                    f"Using WebP version for banner slide image: {webp_filename}",
                    "general",
                    "banner",
                )

            if not webp_exists:
                log_message(
                    "info",
                    f"WebP version not found for {image_filename}, attempting to convert",
                    "general",
                    "banner",
                )

                original_image_path = None

                if os.path.exists(
                    os.path.join(os.path.dirname(blog.file_path), image_filename)
                ):
                    original_image_path = os.path.join(
                        os.path.dirname(blog.file_path), image_filename
                    )

                elif os.path.exists(
                    os.path.join(
                        os.path.dirname(blog.file_path), "images", image_filename
                    )
                ):
                    original_image_path = os.path.join(
                        os.path.dirname(blog.file_path), "images", image_filename
                    )

                elif os.path.exists(
                    os.path.join(rocmblogs.blogs_directory, "images", image_filename)
                ):
                    original_image_path = os.path.join(
                        rocmblogs.blogs_directory, "images", image_filename
                    )

                if original_image_path:
                    try:
                        with Image.open(original_image_path) as img:
                            original_width, original_height = img.size

                            webp_img = img
                            if img.mode not in ("RGB", "RGBA"):
                                webp_img = img.convert("RGB")

                            if original_width > 1200 or original_height > 675:
                                scaling_factor = min(
                                    1200 / original_width, 675 / original_height
                                )

                                new_width = int(original_width * scaling_factor)
                                new_height = int(original_height * scaling_factor)

                                webp_img = webp_img.resize(
                                    (new_width, new_height), resample=Image.LANCZOS
                                )
                                log_message(
                                    "info",
                                    f"Resized image from {original_width}x{original_height} to {new_width}x{new_height}",
                                    "general",
                                    "banner",
                                )

                            webp_path = (
                                os.path.splitext(original_image_path)[0] + ".webp"
                            )
                            webp_img.save(
                                webp_path, format="WEBP", quality=98, method=6
                            )

                            image_filename = webp_filename
                            log_message(
                                "info",
                                f"Successfully converted {image_filename} to WebP: {webp_path}",
                                "general",
                                "banner",
                            )
                    except Exception as error:
                        log_message(
                            "warning",
                            f"Failed to convert {image_filename} to WebP: {error}",
                        )
            image = f"./_images/{image_filename}"
            log_message(
                "info",
                f"Step 6c: Final image path set to: '{image}'",
                "slide_generation",
                "banner",
            )
            log_message(
                "debug",
                f"Image processing completed successfully for: '{image_filename}'",
                "slide_generation",
                "banner",
            )
    else:
        log_message(
            "warning",
            f"Step 6a: No image_paths found for blog '{title}'",
            "slide_generation",
            "banner",
        )
        generic_webp_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "static",
            "images",
            "generic.webp",
        )
        if os.path.exists(generic_webp_path):
            image = "./_images/generic.webp"
            log_message(
                "info",
                f"Using WebP version for generic banner image: {image}",
                "general",
                "banner",
            )
        else:
            image = "./_images/generic.jpg"
            log_message(
                "info",
                f"Step 6d: No image found for banner slide, using generic: '{image}'",
                "slide_generation",
                "banner",
            )

    log_message(
        "info",
        f"Step 7: Processing href for banner slide",
        "slide_generation",
        "banner",
    )

    # Try to get href from blog object, with fallback URL generation
    href = "#"  # Default fallback

    # First try to get the blog URL directly if available
    if hasattr(blog, "blog_url") and blog.blog_url:
        href = f".{blog.blog_url}"
        log_message(
            "info",
            f"Step 7a: Using blog.blog_url: '{href}'",
            "slide_generation",
            "banner",
        )
    else:
        # Try the existing grab_href method
        try:
            raw_href = blog.grab_href()
            log_message(
                "info",
                f"Step 7b: Raw href from grab_href(): '{raw_href}'",
                "slide_generation",
                "banner",
            )

            if raw_href and str(raw_href) != "#":
                if hasattr(raw_href, "split"):
                    href = "." + raw_href.split("/blogs")[-1].replace("\\", "/")
                else:
                    href = "." + str(raw_href).split("/blogs")[-1].replace("\\", "/")
                log_message(
                    "info",
                    f"Step 7c: Processed href: '{href}'",
                    "slide_generation",
                    "banner",
                )
            else:
                log_message(
                    "warning",
                    f"Step 7d: grab_href() returned invalid result, using fallback",
                    "slide_generation",
                    "banner",
                )
        except Exception as href_error:
            log_message(
                "warning",
                f"Step 7e: grab_href() failed: {href_error}, using fallback",
                "slide_generation",
                "banner",
            )

    log_message("info", f"Step 7f: Final href: '{href}'", "slide_generation", "banner")

    log_message(
        "info",
        f"Step 8: Processing description for banner slide",
        "slide_generation",
        "banner",
    )
    description = "Explore the latest insights and developments in ROCm technology."

    if hasattr(blog, "myst") and blog.myst:
        html_meta = blog.myst.get("html_meta", {})
        if html_meta and "description lang=en" in html_meta:
            description = html_meta["description lang=en"]
            log_message(
                "info",
                f"Step 8a: Using description from myst html_meta: '{description[:100]}...'",
                "slide_generation",
                "banner",
            )
    elif hasattr(blog, "description") and blog.description:
        description = blog.description
        log_message(
            "info",
            f"Step 8b: Using description from blog.description: '{description[:100]}...'",
            "slide_generation",
            "banner",
        )
    elif hasattr(blog, "summary") and blog.summary:
        description = blog.summary
        log_message(
            "info",
            f"Step 8c: Using description from blog.summary: '{description[:100]}...'",
            "slide_generation",
            "banner",
        )
    else:
        log_message(
            "info",
            f"Step 8d: Using default description for banner slide",
            "slide_generation",
            "banner",
        )

    log_message(
        "info",
        f"Step 9: Processing authors for banner slide",
        "slide_generation",
        "banner",
    )
    authors_list = getattr(blog, "author", "").split(",")
    log_message(
        "info",
        f"Authors list for banner slide: {authors_list}",
        "slide_generation",
        "banner",
    )

    authors_html = ""

    if authors_list and authors_list[0]:
        log_message(
            "info",
            f"Step 9a: Calling grab_authors with: {authors_list}",
            "slide_generation",
            "banner",
        )
        try:
            authors_html = blog.grab_authors(authors_list, rocmblogs)
            log_message(
                "info",
                f"Step 9b: Generated authors HTML: '{authors_html}'",
                "slide_generation",
                "banner",
            )
        except Exception as author_error:
            log_message(
                "error",
                f"Step 9a: Error generating authors HTML: {author_error}",
                "slide_generation",
                "banner",
            )
            authors_html = ""

    if authors_html:
        author = f"by {authors_html}"
        log_message(
            "info",
            f"Step 9c: Final author string: '{author}'",
            "slide_generation",
            "banner",
        )
    else:
        author = "."
        log_message(
            "info",
            f"Step 9d: No valid authors found, using default: '{author}'",
            "slide_generation",
            "banner",
        )

    log_message(
        "info",
        f"Step 10: All data collection completed for '{title}' (index: {index}, active: {active})",
        "slide_generation",
        "banner",
    )

    # Log all template variables before formatting
    log_message(
        "info", f"Step 11: Template variables summary:", "slide_generation", "banner"
    )
    log_message(
        "info", f"  - active_class: '{active_class}'", "slide_generation", "banner"
    )
    log_message("info", f"  - title: '{title_escaped}'", "slide_generation", "banner")
    log_message("info", f"  - category: '{category}'", "slide_generation", "banner")
    log_message(
        "info", f"  - category_url: '{category_url}'", "slide_generation", "banner"
    )
    log_message("info", f"  - image: '{image}'", "slide_generation", "banner")
    log_message("info", f"  - href: '{href}'", "slide_generation", "banner")
    log_message(
        "info",
        f"  - description: '{description[:50]}...'",
        "slide_generation",
        "banner",
    )
    log_message("info", f"  - author: '{author}'", "slide_generation", "banner")

    try:
        log_message(
            "info", f"Step 12: Formatting slide template", "slide_generation", "banner"
        )
        result = slide_template.format(
            active_class=active_class,
            title=title_escaped,  # Use escaped title
            category=category,
            category_url=category_url,
            image=image,
            href=href,
            description=description,
            author=author,
        )
        log_message(
            "info",
            f"Step 12: [SUCCESS] Successfully formatted slide for index {index}, length: {len(result)}",
            "slide_generation",
            "banner",
        )

        # Log a preview of the generated HTML
        html_preview = result[:300] + "..." if len(result) > 300 else result
        log_message(
            "debug",
            f"Generated HTML preview: {html_preview}",
            "slide_generation",
            "banner",
        )

        log_message(
            "info",
            f"========== GENERATE_BANNER_SLIDE COMPLETED SUCCESSFULLY (index {index}) ==========",
            "slide_generation",
            "banner",
        )
        return result
    except Exception as e:
        log_message(
            "error",
            f"Step 12: [FAILED] FAILED to format banner slide for '{title}': {e}"
            "slide_generation",
            "banner",
        )
        log_message(
            "error",
            f"Template variables summary for debugging:",
            "slide_generation",
            "banner",
        )
        log_message(
            "error",
            f"  - active_class: '{active_class}' (type: {type(active_class)})",
            "slide_generation",
            "banner",
        )
        log_message(
            "error",
            f"  - title: '{title_escaped}' (type: {type(title_escaped)})",
            "slide_generation",
            "banner",
        )
        log_message(
            "error",
            f"  - category: '{category}' (type: {type(category)})",
            "slide_generation",
            "banner",
        )
        log_message(
            "error",
            f"  - image: '{image}' (type: {type(image)})",
            "slide_generation",
            "banner",
        )
        log_message(
            "error",
            f"  - href: '{href}' (type: {type(href)})",
            "slide_generation",
            "banner",
        )
        log_message(
            "error",
            f"Traceback: {traceback.format_exc()}",
            "slide_generation",
            "banner",
        )
        log_message(
            "info",
            f"========== GENERATE_BANNER_SLIDE FAILED (index {index}) ==========",
            "slide_generation",
            "banner",
        )
        return ""


def generate_banner_navigation_item(blog, index: int = 0, active: bool = False) -> str:
    """Generate a banner navigation item with category, title and progress bar."""

    log_message(
        "info",
        f"========== GENERATE_BANNER_NAVIGATION_ITEM (index {index}) ==========",
        "nav_generation",
        "banner",
    )
    log_message(
        "info",
        f"Input parameters - Index: {index}, Active: {active}",
        "nav_generation",
        "banner",
    )

    active_class = " active" if active else ""
    nav_template = """<div class="banner-slider__nav-item{active_class}" data-index="{index}">
        <div class="banner-slider__nav-progress"></div>
        <div class="banner-slider__nav-content">
            <div class="banner-slider__nav-category">{category}</div>
            <div class="banner-slider__nav-title">{title}</div>
        </div>
    </div>"""

    title = blog.blog_title if hasattr(blog, "blog_title") else "No Title"
    category = getattr(blog, "category", "ROCm Blog")

    log_message(
        "debug",
        f"Banner navigation item - Category: {category}, Title: {title}, Index: {index}",
    )

    result = nav_template.format(
        active_class=active_class,
        index=index,
        category=category,
        title=title,
    )

    log_message(
        "debug",
        f"Generated banner navigation item for '{title}' (index: {index}, active: {active})",
    )
    return result
