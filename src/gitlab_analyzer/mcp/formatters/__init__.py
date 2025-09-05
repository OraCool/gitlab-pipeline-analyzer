"""
MCP Formatters Package

This package contains formatting utilities for different response modes.
Formatters are responsible for presenting data in user-friendly formats based on
the requested analysis mode (minimal, balanced, detailed, fixing).

Formatters follow SOLID principles:
- Single Responsibility: Each formatter handles one type of data
- Open/Closed: Easy to add new formatting modes
- Interface Segregation: Specific formatters for specific data types
"""
