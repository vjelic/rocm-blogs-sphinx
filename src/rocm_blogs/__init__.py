from datetime import datetime
import os
from pathlib import Path
import logging
import re
import time

from sphinx.application import Sphinx
from sphinx.util import logging as sphinx_logging

import importlib.resources as pkg_resources

from ._rocmblogs import ROCmBlogs
from .grid import generate_grid
from ._version import __version__
from .metadata import metadata_generator

__all__ = ["Blog", "BlogHolder", "ROCmBlogs", "grid_generation", "metadata_generator"]

logger = sphinx_logging.getLogger(__name__)

def calculate_read_time(words: int) -> int:

    return round(words / 245)

def truncate_string(input_string: str) -> str:
    # remove special characters
    cleaned_string = re.sub(r"[!@#$%^&*?/|]", "", input_string)
    # remove spaces
    transformed_string = re.sub(r"\s+", "-", cleaned_string)

    return transformed_string.lower()

def update_index_file(app: Sphinx):
    """Update the index file with the latest blog entries."""

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

        template_html = pkg_resources.read_text("rocm_blogs.templates", "index.html")

        # 2. Load and embed the CSS.
        css_content = pkg_resources.read_text("rocm_blogs.static.css", "index.css")

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

        #metadata_generator(rocmblogs)

        print(rocmblogs.categories)

        all_blogs = rocmblogs.blogs.get_blogs()

        used = []
        grid_items = []
        eco_grid_items = []
        application_grid_items = []
        software_grid_items = []

        for blog in all_blogs:
            if blog not in used:
                used.append(blog)
                grid_items.append(generate_grid(rocmblogs, blog))
                if len(grid_items) == 12:
                    break
        
        for blog in rocmblogs.blogs.blogs_categories.get("Ecosystems and Partners"):
            if blog not in used:
                used.append(blog)
                eco_grid_items.append(generate_grid(rocmblogs, blog))
                if len(eco_grid_items) == 4:
                    break

        for blog in rocmblogs.blogs.blogs_categories.get("Applications & models"):
            if blog not in used:
                used.append(blog)
                application_grid_items.append(generate_grid(rocmblogs, blog))
                if len(application_grid_items) == 4:
                    break

        for blog in rocmblogs.blogs.blogs_categories.get("Software tools & optimizations"):
            if blog not in used:
                used.append(blog)
                software_grid_items.append(generate_grid(rocmblogs, blog))
                if len(software_grid_items) == 4:
                    break
        
        grid_content = "\n".join(grid_items)
        eco_grid_content = "\n".join(eco_grid_items)
        application_grid_content = "\n".join(application_grid_items)
        software_grid_content = "\n".join(software_grid_items)

        updated_html = index_template.replace("{grid_items}", grid_content)
        updated_html = updated_html.replace("{eco_grid_items}", eco_grid_content)
        updated_html = updated_html.replace("{application_grid_items}", application_grid_content)
        updated_html = updated_html.replace("{software_grid_items}", software_grid_content)

        # 6. Write the updated HTML to blogs/index.md.
        output_path = Path(blogs_dir) / "index.md"
        with output_path.open("w", encoding="utf-8") as f:
            f.write(updated_html)

        print(f"Successfully updated {output_path} with new grid items.")
        print(blogs_dir / "index.md")
        print(blogs_dir)

        logger.info(f"Successfully updated {output_path} with new grid items.")
    except Exception as error:
        logger.warning(f"Failed to update index file: {error}")

def quickshare(blog):

    css = pkg_resources.read_text("rocm_blogs.static.css", "social-bar.css")

    html = pkg_resources.read_text("rocm_blogs.templates", "social-bar.html")

    social_bar = """
<style>
{CSS}
</style>
{HTML}
"""

    social_bar = social_bar.format(CSS=css, HTML=html)

    url = f"http://rocm.blogs.amd.com{blog.grab_href()[1:]}"

    title = blog.blog_title if hasattr(blog, "blog_title") else "No Title"

    if hasattr(blog, "myst"):
        description = blog.myst.get("html_meta", {}).get(
            "description lang=en", "No Description"
        )
    else:
        description = "No Description"
    title = f"{title} | ROCm Blogs"

    social_bar = (
        social_bar.replace("{URL}", url)
        .replace("{TITLE}", title)
        .replace("{TEXT}", description)
    )

    return social_bar

def blog_generation(app: Sphinx):
    """Generate blog pages with enhanced styling and metadata.
    
    This function processes each blog file, adding styling, author attribution,
    images, and social sharing buttons. It includes robust error handling and
    file backup mechanisms to prevent data loss.
    """
    
    try:
        env = app.builder.env
        srcdir = Path(env.srcdir)

        rocmblogs = ROCmBlogs()
        blogs_dir = rocmblogs.find_blogs_directory(str(srcdir))
        rocmblogs.blogs_directory = str(blogs_dir)
        rocmblogs.find_readme_files_cache()
        rocmblogs.create_blog_objects()
        rocmblogs.blogs.sort_blogs_by_date()

        # Process each blog
        for blog in rocmblogs.blogs.get_blogs():
            try:
                process_single_blog(blog, rocmblogs)
            except Exception as e:
                logger.warning(f"Error processing blog {blog.file_path}: {e}")
                # Continue with next blog instead of failing completely
                continue
    except Exception as error:
        logger.warning(f"Failed to generate blogs: {error}")

