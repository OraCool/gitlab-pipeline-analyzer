Environment Variables Configuration
===================================

The GitLab Pipeline Analyzer MCP Server supports comprehensive configuration through environment variables for database storage, server behavior, auto-cleanup, and GitLab connectivity.

.. contents::
   :local:
   :depth: 2

Overview
--------

Environment variables provide flexible configuration for different deployment scenarios:

- **Development**: Custom database paths, debug settings
- **Production**: Persistent storage, optimized cleanup intervals
- **Testing**: Isolated database locations, disabled cleanup
- **Container Deployments**: Volume-mounted storage, network configuration

Required Variables
------------------

GITLAB_URL
~~~~~~~~~~

**Purpose**: GitLab instance URL for API access

**Default**: ``https://gitlab.com``

**Examples**:

.. code-block:: bash

    # GitLab.com (public)
    export GITLAB_URL="https://gitlab.com"

    # GitLab Enterprise (self-hosted)
    export GITLAB_URL="https://gitlab.company.com"

    # GitLab with custom port
    export GITLAB_URL="https://gitlab.internal:8443"

GITLAB_TOKEN
~~~~~~~~~~~~

**Purpose**: Personal access token for GitLab API authentication

**Scope Required**: ``api`` (read access to projects, pipelines, jobs)

**Examples**:

.. code-block:: bash

    # Standard personal access token
    export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"

    # Project access token
    export GITLAB_TOKEN="glpat-abcdefghijklmnopqrst"

**Security Note**: Never commit tokens to version control. Use secure secret management.

Database Configuration
----------------------

MCP_DATABASE_PATH
~~~~~~~~~~~~~~~~~

**Purpose**: SQLite database file location for analysis cache

**Default**: ``analysis_cache.db`` (in current working directory)

**Examples**:

.. code-block:: bash

    # Absolute path
    export MCP_DATABASE_PATH="/var/lib/gitlab-analyzer/cache.db"

    # User data directory
    export MCP_DATABASE_PATH="$HOME/.local/share/gitlab-analyzer/analysis_cache.db"

    # Temporary location (testing)
    export MCP_DATABASE_PATH="/tmp/gitlab_analyzer_test.db"

    # Container volume
    export MCP_DATABASE_PATH="/data/analysis_cache.db"

**Use Cases**:

- **Development**: ``./dev_cache.db``
- **Production**: ``/var/lib/gitlab-analyzer/production_cache.db``
- **Testing**: ``/tmp/test_cache_${TEST_ID}.db``
- **Docker**: ``/data/analysis_cache.db`` with volume mount

Auto-Cleanup Configuration
--------------------------

MCP_AUTO_CLEANUP_ENABLED
~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Enable/disable automatic cache cleanup

**Default**: ``true``

**Values**: ``true`` | ``false``

**Examples**:

.. code-block:: bash

    # Enable automatic cleanup (default)
    export MCP_AUTO_CLEANUP_ENABLED="true"

    # Disable automatic cleanup
    export MCP_AUTO_CLEANUP_ENABLED="false"

**When to Disable**:
- Development/debugging environments
- Systems with manual maintenance schedules
- High-frequency analysis scenarios

MCP_AUTO_CLEANUP_INTERVAL_MINUTES
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Time interval between automatic cleanup checks

**Default**: ``60`` (1 hour)

**Range**: ``1`` to ``10080`` (1 week)

**Examples**:

.. code-block:: bash

    # Check every 30 minutes
    export MCP_AUTO_CLEANUP_INTERVAL_MINUTES="30"

    # Check every 6 hours
    export MCP_AUTO_CLEANUP_INTERVAL_MINUTES="360"

    # Check daily
    export MCP_AUTO_CLEANUP_INTERVAL_MINUTES="1440"

**Considerations**:
- **Lower values**: More frequent cleanup, higher CPU usage
- **Higher values**: Less frequent cleanup, more storage usage
- **Recommended**: 60-360 minutes for most deployments

MCP_AUTO_CLEANUP_MAX_AGE_HOURS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Maximum age of cache entries before cleanup

**Default**: ``24`` (24 hours)

**Range**: ``1`` to ``8760`` (1 year)

**Examples**:

.. code-block:: bash

    # Clean entries older than 12 hours
    export MCP_AUTO_CLEANUP_MAX_AGE_HOURS="12"

    # Clean entries older than 7 days
    export MCP_AUTO_CLEANUP_MAX_AGE_HOURS="168"

    # Clean entries older than 30 days
    export MCP_AUTO_CLEANUP_MAX_AGE_HOURS="720"

