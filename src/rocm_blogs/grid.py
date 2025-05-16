import os

from PIL import Image
from sphinx.util import logging as sphinx_logging

sphinx_diagnostics = sphinx_logging.getLogger(__name__)

def generate_grid(ROCmBlogs, blog, lazy_load=False, use_og=False) -> str:
    """Takes a blog and creates a sphinx grid item with WebP image support."""
    
    sphinx_diagnostics.debug(
        f"Generating grid item for blog: {getattr(blog, 'blog_title', 'Unknown')}"
    )

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
    sphinx_diagnostics.debug(
        f"Grid item title: {title}"
    )

    date = blog.date.strftime("%B %d, %Y") if blog.date else "No Date"
    sphinx_diagnostics.debug(
        f"Grid item date: {date}"
    )

    description = "No Description"
    if hasattr(blog, "myst") and blog.myst:
        html_meta = blog.myst.get("html_meta", {})
        if html_meta and "description lang=en" in html_meta:
            description = html_meta["description lang=en"]
            sphinx_diagnostics.debug(
                f"Using description from myst html_meta"
            )
    else:
        sphinx_diagnostics.debug(
            f"No myst metadata found, using default description"
        )

    authors_list = getattr(blog, "author", "").split(",")
    sphinx_diagnostics.debug(
        f"Authors list for grid item: {authors_list}"
    )

    if hasattr(blog, "thumbnail") and blog.thumbnail:
        thumbnail_path = blog.thumbnail
        webp_thumbnail_path = os.path.splitext(thumbnail_path)[0] + '.webp'

        if os.path.exists(os.path.join(ROCmBlogs.blogs_directory, webp_thumbnail_path)):
            sphinx_diagnostics.info(
                f"Using WebP version for grid item thumbnail: {webp_thumbnail_path}"
            )
            blog.thumbnail = webp_thumbnail_path
        elif os.path.exists(os.path.join(os.path.dirname(blog.file_path), webp_thumbnail_path)):
            sphinx_diagnostics.info(
                f"Using WebP version for grid item thumbnail: {webp_thumbnail_path}"
            )
            blog.thumbnail = webp_thumbnail_path
        elif os.path.exists(os.path.join(os.path.dirname(blog.file_path), "images", webp_thumbnail_path)):
            sphinx_diagnostics.info(
                f"Using WebP version for grid item thumbnail: {webp_thumbnail_path}"
            )
            blog.thumbnail = webp_thumbnail_path

    sphinx_diagnostics.debug(
        f"Getting image for grid item: {title}"
    )
    image = blog.grab_image(ROCmBlogs)
 
    image_str = str(image)

    if "generic.jpg" in image_str.lower():

        generic_webp_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images", "generic.webp")
        if os.path.exists(generic_webp_path):

            image = str(image).replace("generic.jpg", "generic.webp").replace("generic.JPG", "generic.webp")
            sphinx_diagnostics.info(
                f"Using WebP version for generic image: {image}"
            )

    elif any(image_str.lower().endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG')):
        base_name = os.path.splitext(image_str)[0]
        webp_image = base_name + '.webp'

        webp_exists = False

        if os.path.exists(os.path.join(ROCmBlogs.blogs_directory, webp_image)):
            image = webp_image
            webp_exists = True

        elif os.path.exists(os.path.join(os.path.dirname(blog.file_path), webp_image)):
            image = webp_image
            webp_exists = True

        elif os.path.exists(os.path.join(os.path.dirname(blog.file_path), "images", os.path.basename(webp_image))):
            image = os.path.join(os.path.dirname(image_str), os.path.basename(webp_image))
            webp_exists = True
            
        if webp_exists:
            sphinx_diagnostics.info(
                f"Using WebP version for grid item image: {image}"
            )
        else:
            sphinx_diagnostics.info(
                f"WebP version not found for {image_str}, attempting to convert"
            )

            original_image_path = None

            if os.path.exists(os.path.join(ROCmBlogs.blogs_directory, image_str)):
                original_image_path = os.path.join(ROCmBlogs.blogs_directory, image_str)

            elif os.path.exists(os.path.join(os.path.dirname(blog.file_path), image_str)):
                original_image_path = os.path.join(os.path.dirname(blog.file_path), image_str)

            elif os.path.exists(os.path.join(os.path.dirname(blog.file_path), "images", os.path.basename(image_str))):
                original_image_path = os.path.join(os.path.dirname(blog.file_path), "images", os.path.basename(image_str))

            if original_image_path:
                try:

                    with Image.open(original_image_path) as img:

                        original_width, original_height = img.size

                        webp_img = img
                        if img.mode not in ('RGB', 'RGBA'):
                            webp_img = img.convert('RGB')

                        if original_width > 1280 or original_height > 720:
                            scaling_factor = min(1280 / original_width, 720 / original_height)
                            
                            new_width = int(original_width * scaling_factor)
                            new_height = int(original_height * scaling_factor)
                            
                            webp_img = webp_img.resize((new_width, new_height), resample=Image.LANCZOS)
                            sphinx_diagnostics.info(
                                f"Resized image from {original_width}x{original_height} to {new_width}x{new_height}"
                            )

                        webp_path = os.path.splitext(original_image_path)[0] + '.webp'
                        webp_img.save(webp_path, format="WEBP", quality=85, method=6)

                        image = webp_image
                        sphinx_diagnostics.info(
                            f"Successfully converted {image_str} to WebP: {webp_path}"
                        )
                except Exception as e:
                    sphinx_diagnostics.warning(
                        f"Failed to convert {image_str} to WebP: {e}"
                    )
    
    sphinx_diagnostics.debug(
        f"Using image for grid item: {image}"
    )

    authors_html = ""

    if authors_list:
        authors_html = blog.grab_authors(authors_list)
        sphinx_diagnostics.debug(
            f"Generated authors HTML: {authors_html}"
        )

    if authors_html:
        authors_html = f"by {authors_html}"
        sphinx_diagnostics.debug(
            f"Final authors HTML with prefix: {authors_html}"
        )
    else:
        sphinx_diagnostics.debug(
            f"No valid authors found for grid item"
        )

    raw_href = blog.grab_href()
    if hasattr(raw_href, "split"):
        href = "." + raw_href.split("/blogs")[-1].replace("\\", "/")
    else:
        href = "." + str(raw_href).split("/blogs")[-1].replace("\\", "/")
    sphinx_diagnostics.debug(
        f"Grid item href: {href}"
    )

    sphinx_diagnostics.info(
        f"Generated grid item for '{title}'"
    )

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