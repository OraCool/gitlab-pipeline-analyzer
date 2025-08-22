Troubleshooting Guide
=====================

This guide helps you diagnose and resolve common issues with the GitLab Pipeline Analyzer MCP Server.

.. contents::
   :local:
   :depth: 2

Common Issues
-------------

Connection Problems
~~~~~~~~~~~~~~~~~~~

**Issue: Cannot connect to GitLab instance**

.. code-block:: text

    Error: Failed to connect to GitLab API
    ConnectionError: HTTPSConnectionPool(host='gitlab.company.com', port=443)

**Diagnosis:**

.. code-block:: bash

    # Test basic connectivity
    curl -I https://gitlab.company.com

    # Test API connectivity
    curl -H "Authorization: Bearer $GITLAB_TOKEN" "https://gitlab.company.com/api/v4/projects"

    # Check DNS resolution
    nslookup gitlab.company.com

**Solutions:**

1. **Network connectivity:**

   .. code-block:: bash

       # Check firewall rules
       sudo iptables -L

       # Test with proxy if needed
       export HTTP_PROXY="http://proxy.company.com:8080"
       export HTTPS_PROXY="http://proxy.company.com:8080"

2. **SSL certificate issues:**

   .. code-block:: bash

       # For self-signed certificates
       export REQUESTS_CA_BUNDLE="/path/to/ca-bundle.crt"
       export SSL_CERT_FILE="/path/to/ca-bundle.crt"

3. **DNS and routing:**

   .. code-block:: bash

       # Add to /etc/hosts if needed
       echo "192.168.1.100 gitlab.company.com" | sudo tee -a /etc/hosts

**Issue: MCP transport connection fails**

.. code-block:: text

    Error: Cannot bind to address 127.0.0.1:8000
    OSError: [Errno 98] Address already in use

**Solutions:**

.. code-block:: bash

    # Check what's using the port
    lsof -i :8000
    netstat -tlnp | grep :8000

    # Use a different port
    gitlab-analyzer --transport http --port 8001

    # Kill existing process if safe to do so
    sudo kill $(lsof -t -i:8000)

Authentication Issues
~~~~~~~~~~~~~~~~~~~~~

**Issue: GitLab token authentication fails**

.. code-block:: text

    Error: 401 Unauthorized
    GitLab API authentication failed

**Diagnosis:**

.. code-block:: bash

    # Test token directly
    curl -H "Authorization: Bearer $GITLAB_TOKEN" \
         "$GITLAB_URL/api/v4/user" | jq '.'

    # Check token scopes
    curl -H "Authorization: Bearer $GITLAB_TOKEN" \
         "$GITLAB_URL/api/v4/personal_access_tokens" | jq '.'

**Solutions:**

1. **Verify token:**

   - Go to GitLab → User Settings → Access Tokens
   - Ensure token has ``api`` and ``read_repository`` scopes
   - Check token expiration date
   - Regenerate token if needed

2. **Check token format:**

   .. code-block:: bash

       # Token should start with glpat- for GitLab
       echo $GITLAB_TOKEN | grep -E '^glpat-'

3. **Update token:**

   .. code-block:: bash

       # Update environment variable
       export GITLAB_TOKEN="glpat-new-token-here"

       # Or update .env file
       echo "GITLAB_TOKEN=glpat-new-token-here" > .env

**Issue: Token has insufficient permissions**

.. code-block:: text

    Error: 403 Forbidden
    Insufficient permissions to access project

**Solutions:**

1. **Check project access:**

   .. code-block:: bash

       # Test project access
       curl -H "Authorization: Bearer $GITLAB_TOKEN" \
            "$GITLAB_URL/api/v4/projects/$PROJECT_ID"

2. **Request access:**

   - Ensure you're a member of the project
   - Request Developer role or higher
   - For group-owned projects, check group membership

Performance Issues
~~~~~~~~~~~~~~~~~~

**Issue: Slow response times**

**Diagnosis:**

.. code-block:: bash

    # Time GitLab API calls
    time curl -H "Authorization: Bearer $GITLAB_TOKEN" \
              "$GITLAB_URL/api/v4/projects/$PROJECT_ID/pipelines"

**Solutions:**

1. **Check GitLab instance performance:**

   - Verify GitLab server isn't overloaded
   - Check network latency to GitLab instance
   - Consider GitLab API rate limits

2. **Optimize requests:**

   - Use specific project IDs instead of searching
   - Limit data requests to necessary fields
   - Consider caching for repeated requests

**Issue: High memory usage**

**Diagnosis:**

