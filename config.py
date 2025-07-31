"""
Configuration settings for GitLab Pipeline Analyzer MCP Server
"""

import os
from typing import Optional


class Config:
    """Configuration class for GitLab settings"""
    
    def __init__(self) -> None:
        self.gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
        self.gitlab_token = os.getenv("GITLAB_TOKEN")
        
        # Validation
        if not self.gitlab_token:
            raise ValueError(
                "GITLAB_TOKEN environment variable is required. "
                "Please set it in your .env file or environment."
            )
    
    @property
    def is_configured(self) -> bool:
        """Check if all required configuration is present"""
        return bool(self.gitlab_token)
    
    def get_api_url(self) -> str:
        """Get the GitLab API URL"""
        return f"{self.gitlab_url.rstrip('/')}/api/v4"
    
    def get_headers(self) -> dict:
        """Get HTTP headers for GitLab API requests"""
        return {
            "Authorization": f"Bearer {self.gitlab_token}",
            "Content-Type": "application/json"
        }


def load_env_file(env_path: str = ".env") -> None:
    """Load environment variables from .env file"""
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('\'"')
                    os.environ[key] = value
