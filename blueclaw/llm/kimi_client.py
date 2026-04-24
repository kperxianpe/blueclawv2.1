#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kimi (Moonshot) API Client

Compatible with OpenAI API format
"""

import json
import urllib.request
from typing import List, Dict, Optional, Iterator
from dataclasses import dataclass


@dataclass
class ChatResponse:
    content: str
    model: str
    usage: Dict
    raw_response: Dict


class KimiClient:
    """
    Kimi API Client
    
    Usage:
        client = KimiClient(api_key="your-key")
        response = client.chat("Hello")
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.moonshot.cn/v1",
                 model: str = "moonshot-v1-8k"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        
    def chat(self, message: str, system: str = None, 
             temperature: float = 0.7, max_tokens: int = 2000) -> ChatResponse:
        """Send a chat message"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": message})
        
        return self.chat_messages(messages, temperature, max_tokens)
    
    def chat_messages(self, messages: List[Dict], 
                     temperature: float = 0.7,
                     max_tokens: int = 2000) -> ChatResponse:
        """Send chat messages with history"""
        url = f"{self.base_url}/chat/completions"
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                return ChatResponse(
                    content=result['choices'][0]['message']['content'],
                    model=result.get('model', self.model),
                    usage=result.get('usage', {}),
                    raw_response=result
                )
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_json = json.loads(error_body)
                error_msg = error_json.get('error', {}).get('message', error_body)
            except:
                error_msg = error_body
            raise Exception(f"Kimi API error: {error_msg}")
        except Exception as e:
            raise Exception(f"Request failed: {e}")
    
    def list_models(self) -> List[Dict]:
        """List available models"""
        url = f"{self.base_url}/models"
        
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('data', [])