.. code-block:: bash

    # Monitor memory usage
    ps aux | grep gitlab-analyzer
    top -p $(pgrep gitlab-analyzer)

**Solutions:**

1. **Limit processing:**

   - Process smaller pipelines
   - Use pagination for large result sets
   - Restart server periodically if needed

2. **System resources:**

   .. code-block:: bash

       # Check available memory
       free -h

       # Monitor swap usage
       swapon --show

Parsing Issues
~~~~~~~~~~~~~~

**Issue: Cannot parse job logs**

.. code-block:: text

    Error: Failed to parse job trace
    No parseable content found

**Diagnosis:**

.. code-block:: bash

    # Check job trace directly
    curl -H "Authorization: Bearer $GITLAB_TOKEN" \
         "$GITLAB_URL/api/v4/projects/$PROJECT_ID/jobs/$JOB_ID/trace"

**Solutions:**

1. **Verify job has trace:**

   - Check that job has completed
   - Ensure job generated output
   - Verify job trace isn't empty

2. **Check trace format:**

   - Server supports pytest and generic log formats
   - Ensure logs contain recognizable error patterns
   - Check for ANSI color codes that might interfere

**Issue: Incorrect error extraction**

**Solutions:**

1. **Use appropriate parser:**

   - Use pytest tools for Python test jobs
   - Use generic log tools for other job types
   - Check tool descriptions for best fit

2. **Verify log content:**

   - Ensure error messages are in expected format
   - Check for truncated logs
   - Verify complete error traces are available

Configuration Issues
~~~~~~~~~~~~~~~~~~~~

**Issue: Environment variables not loaded**

.. code-block:: text

    Error: GITLAB_TOKEN environment variable not set

**Solutions:**

1. **Check environment:**

   .. code-block:: bash

       # Verify variables are set
       env | grep GITLAB
       echo "URL: $GITLAB_URL"
       echo "Token: ${GITLAB_TOKEN:0:10}..."

2. **Load .env file:**

   .. code-block:: bash

       # Source .env file manually
       source .env

       # Or use with command
       env $(cat .env | xargs) gitlab-analyzer

3. **Check file permissions:**

   .. code-block:: bash

       # Verify .env file permissions
       ls -la .env

       # Fix permissions if needed
       chmod 600 .env

**Issue: Wrong GitLab URL**

.. code-block:: text

    Error: Name or service not known

**Solutions:**

.. code-block:: bash

    # Verify URL format
    echo $GITLAB_URL

    # Should be like: https://gitlab.com or https://gitlab.company.com
    # No trailing slash
    export GITLAB_URL="https://gitlab.company.com"

Server Issues
-------------

**Issue: Server won't start**

**Diagnosis:**

.. code-block:: bash

    # Run with verbose output
    uv run gitlab-analyzer --transport stdio

    # Check Python environment
    which python
    python --version
    uv --version

**Solutions:**

1. **Check dependencies:**

   .. code-block:: bash

       # Reinstall dependencies
       uv sync --all-extras

       # Or with pip
       pip install -e .

2. **Python environment:**

   .. code-block:: bash

       # Ensure Python 3.10+
       python --version

       # Check import works
       python -c "import gitlab_analyzer"

**Issue: Server crashes during operation**

**Diagnosis:**

.. code-block:: bash

    # Run server and check output
    gitlab-analyzer --transport http --port 8000

    # Check system resources
    df -h  # Disk space
    free -h  # Memory

**Solutions:**

1. **Check logs:**

   - Review FastMCP output for error messages
   - Look for Python tracebacks
   - Check for out-of-memory errors

2. **Resource management:**

   .. code-block:: bash

       # Monitor resource usage
       htop

       # Restart server if needed
       pkill -f gitlab-analyzer
       gitlab-analyzer --transport http --port 8000

**Issue: HTTP transport not accessible**

