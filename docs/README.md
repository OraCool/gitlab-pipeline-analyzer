# GitLab Pipeline Analyzer Documentation

This directory contains the Sphinx documentation for the GitLab Pipeline Analyzer MCP Server.

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
pip install -r requirements.txt
```

### Building HTML Documentation

To build the HTML documentation:

```bash
make html
```

The built documentation will be in `_build/html/`.

### Live Development Server

For live development with auto-reload:

```bash
make livehtml
```

This will start a development server at `http://localhost:8000` that automatically rebuilds and refreshes when you make changes.

### Other Formats

You can build documentation in other formats:

```bash
make latexpdf  # PDF via LaTeX
make epub      # EPUB
make man       # Manual pages
```

## Documentation Structure

- `index.rst` - Main documentation page with table of contents
- `installation.rst` - Installation and setup guide
- `mcp_tools.rst` - Overview of MCP tools and categories
- `tool_reference.rst` - Complete API reference for all tools
- `examples.rst` - Practical usage examples and code samples
- `configuration.rst` - Advanced configuration options
- `deployment.rst` - Production deployment strategies
- `troubleshooting.rst` - Common issues and solutions

## GitHub Pages Deployment

The documentation is automatically deployed to GitHub Pages when changes are pushed to the `main` branch. The deployment is handled by the `.github/workflows/docs.yml` workflow.

The published documentation is available at:
https://oracool.github.io/gitlab-pipeline-analyzer/

## Writing Documentation

### RestructuredText (RST) Format

The documentation uses reStructuredText format. Key syntax:

```rst
# Page Title
===============

## Section Title
----------------

### Subsection Title
~~~~~~~~~~~~~~~~~~~~

**Bold text**
*Italic text*
``Code text``

.. code-block:: python

    # Python code example
    async def example():
        return "Hello, World!"

.. note::
    This is a note admonition.

.. warning::
    This is a warning admonition.

:doc:`link-to-other-document`
```

### Cross-References

Use cross-references to link between documents:

- `:doc:`installation`` - Link to installation.rst
- `:ref:`some-label`` - Link to a labeled section
- `:meth:`module.function`` - Link to a Python method

### Code Examples

Use appropriate code-block directives:

```rst
.. code-block:: bash

    # Shell commands
    gitlab-analyzer --help

.. code-block:: python

    # Python code
    from fastmcp import Client

.. code-block:: yaml

    # YAML configuration
    key: value
```

## Customization

- `conf.py` - Sphinx configuration
- `_static/custom.css` - Custom CSS styles
- `_templates/` - Custom HTML templates (if needed)

## Contributing

When contributing to the documentation:

1. Follow the existing structure and style
2. Test your changes locally with `make html`
3. Use proper RST syntax and formatting
4. Include practical examples where appropriate
5. Update cross-references when adding new sections
