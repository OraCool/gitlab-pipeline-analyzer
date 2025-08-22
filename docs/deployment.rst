Deployment Guide
================

This guide covers deploying the GitLab Pipeline Analyzer MCP Server for different use cases.

.. contents::
   :local:
   :depth: 2

Deployment Overview
-------------------

The GitLab Pipeline Analyzer MCP Server can be deployed in several ways:

- **Local Development** - Direct Python execution for development and testing
- **Remote HTTP Server** - HTTP transport for team sharing and web integration
- **Process Management** - Using process managers for long-running deployments

Local Development
-----------------

For development, testing, and personal use with Claude Desktop:

.. code-block:: bash

    # Install in development mode
    git clone https://github.com/OraCool/gitlab-pipeline-analyzer.git
    cd gitlab-pipeline-analyzer
    uv sync --all-extras

    # Set environment variables
    export GITLAB_URL="https://gitlab.com"
    export GITLAB_TOKEN="your-token"

    # Run with STDIO transport (default)
    uv run gitlab-analyzer

This is ideal for:
- Local development and testing
- Claude Desktop integration
- Personal automation scripts

Remote HTTP Server
------------------

For team sharing and web application integration:

Basic HTTP Server
~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Run HTTP server accessible from network
    uv run gitlab-analyzer --transport http --host 0.0.0.0 --port 8000

The server will be available at: ``http://your-server:8000/mcp``

Background Execution
~~~~~~~~~~~~~~~~~~~~

To run the server in the background:

.. code-block:: bash

    # Using nohup (Linux/macOS)
    nohup uv run gitlab-analyzer --transport http --host 0.0.0.0 --port 8000 > analyzer.log 2>&1 &

    # Using screen (Linux/macOS)
    screen -S gitlab-analyzer
    uv run gitlab-analyzer --transport http --host 0.0.0.0 --port 8000
    # Press Ctrl+A then D to detach

Process Management
------------------

For production-like deployments where you need the server to restart automatically:

Using systemd (Linux)
~~~~~~~~~~~~~~~~~~~~~~

Create a systemd service file ``/etc/systemd/system/gitlab-analyzer.service``:

.. code-block:: ini

    [Unit]
    Description=GitLab Pipeline Analyzer MCP Server
    After=network.target

    [Service]
    Type=simple
    User=your-username
    WorkingDirectory=/path/to/gitlab-pipeline-analyzer
    Environment=GITLAB_URL=https://gitlab.com
    Environment=GITLAB_TOKEN=your-token
    ExecStart=/path/to/uv run gitlab-analyzer --transport http --host 0.0.0.0 --port 8000
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target

Enable and start the service:

.. code-block:: bash

    sudo systemctl enable gitlab-analyzer
    sudo systemctl start gitlab-analyzer
    sudo systemctl status gitlab-analyzer

Using pm2 (Cross-platform)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have Node.js and pm2 installed:

.. code-block:: bash

    # Install pm2 if not already installed
    npm install -g pm2

    # Create ecosystem file
    cat > ecosystem.config.js << EOF
    module.exports = {
      apps: [{
        name: 'gitlab-analyzer',
        script: 'uv',
        args: 'run gitlab-analyzer --transport http --host 0.0.0.0 --port 8000',
        cwd: '/path/to/gitlab-pipeline-analyzer',
        env: {
          GITLAB_URL: 'https://gitlab.com',
          GITLAB_TOKEN: 'your-token'
        },
        restart_delay: 10000,
        max_restarts: 10
      }]
    };
    EOF

    # Start the application
    pm2 start ecosystem.config.js
    pm2 save
    pm2 startup

Security Considerations
-----------------------

Token Security
~~~~~~~~~~~~~~~

**Environment Variables:**
- Never hardcode tokens in scripts or configuration files
- Use environment variables or secure credential management
- Regularly rotate your GitLab tokens

**Network Security:**
- For HTTP transport, consider using a reverse proxy with HTTPS
- Restrict access to the MCP server port using firewall rules
- Use VPN or private networks for sensitive GitLab instances

**File Permissions:**
- Ensure ``.env`` files have restricted permissions (``chmod 600 .env``)
- Run the server with minimal required privileges

Reverse Proxy Setup
~~~~~~~~~~~~~~~~~~~~

For HTTPS and additional security, use nginx or similar:

.. code-block:: nginx

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate /path/to/certificate.crt;
        ssl_certificate_key /path/to/private.key;

        location /mcp/ {
            proxy_pass http://127.0.0.1:8000/mcp/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

Monitoring and Maintenance
--------------------------

Health Checks
~~~~~~~~~~~~~

For HTTP transport, you can check server health:

.. code-block:: bash

    # Simple health check
    curl -f http://localhost:8000/mcp || echo "Server is down"

Log Management
~~~~~~~~~~~~~~

The server uses FastMCP's logging capabilities. For production deployments:

.. code-block:: bash

    # Redirect logs to file
    uv run gitlab-analyzer --transport http --host 0.0.0.0 --port 8000 > /var/log/gitlab-analyzer.log 2>&1

    # Use logrotate for log management
    sudo tee /etc/logrotate.d/gitlab-analyzer << EOF
    /var/log/gitlab-analyzer.log {
        daily
        rotate 30
        compress
        delaycompress
        missingok
        notifempty
        create 644 your-username your-username
    }
    EOF

Performance Tuning
~~~~~~~~~~~~~~~~~~~

For high-traffic deployments:

1. **Multiple Instances**: Run multiple server instances on different ports and use a load balancer
2. **Resource Limits**: Monitor memory and CPU usage
3. **GitLab API Limits**: Be aware of GitLab API rate limits and implement appropriate delays

.. code-block:: bash

    # Run multiple instances
    uv run gitlab-analyzer --transport http --host 0.0.0.0 --port 8000 &
    uv run gitlab-analyzer --transport http --host 0.0.0.0 --port 8001 &
    uv run gitlab-analyzer --transport http --host 0.0.0.0 --port 8002 &

Troubleshooting Deployment
--------------------------

Common Deployment Issues
~~~~~~~~~~~~~~~~~~~~~~~~

**Port Already in Use:**

.. code-block:: bash

    # Check what's using the port
    lsof -i :8000

    # Use a different port
    uv run gitlab-analyzer --transport http --port 8001

**Server Not Accessible:**

- Check firewall settings
- Verify the host binding (use ``0.0.0.0`` for external access)
- Ensure the port is not blocked

**Server Crashes:**

- Check logs for error messages
- Verify GitLab token is valid and has correct permissions
- Ensure network connectivity to GitLab instance

**High Memory Usage:**

- Monitor for memory leaks
- Restart the server periodically if needed
- Consider processing limits for large pipelines

For detailed troubleshooting, see :doc:`troubleshooting`.

Next Steps
----------

- Review :doc:`configuration` for advanced configuration options
- Check :doc:`troubleshooting` for common issues and solutions
- See :doc:`examples` for usage examples with different clients
