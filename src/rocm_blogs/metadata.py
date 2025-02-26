import re
from datetime import datetime

from numpy import remainder as rem

from rocm_blogs import ROCmBlogs


def is_leap_year(year: int) -> bool:
    """Determine whether a year is a leap year."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def calculate_day_of_week(y: int, m: int, d: int) -> str:
    """return day of week of given date as string, using Gauss's algorithm to find it"""

    if is_leap_year(y):
        month_offset = (0, 3, 4, 0, 2, 5, 0, 3, 6, 1, 4, 6)[m - 1]
    else:
        month_offset = (0, 3, 3, 6, 1, 4, 6, 2, 5, 0, 3, 5)[m - 1]
    y -= 1
    wd = int(
        rem(d + month_offset + 5 * rem(y, 4) + 4 * rem(y, 100) + 6 * rem(y, 400), 7)
    )

    return ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")[wd]


def metadata_generator(blogs: ROCmBlogs) -> None:
    """Generate metadata for the ROCm blogs."""

    print("Generating metadata...")

    metadata_template = """
---
blogpost: true
blog_title: "{blog_title}"
date: {date}
author: '{author}'
thumbnail: '{thumbnail}'
tags: {tags}
category: {category}
target_audience: {target_audience}
key_value_propositions: {key_value_propositions}
language: English
myst:
    html_meta:
        "author": "{author}"
        "description lang=en": "{description}"
        "keywords": "{keywords}"
        "property=og:locale": "en_US"
        "amd_category": {amd_category}
        "amd_asset_type": {amd_asset_type}
        "amd_blog_type": {amd_blog_type}
        "amd_technical_blog_type": {amd_technical_blog_type}
        "amd_developer_type": {amd_developer_type}
        "amd_deployment": {amd_deployment}
        "amd_product_type": {amd_product_type}
        "amd_developer_tool": {amd_developer_tool}
        "amd_applications": {amd_applications}
        "amd_industries": {amd_industries}
        "amd_blog_releasedate": {amd_blog_releasedate}
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

            myst_section = metadata.get("myst", {})
            html_meta = myst_section.get("html_meta", {})
            description = html_meta.get("description lang=en", "")
            amd_category = html_meta.get("amd_category", "Developer Resources")
            amd_asset_type = html_meta.get("amd_asset_type", "Blogs")
            amd_blog_type = html_meta.get("amd_blog_type", "Technical Articles & Blogs")
            amd_technical_blog_type = html_meta.get("amd_technical_blog_type", "")
            amd_developer_type = html_meta.get("amd_developer_type", "")
            amd_deployment = html_meta.get("amd_deployment", "Servers")
            amd_product_type = html_meta.get("amd_product_type", "Accelerators")
            amd_developer_tool = html_meta.get("amd_developer_tool", "")
            amd_applications = html_meta.get("amd_applications", "")
            amd_industries = html_meta.get("amd_industries", "Data Center")
            keywords = html_meta.get("keywords", "")

            # grab the title from the markdown
            with open(blog, "r", encoding="utf-8", errors="replace") as file:
                content = file.read()

            title_pattern = re.compile(r"^# (.+)$", re.MULTILINE)
            match = title_pattern.search(content)

            if match:
                metadata["blog_title"] = match.group(1)
            else:
                metadata["blog_title"] = description

            if "author" not in metadata:
                metadata["author"] = "No author"

            if "thumbnail" not in metadata:
                metadata["thumbnail"] = ""

            if "date" not in metadata:
                metadata["date"] = "9999-12-31"

            if "Sept" in metadata["date"]:
                metadata["date"] = metadata["date"].replace("Sept", "Sep")

            date_formats = [
                "%d-%m-%Y",  # e.g. 8-08-2024
                "%d/%m/%Y",  # e.g. 8/08/2024
                "%d-%B-%Y",  # e.g. 8-August-2024
                "%d-%b-%Y",  # e.g. 8-Aug-2024
                "%d %B %Y",  # e.g. 8 August 2024
                "%d %b %Y",  # e.g. 8 Aug 2024
                "%d %B, %Y",  # e.g. 8 August, 2024
                "%d %b, %Y",  # e.g. 8 Aug, 2024
                "%B %d, %Y",  # e.g. August 8, 2024
                "%b %d, %Y",  # e.g. Aug 8, 2024
                "%B %d %Y",  # e.g. August 8 2024
                "%b %d %Y",  # e.g. Aug 8 2024
            ]

            for fmt in date_formats:
                try:
                    date_string = datetime.strptime(metadata["date"], fmt).strftime(
                        "%d %B %Y"
                    )
                    break
                except ValueError:
                    continue

            # check all of the date formats

            # amd blog release date format Day-of-week Month Day, 12:00:00 PST Year
            # calculate the day of week based on the date

            day, month, year = date_string.split(" ")

            month = month[:3]

            date_formats = ["%b", "%B"]

            for fmt in date_formats:
                try:
                    d_month = datetime.strptime(month, fmt).month
                    break
                except ValueError:
                    continue

            day = int(day)
            year = int(year)

            day_of_week = calculate_day_of_week(year, d_month, day)

            # day of week, month, day, 12:00:00 PST year
            amd_blog_releasedate = datetime.strptime(
                f"{day_of_week} {month} {day}, 12:00:00 PST {year}",
                "%a %B %d, 12:00:00 PST %Y",
            ).strftime("%a %B %d, 12:00:00 PST %Y")

            # construct the metadata
            metadata_content = metadata_template.format(
                blog_title=metadata["blog_title"],
                date=metadata["date"],
                author=metadata["author"],
                thumbnail=metadata["thumbnail"],
                tags=metadata["tags"],
                category=metadata["category"],
                description=description,
                keywords=keywords,
                amd_category=amd_category,
                amd_asset_type=amd_asset_type,
                amd_blog_type=amd_blog_type,
                amd_technical_blog_type=amd_technical_blog_type,
                amd_developer_type=amd_developer_type,
                amd_deployment=amd_deployment,
                amd_product_type=amd_product_type,
                amd_developer_tool=amd_developer_tool,
                amd_applications=amd_applications,
                amd_industries=amd_industries,
                amd_blog_releasedate=amd_blog_releasedate,
                target_audience=metadata.get("target_audience", ""),
                key_value_propositions=metadata.get("key_value_propositions", ""),
            )

            print(metadata_content)

            # replace the metadata in the markdown file
            with open(blog, "r", encoding="utf-8", errors="replace") as file:
                content = file.read()

            content = re.sub(
                r"^---\s*\n(.*?)\n---\s*\n", metadata_content, content, flags=re.DOTALL
            )

            # remove the newline at the beginning and add newline at the end of
            # content
            content = content.strip() + "\n"

            with open(blog, "w", encoding="utf-8", errors="replace") as file:
                file.write(content)

            print(f"Metadata added to {blog}")
