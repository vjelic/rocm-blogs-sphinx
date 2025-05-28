def create_updated_html(
    index_template,
    vertical,
    main_grid_items,
    ecosystem_grid_items,
    application_grid_items,
    software_grid_items,
):

    main_grid_str = "\n".join(main_grid_items)
    eco_grid_str = "\n".join(ecosystem_grid_items)
    app_grid_str = "\n".join(application_grid_items)
    software_grid_str = "\n".join(software_grid_items)

    eco_section = ""
    if eco_grid_str.strip():
        eco_section = """
    <div class="container">
        <h2>Ecosystems and partners</h2>
        <a href="ecosystem-partners.html">
            <button id="buttonWrapper">
                See All
            </button>
        </a>
    </div>

    ::::{grid} 1 2 3 4
    :margin 2
    {eco_grid_items}
    ::::
        """.format(
            eco_grid_items=eco_grid_str
        )

    app_section = ""
    if app_grid_str.strip():
        app_section = """
    <div class="container">
        <h2>Applications</h2>
        <a href="applications.html">
            <button id="buttonWrapper">
                See All
            </button>
        </a>
    </div>

    ::::{grid} 1 2 3 4
    :margin 2
    {application_grid_items}
    ::::
        """.format(
            application_grid_items=app_grid_str
        )

    software_section = ""
    if software_grid_str.strip():
        software_section = """
    <div class="container">
        <h2>Software</h2>
        <a href="software.html">
            <button id="buttonWrapper">
                See All
            </button>
        </a>
    </div>

    ::::{grid} 1 2 3 4
    :margin 2
    {software_grid_items}
    ::::
        """.format(
            software_grid_items=software_grid_str
        )

    updated_template = index_template

    updated_template = updated_template.replace(
        """{% if not eco_grid_items %}
{% endif %}
{% if eco_grid_items %}
    <div class="container">
        <h2>Ecosystems and partners</h2>
        <a href="ecosystem-partners.html">
            <button id="buttonWrapper">
                See All
            </button>
        </a>
    </div>
{% endif %}

::::{grid} 1 2 3 4
:margin 2
{eco_grid_items}
::::""",
        eco_section,
    )

    updated_template = updated_template.replace(
        """{% if not application_grid_items %}
{% endif %}
{% if application_grid_items %}
    <div class="container">
        <h2>Applications</h2>
        <a href="applications.html">
            <button id="buttonWrapper">
                See All
            </button>
        </a>
    </div>
{% endif %}

::::{grid} 1 2 3 4
:margin 2
{application_grid_items}
::::""",
        app_section,
    )

    updated_template = updated_template.replace(
        """{% if not software_grid_items %}
{% endif %}
{% if software_grid_items %}
    <div class="container">
        <h2>Software</h2>
        <a href="software.html">
            <button id="buttonWrapper">
                See All
            </button>
        </a>
    </div>
{% endif %}

::::{grid} 1 2 3 4
:margin 2
{software_grid_items}
::::""",
        software_section,
    )

    # Replace the standard placeholders
    updated_template = updated_template.replace(
        "{PAGE_TITLE}", f"{vertical} Blogs"
    ).replace("{grid_items}", main_grid_str)

    return updated_template
