#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Summarize Skill

Summarize text content using simple extractive methods.
"""

import re
from typing import Optional, List
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class AISummarizeSkill(Skill):
    name = "ai_summarize"
    description = "总结文本内容，提取关键信息"
    category = "ai"
    
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "要总结的文本"
            },
            "max_length": {
                "type": "integer",
                "default": 200,
                "description": "摘要最大长度（字符）"
            },
            "method": {
                "type": "string",
                "enum": ["extractive", "simple"],
                "default": "extractive",
                "description": "总结方法"
            },
            "sentences": {
                "type": "integer",
                "default": 3,
                "description": "提取句子数量（仅extractive）"
            }
        },
        "required": ["text"]
    }
    
    capabilities = {
        "can_handle": ["长文本", "文章", "报告", "会议记录"],
        "cannot_handle": ["代码", "表格数据", "非文本内容"],
        "typical_use_cases": [
            "生成文章摘要",
            "提取关键点",
            "简化长文档",
            "生成预览"
        ]
    }
    
    examples = [
        {
            "description": "总结文章",
            "input": {"text": "这是一篇很长的文章...", "max_length": 100},
            "output": "摘要: ..."
        }
    ]
    
    async def execute(self, text: str, max_length: int = 200,
                     method: str = "extractive", sentences: int = 3) -> SkillResult:
        if not text or len(text.strip()) == 0:
            return SkillResult(
                success=False,
                output=None,
                error_message="输入文本为空"
            )
        
        try:
            if method == "extractive":
                summary = self._extractive_summary(text, sentences)
            else:
                summary = self._simple_summary(text, max_length)
            
            # Truncate if exceeds max_length
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(' ', 1)[0] + "..."
            
            return SkillResult(
                success=True,
                output=summary,
                metadata={
                    "original_length": len(text),
                    "summary_length": len(summary),
                    "compression_ratio": round(len(summary) / len(text) * 100, 1),
                    "method": method
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
    
    def _extractive_summary(self, text: str, num_sentences: int) -> str:
        """Extractive summary using sentence scoring"""
        # Split into sentences
        sentences = re.split(r'[.!?。！？]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if len(sentences) <= num_sentences:
            return text
        
        # Score sentences based on word frequency
        word_freq = {}
        for sent in sentences:
            words = re.findall(r'\w+', sent.lower())
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Calculate sentence scores
        sent_scores = []
        for sent in sentences:
            words = re.findall(r'\w+', sent.lower())
            score = sum(word_freq.get(word, 0) for word in words) / max(len(words), 1)
            sent_scores.append((sent, score))
        
        # Get top sentences maintaining original order
        top_indices = sorted(
            range(len(sent_scores)),
            key=lambda i: sent_scores[i][1],
            reverse=True
        )[:num_sentences]
        top_indices.sort()
        
        summary = ' '.join(sentences[i] for i in top_indices)
        return summary
    
    def _simple_summary(self, text: str, max_length: int) -> str:
        """Simple truncation-based summary"""
        # Get first paragraph
        paragraphs = text.split('\n\n')
        first_para = paragraphs[0] if paragraphs else text
        
        if len(first_para) > max_length:
            return first_para[:max_length].rsplit(' ', 1)[0] + "..."
        
        return first_para