.. code-block:: text

    Error: Connection refused (http://localhost:8000/mcp)

**Solutions:**

1. **Check server binding:**

   .. code-block:: bash

       # For external access, use 0.0.0.0
       gitlab-analyzer --transport http --host 0.0.0.0 --port 8000

       # Check if server is listening
       netstat -tlnp | grep :8000

2. **Firewall configuration:**

   .. code-block:: bash

       # Allow port through firewall (Ubuntu/Debian)
       sudo ufw allow 8000

       # CentOS/RHEL
       sudo firewall-cmd --permanent --add-port=8000/tcp
       sudo firewall-cmd --reload

Client Issues
-------------

**Issue: Claude Desktop can't connect**

**Solutions:**

1. **Check configuration:**

   Verify ``claude_desktop_config.json``:

   .. code-block:: json

       {
         "mcpServers": {
           "gitlab-pipeline-analyzer": {
             "command": "uv",
             "args": ["run", "gitlab-analyzer"],
             "env": {
               "GITLAB_URL": "https://gitlab.com",
               "GITLAB_TOKEN": "your-token-here"
             }
           }
         }
       }

2. **Test manually:**

   .. code-block:: bash

       # Test the exact command Claude Desktop would run
       uv run gitlab-analyzer

**Issue: HTTP client connection problems**

**Solutions:**

1. **Test endpoint:**

   .. code-block:: bash

       # Test MCP endpoint
       curl -X POST http://localhost:8000/mcp \
            -H "Content-Type: application/json" \
            -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

2. **Check CORS (if needed):**

   For browser clients, ensure CORS is handled by your reverse proxy or client configuration.

Debugging Tools
---------------

Server Diagnostics
~~~~~~~~~~~~~~~~~~

**Environment Check:**

.. code-block:: bash

    # Check all relevant environment variables
    env | grep -E "(GITLAB|MCP)_"

    # Verify GitLab connectivity
    curl -I "$GITLAB_URL"

    # Test token
    curl -H "Authorization: Bearer $GITLAB_TOKEN" \
         "$GITLAB_URL/api/v4/user"

**Manual Testing:**

.. code-block:: bash

    # Test individual components
    python -c "
    import os
    from gitlab_analyzer.api.client import GitLabClient

    client = GitLabClient(
        url=os.environ['GITLAB_URL'],
        token=os.environ['GITLAB_TOKEN']
    )

    # Test connection
    user = client.get_current_user()
    print(f'Connected as: {user.name}')
    "

Log Analysis
~~~~~~~~~~~~

**Server Output:**

FastMCP provides built-in logging. Monitor server output for:

- Connection attempts
- Authentication status
- Request processing
- Error messages

**System Logs:**

.. code-block:: bash

    # Check system logs for errors
    journalctl -u gitlab-analyzer  # If using systemd

    # Check for Python errors
    dmesg | grep python

**GitLab API Debugging:**

.. code-block:: bash

    # Test API calls manually
    curl -v -H "Authorization: Bearer $GITLAB_TOKEN" \
         "$GITLAB_URL/api/v4/projects/$PROJECT_ID/pipelines/$PIPELINE_ID"

Network Debugging
~~~~~~~~~~~~~~~~~

**Connectivity Tests:**

.. code-block:: bash

    # Test basic connectivity
    ping gitlab.company.com

    # Test SSL
    openssl s_client -connect gitlab.company.com:443

    # Test with specific IP
    curl -H "Host: gitlab.company.com" http://192.168.1.100

**Proxy Configuration:**

.. code-block:: bash

    # Test with proxy
    curl --proxy http://proxy.company.com:8080 \
         -H "Authorization: Bearer $GITLAB_TOKEN" \
         "$GITLAB_URL/api/v4/user"

Performance Monitoring
----------------------

Resource Monitoring
~~~~~~~~~~~~~~~~~~~

**System Resources:**

.. code-block:: bash

    # Monitor CPU and memory
    top -p $(pgrep gitlab-analyzer)

    # Check disk usage
    df -h

    # Monitor network
    netstat -i

**Application Performance:**

.. code-block:: bash

    # Time API calls
    time curl -H "Authorization: Bearer $GITLAB_TOKEN" \
              "$GITLAB_URL/api/v4/projects"

    # Monitor request rates
    watch -n 1 'netstat -an | grep :8000 | wc -l'

Getting Help
------------

**Community Support:**

- Check project documentation: :doc:`index`
- Review configuration guide: :doc:`configuration`
- See examples: :doc:`examples`

**Issue Reporting:**

When reporting issues, include:

1. **Environment information:**

   .. code-block:: bash

       python --version
       uv --version
       gitlab-analyzer --version  # If server starts

2. **Configuration (sanitized):**

   .. code-block:: bash

       # Don't include actual tokens!
       echo "GITLAB_URL: $GITLAB_URL"
       echo "Token set: $([ -n "$GITLAB_TOKEN" ] && echo "Yes" || echo "No")"

3. **Error messages and logs**
4. **Steps to reproduce the issue**

**Self-Diagnosis Checklist:**

- [ ] GitLab token has correct permissions
- [ ] Network connectivity to GitLab instance works
- [ ] Environment variables are properly set
- [ ] Server starts without errors
- [ ] Can make basic GitLab API calls manually
- [ ] Firewall allows necessary ports (for HTTP transport)
- [ ] Python environment has all dependencies installed
