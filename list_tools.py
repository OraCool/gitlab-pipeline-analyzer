#!/usr/bin/env python3
"""
Simple script to list available MCP tools
"""

import json

# Messages to send to MCP server
messages = [
    # 1. Initialize
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    },
    # 2. Initialize complete notification
    {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    },
    # 3. List tools
    {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
]

# Print messages for piping to MCP server
for msg in messages:
    print(json.dumps(msg))
