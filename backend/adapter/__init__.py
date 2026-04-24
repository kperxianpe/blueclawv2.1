#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adapter Module - Week 20.6
AI工具的工具，递归可组合的元工具维度
"""

from .models import (
    Adapter, AdapterType, AdapterLevel, 
    MultimodalInput, SingleConfig, BlueprintConfig, 
    BlueprintStep, AdapterAttachment, AgentConfig, AgentRef,
    adapter_registry
)
from .execution_engine import adapter_execution_engine

__all__ = [
    'Adapter', 'AdapterType', 'AdapterLevel',
    'MultimodalInput', 'SingleConfig', 'BlueprintConfig',
    'BlueprintStep', 'AdapterAttachment', 'AgentConfig', 'AgentRef',
    'adapter_registry', 'adapter_execution_engine'
]