**Tuning Guidelines**:
- **Active development**: 12-24 hours
- **Production monitoring**: 168-720 hours (1-4 weeks)
- **Archival systems**: 2160+ hours (3+ months)

Server Configuration
--------------------

MCP_TRANSPORT
~~~~~~~~~~~~~

**Purpose**: MCP server transport protocol

**Default**: ``stdio``

**Values**: ``stdio`` | ``http`` | ``sse``

**Examples**:

.. code-block:: bash

    # STDIO transport (default, for Claude Desktop)
    export MCP_TRANSPORT="stdio"

    # HTTP transport (for web applications)
    export MCP_TRANSPORT="http"

    # SSE transport (for real-time streaming)
    export MCP_TRANSPORT="sse"

**Transport Selection**:
- **stdio**: Local integrations, Claude Desktop, command-line tools
- **http**: Web applications, REST API consumers, remote access
- **sse**: Real-time applications, streaming updates, live dashboards

MCP_HOST
~~~~~~~~

**Purpose**: Server bind address (HTTP/SSE transports only)

**Default**: ``127.0.0.1``

**Examples**:

.. code-block:: bash

    # Localhost only (default)
    export MCP_HOST="127.0.0.1"

    # All interfaces (container/network access)
    export MCP_HOST="0.0.0.0"

    # Specific interface
    export MCP_HOST="192.168.1.10"

**Security Considerations**:
- **127.0.0.1**: Secure for local-only access
- **0.0.0.0**: Required for container/network access, ensure firewall protection
- **Specific IP**: Bind to particular network interface

MCP_PORT
~~~~~~~~

**Purpose**: Server port number (HTTP/SSE transports only)

**Default**: ``8000``

**Range**: ``1024`` to ``65535`` (unprivileged ports)

**Examples**:

.. code-block:: bash

    # Default port
    export MCP_PORT="8000"

    # Alternative port
    export MCP_PORT="9000"

    # Production port
    export MCP_PORT="80"   # Requires root/capabilities

MCP_PATH
~~~~~~~~

**Purpose**: URL path prefix for HTTP endpoints

**Default**: ``/mcp``

**Examples**:

.. code-block:: bash

    # Default path
    export MCP_PATH="/mcp"

    # Custom path
    export MCP_PATH="/api/gitlab-analyzer"

    # Root path
    export MCP_PATH="/"

Debug Configuration
-------------------

MCP_DEBUG_LEVEL
~~~~~~~~~~~~~~~

**Purpose**: Control debug output verbosity for troubleshooting

**Default**: ``0`` (no debug output)

**Values**: ``0`` | ``1`` | ``2`` | ``3``

**Examples**:

.. code-block:: bash

    # No debug output (default)
    export MCP_DEBUG_LEVEL="0"

    # Basic debug messages
    export MCP_DEBUG_LEVEL="1"

    # Verbose debug messages
    export MCP_DEBUG_LEVEL="2"

    # Very verbose debug messages
    export MCP_DEBUG_LEVEL="3"

**Debug Levels**:
- **0**: No debug output (production default)
- **1**: Basic debug messages (connection info, major operations)
- **2**: Verbose debug messages (includes API calls, cache operations)
- **3**: Very verbose debug messages (includes detailed internal state)

**Usage Guidelines**:
- **Development**: Use levels 1-2 for development and debugging
- **Production**: Keep at 0 unless troubleshooting issues
- **Troubleshooting**: Use level 3 for detailed issue investigation
- **Performance**: Higher levels may impact performance in busy environments

**Security Note**: Debug output may contain sensitive information. Use carefully in production.

Configuration Examples
----------------------

Development Environment
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # .env.dev
    GITLAB_URL="https://gitlab.company.com"
    GITLAB_TOKEN="glpat-development-token"

    # Development database
    MCP_DATABASE_PATH="./dev_cache.db"

    # Frequent cleanup for active development
    MCP_AUTO_CLEANUP_ENABLED="true"
    MCP_AUTO_CLEANUP_INTERVAL_MINUTES="30"
    MCP_AUTO_CLEANUP_MAX_AGE_HOURS="12"

    # STDIO transport for Claude Desktop
    MCP_TRANSPORT="stdio"

    # Enable debug output for development
    MCP_DEBUG_LEVEL="1"

