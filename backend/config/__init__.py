#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration module
"""

import os

# Server configuration
SERVER_HOST = os.environ.get('SERVER_HOST', 'localhost')
SERVER_PORT = int(os.environ.get('SERVER_PORT', '8000'))

# WebSocket settings
WS_CONFIG = {
    'ping_interval': 20,
    'ping_timeout': 10,
    'close_timeout': 10,
    'max_size': 10 * 1024 * 1024,  # 10MB
    'max_queue': 32,
    'compression': True,
}

# Task settings
TASK_CONFIG = {
    'max_concurrent_tasks': 100,
    'max_tasks_per_connection': 10,
    'max_task_duration': 3600,  # 1 hour
    'checkpoint_interval': 30,
    'cleanup_interval': 300,
    'task_ttl': 86400,  # 24 hours
    'max_retries': 3,
    'retry_delay': 1.0,
}

# Checkpoint settings
CHECKPOINT_CONFIG = {
    'storage_dir': os.environ.get('CHECKPOINT_DIR', './checkpoints'),
    'batch_interval': 5,
    'compression': True,
    'max_checkpoints': 1000,
}

# Performance settings
PERFORMANCE_CONFIG = {
    'use_orjson': True,
    'connection_pool_size': 10,
    'message_workers': 4,
    'enable_metrics': True,
}
