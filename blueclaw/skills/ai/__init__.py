#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI skills module"""

from .summarize import AISummarizeSkill
from .translate import AITranslateSkill
from .describe_image import AIDescribeImageSkill

__all__ = ['AISummarizeSkill', 'AITranslateSkill', 'AIDescribeImageSkill']