def count_words_in_markdown(content: str) -> int:
    """
    Count words in a markdown file, excluding code blocks and other non-paragraph areas.
    
    Args:
        content: The content of the markdown file as a string.
        
    Returns:
        The number of words in the markdown file.
    """
    # Remove YAML front matter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2]
    

    content = re.sub(r'```[\s\S]*?```', '', content)

    content = re.sub(r'(?m)^( {4}|\t).*$', '', content)
    
    content = re.sub(r'<[^>]*>', '', content)

    content = re.sub(r'https?://\S+', '', content)

    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)

    content = re.sub(r'\[.*?\]\(.*?\)', '', content)
    
    content = re.sub(r'(?m)^#.*$', '', content)

    content = re.sub(r'(?m)^(---|***|___)$', '', content)

    content = re.sub(r'(?m)^>.*$', '', content)

    content = re.sub(r'(?m)^[ \t]*[-*+][ \t]+', '', content)
    content = re.sub(r'(?m)^[ \t]*\d+\.[ \t]+', '', content)

    words = [word for word in re.split(r'\s+', content) if word.strip()]
    
    return len(words)

def process_single_blog(blog, rocmblogs):
    readme_file = blog.file_path
    backup_file = f"{readme_file}.bak"
    
    # Skip processing if the blog doesn't have required attributes
    if not hasattr(blog, "author") or not blog.author:
        print(f"Skipping blog {readme_file} - no author found")
        return
    
    try:
        # Create a backup of the original file
        try:
            with open(readme_file, "r", encoding="utf-8", errors="replace") as src:
                content = src.read()
            with open(backup_file, "w", encoding="utf-8", errors="replace") as dst:
                dst.write(content)
        except Exception as e:
            print(f"Warning: Could not create backup of {readme_file}: {e}")
            # Continue anyway, but with caution
        
        # Calculate word count from the content
        word_count = count_words_in_markdown(content)
        blog.set_word_count(word_count)
        print(f"Word count for {readme_file}: {word_count}")
        
        # Read the file once
        try:
            with open(readme_file, "r", encoding="utf-8", errors="replace") as file:
                lines = file.readlines()
        except Exception as e:
            print(f"Error reading {readme_file}: {e}")
            return
        
        # Prepare all the data and templates before modifying the file
        try:
            # Process author information
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
            blog_read_time = str(calculate_read_time(getattr(blog, "word_count", 0))) if hasattr(blog, "word_count") else "No Read Time"
            
            # Get author HTML
            authors_html = blog.grab_authors(authors_list)
            if authors_html:
                authors_html = authors_html.replace("././", "../../").replace(".md", ".html")
            
            # Find the title and its position
            title, line_number = None, None
            for i, line in enumerate(lines):
                if line.startswith("#") and line.count("#") == 1:
                    title = line
                    line_number = i
                    break
            
            if not title or line_number is None:
                print(f"Skipping blog {readme_file} - could not find title")
                return
            
            # Load templates and CSS
            quickshare_button = quickshare(blog)
            image_css = pkg_resources.read_text("rocm_blogs.static.css", "image_blog.css")
            image_html = pkg_resources.read_text("rocm_blogs.templates", "image_blog.html")
            blog_css = pkg_resources.read_text("rocm_blogs.static.css", "blog.css")
            author_attribution_template = pkg_resources.read_text("rocm_blogs.templates", "author_attribution.html")
            
            # Fill in the author attribution template
            authors_html_filled = (
                author_attribution_template.replace("{authors_string}", authors_html)
                .replace("{date}", date)
                .replace("{language}", language)
                .replace("{category}", category_html)
                .replace("{tags}", tags_html)
                .replace("{read_time}", blog_read_time)
                .replace(
                    "{word_count}",
                    str(getattr(blog, "word_count", "No Word Count"))
                )
            )
            
            # Get the image path
            try:
                image_path = blog.grab_image(rocmblogs)
                if blog.image_paths:
                    blog_image = f"../../_images/{blog.image_paths[0]}"
                else:
                    blog_image = "../../_images/generic.jpg"
            except Exception as e:
                print(f"Error getting image for {readme_file}: {e}")
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
            
            # Write the modified file
            with open(readme_file, "w", encoding="utf-8", errors="replace") as file:
                file.writelines(new_lines)
            
            print(f"Successfully processed blog {readme_file}")
            
            # Remove the backup file if everything went well
            try:
                os.remove(backup_file)
            except:
                pass  # Ignore errors when removing backup
                
        except Exception as e:
            print(f"Error processing data for {readme_file}: {e}")
            # Restore from backup if possible
            try:
                if os.path.exists(backup_file):
                    with open(backup_file, "r", encoding="utf-8", errors="replace") as src:
                        content = src.read()
                    with open(readme_file, "w", encoding="utf-8", errors="replace") as dst:
                        dst.write(content)
                    print(f"Restored {readme_file} from backup")
            except:
                print(f"WARNING: Could not restore {readme_file} from backup")
            
    except Exception as e:
        print(f"Unexpected error processing {readme_file}: {e}")
        # Try to restore from backup if possible
        try:
            if os.path.exists(backup_file):
                with open(backup_file, "r", encoding="utf-8", errors="replace") as src:
                    content = src.read()
                with open(readme_file, "w", encoding="utf-8", errors="replace") as dst:
                    dst.write(content)
                print(f"Restored {readme_file} from backup after unexpected error")
        except:
            print(f"WARNING: Could not restore {readme_file} from backup after unexpected error")

def setup(app: Sphinx):

    app.connect("builder-inited", update_index_file)
    app.connect("builder-inited", blog_generation)

    return {"version": __version__, "parallel_read_safe": True, "parallel_write_safe": True}
