import os

from PIL import Image
from sphinx.util import logging as sphinx_logging


# Import log_message from the main module
def log_message(level, message, operation="general", component="rocmblogs", **kwargs):
    """Import log_message function from main module to avoid circular imports."""
    try:
        from . import log_message as main_log_message

        return main_log_message(level, message, operation, component, **kwargs)
    except ImportError:
        # Fallback to print if import fails
        print(f"[{level.upper()}] {message}")


def generate_grid(ROCmBlogs, blog, lazy_load=False, use_og=False) -> str:
    """Takes a blog and creates a sphinx grid item with WebP image support."""
    log_message("info", "Generating grid item for blog", "general", "grid")

    grid_template = """
:::{{grid-item-card}}
:padding: 1
:img-top: {image}
:class-img-top: small-sd-card-img-top
:class-body: small-sd-card
:class: small-sd-card
:img-lazy-load: true
+++
<a href="{href}" class="small-card-header-link">
    <h2 class="card-header">{title}</h2>
</a>
<p class="paragraph">{description}</p>
<div class="date">{date} {authors_html}</div>
:::
"""

    title = blog.blog_title if hasattr(blog, "blog_title") else "No Title"
    log_message("info", f"Grid item title: {title}", "general", "grid", title=title)

    date = blog.date.strftime("%B %d, %Y") if blog.date else "No Date"
    log_message("info", f"Grid item date: {date}", "general", "grid", date=date)

    description = "No Description"
    if hasattr(blog, "myst") and blog.myst:
        html_meta = blog.myst.get("html_meta", {})
        if html_meta and "description lang=en" in html_meta:
            description = html_meta["description lang=en"]
            log_message(
                "info",
                "Using description from myst html_meta",
                "general",
                "grid",
                description=description,
            )
    else:
        log_message(
            "info",
            "No myst metadata found, using default description",
            "general",
            "grid",
        )

    authors_list = getattr(blog, "author", "").split(",")
    log_message(
        "info",
        f"Authors list for grid item: {authors_list}",
        "general",
        "grid",
        authors_list=authors_list,
    )

    if hasattr(blog, "thumbnail") and blog.thumbnail:
        thumbnail_path = blog.thumbnail
        webp_thumbnail_path = os.path.splitext(thumbnail_path)[0] + ".webp"

        if os.path.exists(os.path.join(ROCmBlogs.blogs_directory, webp_thumbnail_path)):
            log_message(
                "info",
                f"Using WebP version for grid item thumbnail: {webp_thumbnail_path}",
                "general",
                "grid",
            )
            blog.thumbnail = webp_thumbnail_path
        elif os.path.exists(
            os.path.join(os.path.dirname(blog.file_path), webp_thumbnail_path)
        ):
            log_message(
                "info",
                f"Using WebP version for grid item thumbnail: {webp_thumbnail_path}",
                "general",
                "grid",
            )
            blog.thumbnail = webp_thumbnail_path
        elif os.path.exists(
            os.path.join(os.path.dirname(blog.file_path), "images", webp_thumbnail_path)
        ):
            log_message(
                "info",
                f"Using WebP version for grid item thumbnail: {webp_thumbnail_path}",
                "general",
                "grid",
            )
            blog.thumbnail = webp_thumbnail_path

    log_message(
        "info", f"Getting image for grid item: {title}", "general", "grid", title=title
    )
    image = blog.grab_image(ROCmBlogs)

    image_str = str(image)

    # For grid items, use the relative path from blogs directory (no "_images/" prefix)
    # Remove any leading "./" if present and convert to forward slashes for consistency
    if image_str.startswith("./"):
        image_str = image_str[2:]
    image_str = image_str.replace("\\", "/")
    image = image_str
    log_message(
        "info",
        f"Using image path for grid: {image_str}",
        "general",
        "grid",
        image_str=image_str,
    )

    if "generic.jpg" in image_str.lower():

        generic_webp_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "static",
            "images",
            "generic.webp",
        )
        if os.path.exists(generic_webp_path):

            image = (
                str(image)
                .replace("generic.jpg", "generic.webp")
                .replace("generic.JPG", "generic.webp")
            )
            log_message(
                "info",
                f"Using WebP version for generic image: {image}",
                "general",
                "grid",
            )

    elif any(
        image_str.lower().endswith(ext)
        for ext in (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")
    ):
        base_name = os.path.splitext(image_str)[0]
        webp_image = base_name + ".webp"

        webp_exists = False

        if os.path.exists(os.path.join(ROCmBlogs.blogs_directory, webp_image)):
            image = webp_image
            webp_exists = True

        elif os.path.exists(os.path.join(os.path.dirname(blog.file_path), webp_image)):
            image = webp_image
            webp_exists = True

        elif os.path.exists(
            os.path.join(
                os.path.dirname(blog.file_path), "images", os.path.basename(webp_image)
            )
        ):
            image = os.path.join(
                os.path.dirname(image_str), os.path.basename(webp_image)
            )
            webp_exists = True

        if webp_exists:
            log_message(
                "info",
                f"Using WebP version for grid item image: {image}",
                "general",
                "grid",
            )
        else:
            log_message(
                "info",
                f"WebP version not found for {image_str}, attempting to convert",
                "general",
                "grid",
            )

            original_image_path = None

            if os.path.exists(os.path.join(ROCmBlogs.blogs_directory, image_str)):
                original_image_path = os.path.join(ROCmBlogs.blogs_directory, image_str)

            elif os.path.exists(
                os.path.join(os.path.dirname(blog.file_path), image_str)
            ):
                original_image_path = os.path.join(
                    os.path.dirname(blog.file_path), image_str
                )

            elif os.path.exists(
                os.path.join(
                    os.path.dirname(blog.file_path),
                    "images",
                    os.path.basename(image_str),
                )
            ):
                original_image_path = os.path.join(
                    os.path.dirname(blog.file_path),
                    "images",
                    os.path.basename(image_str),
                )

            if original_image_path:
                try:

                    with Image.open(original_image_path) as img:

                        original_width, original_height = img.size

                        webp_img = img
                        if img.mode not in ("RGB", "RGBA"):
                            webp_img = img.convert("RGB")

                        if original_width > 1280 or original_height > 720:
                            scaling_factor = min(
                                1280 / original_width, 720 / original_height
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
                                "grid",
                            )

                        webp_path = os.path.splitext(original_image_path)[0] + ".webp"
                        webp_img.save(webp_path, format="WEBP", quality=98, method=6)

                        image = webp_image
                        log_message(
                            "info",
                            f"Successfully converted {image_str} to WebP: {webp_path}",
                            "general",
                            "grid",
                        )
                except Exception as e:
                    log_message(
                        "warning",
                        f"Failed to convert {image_str} to WebP: {e}",
                        "general",
                        "grid",
                    )

    log_message("debug", f"Using image for grid item: {image}", "general", "grid")

    authors_html = ""

    if authors_list:
        authors_html = blog.grab_authors(authors_list, ROCmBlogs)
        log_message(
            "info",
            f"Generated authors HTML: {authors_html}",
            "general",
            "grid",
            authors_html=authors_html,
        )

    if authors_html:
        authors_html = f"by {authors_html}"
        log_message(
            "info",
            f"Final authors HTML with prefix: {authors_html}",
            "general",
            "grid",
            authors_html=authors_html,
        )
    else:
        log_message("debug", "No valid authors found for grid item", "general", "grid")

    raw_href = blog.grab_href()
    if hasattr(raw_href, "split"):
        href = "." + raw_href.split("/blogs")[-1].replace("\\", "/")
    else:
        href = "." + str(raw_href).split("/blogs")[-1].replace("\\", "/")
    log_message("debug", f"Grid item href: {href}", "general", "grid", href=href)

    log_message("info", f"Generated grid item for '{title}'", "general", "grid")

    if use_og:
        image = blog.grab_og_image()
        href = blog.grab_og_href()

    return grid_template.format(
        title=title,
        date=date,
        description=description,
        authors_html=authors_html,
        image=image,
        href=href,
    )
