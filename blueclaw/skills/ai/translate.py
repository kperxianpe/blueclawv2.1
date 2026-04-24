#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Translate Skill

Simple text translation simulation (placeholder for real translation API).
"""

from typing import Optional
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class AITranslateSkill(Skill):
    name = "ai_translate"
    description = "翻译文本内容（演示模式，生产环境接入翻译API）"
    category = "ai"
    
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "要翻译的文本"
            },
            "target_language": {
                "type": "string",
                "enum": ["zh", "en", "ja", "ko", "fr", "de", "es"],
                "default": "en",
                "description": "目标语言代码"
            },
            "source_language": {
                "type": "string",
                "enum": ["auto", "zh", "en", "ja", "ko", "fr", "de", "es"],
                "default": "auto",
                "description": "源语言代码（auto自动检测）"
            }
        },
        "required": ["text"]
    }
    
    capabilities = {
        "can_handle": ["短文本", "单词", "简单句子"],
        "cannot_handle": ["长文档", "专业术语", "俚语"],
        "typical_use_cases": [
            "快速翻译",
            "理解外语文本",
            "多语言转换"
        ]
    }
    
    examples = [
        {
            "description": "中文转英文",
            "input": {"text": "你好，世界", "target_language": "en"},
            "output": "Hello, World"
        }
    ]
    
    # Simple dictionary for demo
    # Try to use real API if available
    _client = None
    
    def _get_client(self):
        if self._client is None:
            from ...config import Config
            from ...llm import KimiClient
            config = Config.get_llm_config()
            if config:
                self._client = KimiClient(
                    api_key=config['api_key'],
                    base_url=config.get('base_url'),
                    model=config.get('model', 'moonshot-v1-8k')
                )
        return self._client
    
    async def execute(self, text: str, target_language: str = "en",
                     source_language: str = "auto") -> SkillResult:
        if not text:
            return SkillResult(
                success=False,
                output=None,
                error_message="输入文本为空"
            )
        
        try:
            # Auto-detect source language
            if source_language == "auto":
                source_language = self._detect_language(text)
            
            # Try real API first
            client = self._get_client()
            if client:
                lang_map = {
                    "zh": "中文", "en": "English", "ja": "Japanese",
                    "ko": "Korean", "fr": "French", "de": "German", "es": "Spanish"
                }
                source_name = lang_map.get(source_language, source_language)
                target_name = lang_map.get(target_language, target_language)
                
                prompt = f"Translate the following from {source_name} to {target_name}:\n\n{text}"
                response = client.chat(prompt, temperature=0.3)
                translated = response.content.strip()
                
                return SkillResult(
                    success=True,
                    output=translated,
                    metadata={
                        "source_language": source_language,
                        "target_language": target_language,
                        "provider": "kimi",
                        "tokens_used": response.usage.get('total_tokens', 0)
                    }
                )
            
            # Fallback: mock translation
            translated = self._mock_translate(text, source_language, target_language)
            return SkillResult(
                success=True,
                output=translated,
                metadata={
                    "source_language": source_language,
                    "target_language": target_language,
                    "note": "演示模式 - 请配置 KIMI_API_KEY 使用真实翻译"
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection"""
        # Check for Chinese characters
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            return "zh"
        # Check for Japanese hiragana/katakana
        if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text):
            return "ja"
        # Check for Korean
        if any('\uac00' <= c <= '\ud7af' for c in text):
            return "ko"
        # Default to English
        return "en"
    
    def _mock_translate(self, text: str, source: str, target: str) -> str:
        """Mock translation using simple dictionary or format string"""
        # Try dictionary lookup
        if source == "zh" and target == "en":
            return self._dict_zh_en.get(text, f"[Translated to EN]: {text}")
        elif source == "en" and target == "zh":
            return self._dict_en_zh.get(text, f"[翻译为中文]: {text}")
        
        # Mock format for other language pairs
        lang_names = {
            "zh": "Chinese",
            "en": "English",
            "ja": "Japanese",
            "ko": "Korean",
            "fr": "French",
            "de": "German",
            "es": "Spanish"
        }
        
        return f"[{lang_names.get(source, source)} -> {lang_names.get(target, target)}]: {text}"