Production Environment
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # .env.prod
    GITLAB_URL="https://gitlab.company.com"
    GITLAB_TOKEN="glpat-production-token"

    # Persistent production database
    MCP_DATABASE_PATH="/var/lib/gitlab-analyzer/production_cache.db"

    # Conservative cleanup for production
    MCP_AUTO_CLEANUP_ENABLED="true"
    MCP_AUTO_CLEANUP_INTERVAL_MINUTES="360"  # 6 hours
    MCP_AUTO_CLEANUP_MAX_AGE_HOURS="168"     # 7 days

    # HTTP transport for web access
    MCP_TRANSPORT="http"
    MCP_HOST="0.0.0.0"
    MCP_PORT="8000"
    MCP_PATH="/mcp"

Testing Environment
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # .env.test
    GITLAB_URL="https://gitlab-test.company.com"
    GITLAB_TOKEN="glpat-test-token"

    # Isolated test database
    MCP_DATABASE_PATH="/tmp/test_cache_${CI_JOB_ID}.db"

    # Disable cleanup during tests
    MCP_AUTO_CLEANUP_ENABLED="false"

    # Test-specific transport
    MCP_TRANSPORT="stdio"

Docker Deployment
~~~~~~~~~~~~~~~~~

.. code-block:: dockerfile

    # Dockerfile environment
    ENV GITLAB_URL="https://gitlab.company.com"
    # GITLAB_TOKEN set via secrets/runtime

    ENV MCP_DATABASE_PATH="/data/analysis_cache.db"
    ENV MCP_AUTO_CLEANUP_ENABLED="true"
    ENV MCP_AUTO_CLEANUP_INTERVAL_MINUTES="240"  # 4 hours
    ENV MCP_AUTO_CLEANUP_MAX_AGE_HOURS="336"     # 14 days

    ENV MCP_TRANSPORT="http"
    ENV MCP_HOST="0.0.0.0"
    ENV MCP_PORT="8000"
    ENV MCP_PATH="/mcp"

    VOLUME ["/data"]
    EXPOSE 8000

.. code-block:: yaml

    # docker-compose.yml
    version: '3.8'
    services:
      gitlab-analyzer:
        image: gitlab-analyzer:latest
        environment:
          - GITLAB_URL=https://gitlab.company.com
          - GITLAB_TOKEN=${GITLAB_TOKEN}
          - MCP_DATABASE_PATH=/data/analysis_cache.db
          - MCP_AUTO_CLEANUP_ENABLED=true
          - MCP_AUTO_CLEANUP_INTERVAL_MINUTES=240
          - MCP_AUTO_CLEANUP_MAX_AGE_HOURS=336
          - MCP_TRANSPORT=http
          - MCP_HOST=0.0.0.0
          - MCP_PORT=8000
        ports:
          - "8000:8000"
        volumes:
          - gitlab_data:/data

    volumes:
      gitlab_data:

Environment Variable Priority
-----------------------------

When multiple configuration methods are available:

1. **Command-line arguments** (highest priority)
2. **Environment variables**
3. **Configuration files** (.env files)
4. **Default values** (lowest priority)

**Example**:

.. code-block:: bash

    # Environment variable
    export MCP_PORT="9000"

    # Command-line override (takes precedence)
    gitlab-analyzer --port 8080

Validation and Troubleshooting
------------------------------

Environment Check
~~~~~~~~~~~~~~~~~

Use the built-in environment validation:

.. code-block:: bash

    # Check all environment variables
    make check-env

    # Manual check
    env | grep -E "(GITLAB|MCP)_"

Common Issues
~~~~~~~~~~~~~

**Database Permission Errors**:

.. code-block:: bash

    # Ensure directory exists and is writable
    mkdir -p "$(dirname "$MCP_DATABASE_PATH")"
    touch "$MCP_DATABASE_PATH"

**Port Conflicts**:

.. code-block:: bash

    # Check if port is available
    netstat -ln | grep ":$MCP_PORT"

    # Use alternative port
    export MCP_PORT="9000"

**Token Validation**:

.. code-block:: bash

    # Test GitLab token
    curl -H "Authorization: Bearer $GITLAB_TOKEN" \
         "$GITLAB_URL/api/v4/user"

Best Practices
--------------

Security
~~~~~~~~

- **Never commit tokens** to version control
- **Use secret management** for production tokens
- **Rotate tokens** regularly
- **Limit token scope** to minimum required permissions
- **Use environment-specific tokens** (dev/test/prod)

Performance
~~~~~~~~~~~

- **Monitor database size** and adjust cleanup intervals
- **Use persistent storage** for production deployments
- **Set appropriate cleanup age** based on usage patterns
- **Choose optimal transport** for your use case

Maintenance
~~~~~~~~~~~

- **Regular token rotation** (quarterly/annually)
- **Monitor cleanup effectiveness** via cache_stats
- **Backup important databases** before major updates
- **Test configuration changes** in non-production environments
