"""
Banner slider generation for ROCm Blogs.
"""

import os

from PIL import Image
from sphinx.util import logging as sphinx_logging

sphinx_diagnostics = sphinx_logging.getLogger(__name__)


def generate_banner_slide(blog, rocmblogs, index: int = 0, active: bool = False) -> str:
    """Generate a single banner slide for a blog in NVIDIA-inspired style."""

    sphinx_diagnostics.debug(
        f"Generating banner slide for blog index {index} (active={active})"
    )

    slide_template = """
<div class="banner-slide">
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
        <div class="banner-slide__title__link">
            <a href="{href}" class="cta--prim">
                Read now
            </a>
        </div>
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

    title = blog.blog_title if hasattr(blog, "blog_title") else "No Title"
    sphinx_diagnostics.debug(f"Banner slide title: {title}")

    category = getattr(blog, "category", "ROCm Blog")
    category_link = category.lower().replace(" ", "-")
    category_url = f"./blog/category/{category_link}.html"
    sphinx_diagnostics.debug(f"Banner slide category: {category}, URL: {category_url}")

    if hasattr(blog, "thumbnail") and blog.thumbnail:
        thumbnail_path = blog.thumbnail
        webp_thumbnail_path = os.path.splitext(thumbnail_path)[0] + ".webp"

        if os.path.exists(os.path.join(rocmblogs.blogs_directory, webp_thumbnail_path)):
            sphinx_diagnostics.info(
                f"Using WebP version for banner slide thumbnail: {webp_thumbnail_path}"
            )
            blog.thumbnail = webp_thumbnail_path
        elif os.path.exists(
            os.path.join(os.path.dirname(blog.file_path), webp_thumbnail_path)
        ):
            sphinx_diagnostics.info(
                f"Using WebP version for banner slide thumbnail: {webp_thumbnail_path}"
            )
            blog.thumbnail = webp_thumbnail_path
        elif os.path.exists(
            os.path.join(os.path.dirname(blog.file_path), "images", webp_thumbnail_path)
        ):
            sphinx_diagnostics.info(
                f"Using WebP version for banner slide thumbnail: {webp_thumbnail_path}"
            )
            blog.thumbnail = webp_thumbnail_path

    sphinx_diagnostics.debug(f"Getting image for banner slide: {title}")
    blog.grab_image(rocmblogs)

    if blog.image_paths:
        image_filename = os.path.basename(blog.image_paths[0])

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
                sphinx_diagnostics.info(
                    f"Using WebP version for banner slide image: {webp_filename}"
                )

            elif os.path.exists(
                os.path.join(os.path.dirname(blog.file_path), "images", webp_filename)
            ):
                image_filename = webp_filename
                webp_exists = True
                sphinx_diagnostics.info(
                    f"Using WebP version for banner slide image: {webp_filename}"
                )

            elif os.path.exists(
                os.path.join(rocmblogs.blogs_directory, "images", webp_filename)
            ):
                image_filename = webp_filename
                webp_exists = True
                sphinx_diagnostics.info(
                    f"Using WebP version for banner slide image: {webp_filename}"
                )

            if not webp_exists:
                sphinx_diagnostics.info(
                    f"WebP version not found for {image_filename}, attempting to convert"
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
                                sphinx_diagnostics.info(
                                    f"Resized image from {original_width}x{original_height} to {new_width}x{new_height}"
                                )

                            webp_path = (
                                os.path.splitext(original_image_path)[0] + ".webp"
                            )
                            webp_img.save(
                                webp_path, format="WEBP", quality=85, method=6
                            )

                            image_filename = webp_filename
                            sphinx_diagnostics.info(
                                f"Successfully converted {image_filename} to WebP: {webp_path}"
                            )
                    except Exception as error:
                        sphinx_diagnostics.warning(
                            f"Failed to convert {image_filename} to WebP: {error}"
                        )
            image = f"./_images/{image_filename}"
            sphinx_diagnostics.debug(f"Using image for banner slide: {image}")
    else:
        generic_webp_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "static",
            "images",
            "generic.webp",
        )
        if os.path.exists(generic_webp_path):
            image = "./_images/generic.webp"
            sphinx_diagnostics.info(
                f"Using WebP version for generic banner image: {image}"
            )
        else:
            image = "./_images/generic.jpg"
            sphinx_diagnostics.debug(
                f"No image found for banner slide, using generic: {image}"
            )

    raw_href = blog.grab_href()
    if hasattr(raw_href, "split"):
        href = "." + raw_href.split("/blogs")[-1].replace("\\", "/")
    else:
        href = "." + str(raw_href).split("/blogs")[-1].replace("\\", "/")
        sphinx_diagnostics.debug(f"Banner slide href: {href}")

    description = "Explore the latest insights and developments in ROCm technology."
    if hasattr(blog, "myst") and blog.myst:
        html_meta = blog.myst.get("html_meta", {})
        if html_meta and "description lang=en" in html_meta:
            description = html_meta["description lang=en"]
            sphinx_diagnostics.debug(f"Using description from myst html_meta")
    elif hasattr(blog, "description") and blog.description:
        description = blog.description
        sphinx_diagnostics.debug(f"Using description from blog.description")
    elif hasattr(blog, "summary") and blog.summary:
        description = blog.summary
        sphinx_diagnostics.debug(f"Using description from blog.summary")
    else:
        sphinx_diagnostics.debug(f"Using default description for banner slide")

    authors_list = getattr(blog, "author", "").split(",")
    sphinx_diagnostics.debug(f"Authors list for banner slide: {authors_list}")

    authors_html = ""

    if authors_list and authors_list[0]:
        authors_html = blog.grab_authors(authors_list, rocmblogs.blogs_directory)
        sphinx_diagnostics.debug(f"Generated authors HTML: {authors_html}")

    if authors_html:
        author = f"by {authors_html}"
    else:
        author = "."
        sphinx_diagnostics.debug(f"No valid authors found, using default: {author}")

    sphinx_diagnostics.info(
        f"Generated banner slide for '{title}' (index: {index}, active: {active})"
    )
    return slide_template.format(
        title=title,
        category=category,
        category_url=category_url,
        image=image,
        href=href,
        description=description,
        author=author,
    )


def generate_banner_navigation_item(blog, index: int = 0, active: bool = False) -> str:
    """Generate a banner navigation item in NVIDIA-inspired style."""

    sphinx_diagnostics.debug(
        f"Generating banner navigation item for blog index {index} (active={active})"
    )

    active_class = " active" if active else ""
    nav_template = """
        <li class="banner-slider__nav-item{active_class}">
            <div class="banner-slider__nav-progress-bar"></div>
            <div class="banner-slider__nav-title">
                {category}
            </div>
            <div class="banner-slider__nav-category">
                {title}
            </div>
            <button class="js-banner-slider__nav-btn banner-slider__nav-btn{active_btn_class}" type="button" value="{index}">
                {title}
            </button>
        </li>
    """

    title = blog.blog_title if hasattr(blog, "blog_title") else "No Title"
    category = getattr(blog, "category", "ROCm Blog")

    sphinx_diagnostics.debug(
        f"Banner navigation item - Title: {title}, Category: {category}"
    )

    result = nav_template.format(
        active_class=active_class,
        active_btn_class=" active" if active else "",
        title=title,
        category=category,
        index=index,
    )

    sphinx_diagnostics.debug(
        f"Generated banner navigation item for '{title}' (index: {index}, active: {active})"
    )
    return result
