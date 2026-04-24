#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blueclaw Configuration

Loads API keys from .env file
"""

import os
from pathlib import Path
from typing import Optional

# Load .env file if exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)


class Config:
    """Configuration class"""
    
    # Kimi (Moonshot) - Primary
    KIMI_API_KEY: Optional[str] = os.getenv('KIMI_API_KEY')
    KIMI_BASE_URL: str = os.getenv('KIMI_BASE_URL', 'https://api.moonshot.cn/v1')
    KIMI_MODEL: str = os.getenv('KIMI_MODEL', 'moonshot-v1-8k')
    
    # OpenAI - Fallback
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    OPENAI_BASE_URL: str = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    # Claude - Optional
    ANTHROPIC_API_KEY: Optional[str] = os.getenv('ANTHROPIC_API_KEY')
    
    # Search APIs
    GOOGLE_SEARCH_API_KEY: Optional[str] = os.getenv('GOOGLE_SEARCH_API_KEY')
    BING_SEARCH_API_KEY: Optional[str] = os.getenv('BING_SEARCH_API_KEY')
    
    @classmethod
    def has_kimi(cls) -> bool:
        """Check if Kimi API key is available"""
        return cls.KIMI_API_KEY is not None and len(cls.KIMI_API_KEY) > 10
    
    @classmethod
    def has_openai(cls) -> bool:
        """Check if OpenAI API key is available"""
        return cls.OPENAI_API_KEY is not None and len(cls.OPENAI_API_KEY) > 10
    
    @classmethod
    def get_llm_config(cls) -> dict:
        """Get primary LLM configuration"""
        if cls.has_kimi():
            return {
                'api_key': cls.KIMI_API_KEY,
                'base_url': cls.KIMI_BASE_URL,
                'model': cls.KIMI_MODEL,
                'provider': 'kimi'
            }
        elif cls.has_openai():
            return {
                'api_key': cls.OPENAI_API_KEY,
                'base_url': cls.OPENAI_BASE_URL,
                'model': cls.OPENAI_MODEL,
                'provider': 'openai'
            }
        else:
            return None
    
    @classmethod
    def check_setup(cls) -> dict:
        """Check configuration status"""
        return {
            'kimi_ready': cls.has_kimi(),
            'openai_ready': cls.has_openai(),
            'llm_available': cls.has_kimi() or cls.has_openai(),
            'primary_provider': 'kimi' if cls.has_kimi() else ('openai' if cls.has_openai() else None)
        }


# Convenience function
def get_config() -> Config:
    return Config()
