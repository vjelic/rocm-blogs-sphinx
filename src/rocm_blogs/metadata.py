import re
from datetime import datetime

from rocm_blogs import ROCmBlogs


def metadata_generator(blogs: ROCmBlogs) -> None:
    """Generate metadata for the ROCm blogs."""

    print("Generating metadata...")

    metadata_template = """
---
blogpost: true
blog_title: "{blog_title}"
date: {date}
author: "{author}"
thumbnail: '{thumbnail}'
tags: {tags}
category: {category}
language: English
myst:
    html_meta:
        "author": "{author}"
        "description lang=en": "{description}"
        "keywords": "{keywords}"
        "property=og:locale": "en_US"
---

"""

    for blog in blogs.blog_paths:
        print(blog)

        # grab the metadata from the blog
        metadata = blogs.extract_metadata_from_file(blog)

        if not metadata:
            continue
        else:
            print(metadata)

            # Extract essential metadata
            myst_section = metadata.get("myst", {})
            html_meta = myst_section.get("html_meta", {})
            description = html_meta.get("description lang=en", "")
            keywords = html_meta.get("keywords", "")

            # Extract title from markdown content
            with open(blog, "r", encoding="utf-8", errors="replace") as file:
                content = file.read()

            title_pattern = re.compile(r"^# (.+)$", re.MULTILINE)
            match = title_pattern.search(content)

            if match:
                # Replace single quotes with double quotes in blog_title
                title = match.group(1)
                title = title.replace("\"", "'")
                metadata["blog_title"] = title
            else:
                # Replace single quotes with double quotes in description
                desc = description.replace("'", "\"")
                metadata["blog_title"] = desc

            # Set default values for required fields
            if "author" not in metadata:
                metadata["author"] = "No author"
            else:
                # Replace single quotes with double quotes in author
                metadata["author"] = metadata["author"].replace("'", "''")

            if "thumbnail" not in metadata:
                metadata["thumbnail"] = ""

            if "date" not in metadata:
                metadata["date"] = datetime.now().strftime("%d %B %Y")
                
            if "tags" not in metadata:
                metadata["tags"] = ""
                
            if "category" not in metadata:
                metadata["category"] = "ROCm Blog"

            # Normalize date format if needed
            if "Sept" in metadata["date"]:
                metadata["date"] = metadata["date"].replace("Sept", "Sep")

            # Construct the metadata content
            metadata_content = metadata_template.format(
                blog_title=metadata["blog_title"],
                date=metadata["date"],
                author=metadata["author"],
                thumbnail=metadata["thumbnail"],
                tags=metadata.get("tags", ""),
                category=metadata.get("category", "ROCm Blog"),
                description=description,
                keywords=keywords,
            )

            print(metadata_content)

            # Replace the metadata in the markdown file
            with open(blog, "r", encoding="utf-8", errors="replace") as file:
                content = file.read()

            content = re.sub(
                r"^---\s*\n(.*?)\n---\s*\n", metadata_content, content, flags=re.DOTALL
            )

            # Ensure proper formatting
            content = content.strip() + "\n"

            with open(blog, "w", encoding="utf-8", errors="replace") as file:
                file.write(content)

            print(f"Metadata added to {blog}")
