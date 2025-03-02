def generate_grid(ROCmBlogs, blog) -> str:
    """Takes a blog and creates a sphinx grid item."""

    grid_template = """
:::{{grid-item-card}}
:padding: 1
:img-top: {image}
:class-img-top: small-sd-card-img-top
:class-body: small-sd-card
:class: small-sd-card
+++
<a href="{href}" class="small-card-header-link">
    <h2 class="card-header">{title}</h2>
</a>
<p class="paragraph">{description}</p>
<div class="date">{date} {authors_html}</div>
:::
"""

    title = blog.blog_title if hasattr(blog, "blog_title") else "No Title"

    date = blog.date.strftime("%B %d, %Y") if blog.date else "No Date"

    # Get description from myst metadata
    description = "No Description"
    if hasattr(blog, "myst") and blog.myst:
        html_meta = blog.myst.get("html_meta", {})
        if html_meta and "description lang=en" in html_meta:
            description = html_meta["description lang=en"]
    
    authors_list = getattr(blog, "author", "").split(",")

    image = blog.grab_image(ROCmBlogs)

    # Initialize authors_html
    authors_html = ""
    
    # Get author HTML if there are authors
    if authors_list:
        authors_html = blog.grab_authors(authors_list)
    
    # Only add "by" prefix if there are valid authors
    if authors_html:
        authors_html = f"by {authors_html}"

    raw_href = blog.grab_href()
    if hasattr(raw_href, "split"):
        href = "." + raw_href.split("/blogs")[-1].replace("\\", "/")
    else:
        href = "." + str(raw_href).split("/blogs")[-1].replace("\\", "/")

    return grid_template.format(
        title=title,
        date=date,
        description=description,
        authors_html=authors_html,
        image=image,
        href=href,
    )
