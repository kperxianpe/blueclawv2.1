# -*- coding: utf-8 -*-
"""
intent_analyzer.py - 意图分析器

职责: 识别用户输入的意图类型，提取关键实体
"""

from enum import Enum, auto
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import re


class IntentType(Enum):
    """意图类型枚举"""
    TASK = "task"           # 任务型（需要规划执行）
    QUESTION = "question"   # 问答型（直接回答）
    GREETING = "greeting"   # 问候型
    CLARIFICATION = "clarification"  # 澄清回复
    COMMAND = "command"     # 直接命令


class TaskType(Enum):
    """任务类型枚举"""
    TRAVEL_PLANNING = "travel_planning"     # 旅行规划
    CODE_GENERATION = "code_generation"     # 代码生成
    DATA_ANALYSIS = "data_analysis"         # 数据分析
    FILE_OPERATION = "file_operation"       # 文件操作
    CONTENT_CREATION = "content_creation"   # 内容创作
    PROJECT_SETUP = "project_setup"         # 项目搭建
    SEARCH = "search"                       # 搜索查询
    GENERAL = "general"                     # 通用任务


@dataclass
class IntentAnalysis:
    """意图分析结果"""
    intent_type: IntentType
    task_type: Optional[TaskType] = None
    raw_input: str = ""
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    task_scope: Optional[str] = None
    confidence: float = 0.5


class IntentAnalyzer:
    """意图分析器"""
    
    # 问候语关键词
    GREETING_PATTERNS = [
        r'你好', r'您好', r'哈喽', r'嗨', r'hello', r'hi', r'hey',
        r'在吗', r'在么', r'在不在', r'有人吗'
    ]
    
    # 问答型关键词
    QUESTION_PATTERNS = [
        r'是什么', r'为什么', r'怎么做', r'如何', r'请问',
        r'什么', r'多少', r'哪里', r'哪个', r'怎样',
        r'what', r'how', r'why', r'where', r'when',
        r'can you', r'could you', r'would you',
        r'你能', r'你会', r'你可以'
    ]
    
    # 任务型关键词
    TASK_PATTERNS = [
        r'规划', r'计划', r'安排', r'帮我', r'给我', r'给我做',
        r'创建', r'生成', r'写', r'做', r'执行', r'运行',
        r'plan', r'schedule', r'create', r'generate', r'write',
        r'make', r'build', r'do', r'execute', r'run'
    ]
    
    # 命令型关键词
    COMMAND_PATTERNS = [
        r'列出', r'显示', r'打开', r'关闭', r'开始', r'停止',
        r'list', r'show', r'open', r'close', r'start', r'stop'
    ]
    
    # 任务类型识别规则
    TASK_TYPE_RULES = {
        TaskType.TRAVEL_PLANNING: [
            r'旅行', r'旅游', r'出行', r'trip', r'travel', r'vacation',
            r'酒店', r'机票', r'景点', r'行程', r'攻略'
        ],
        TaskType.CODE_GENERATION: [
            r'代码', r'程序', r'脚本', r'函数', r'类', r'算法',
            r'code', r'program', r'script', r'function', r'algorithm',
            r'python', r'javascript', r'java', r'cpp', r'c++'
        ],
        TaskType.DATA_ANALYSIS: [
            r'分析', r'统计', r'图表', r'数据', r'report',
            r'analyze', r'statistics', r'chart', r'data', r'analysis',
            r'csv', r'excel', r'json', r'database'
        ],
        TaskType.FILE_OPERATION: [
            r'文件', r'目录', r'文件夹', r'重命名', r'复制', r'移动',
            r'file', r'directory', r'folder', r'rename', r'copy', r'move'
        ],
        TaskType.CONTENT_CREATION: [
            r'文章', r'内容', r'文案', r'报告', r'邮件', r'信',
            r'article', r'content', r'email', r'letter', r'report',
            r'write about', r'draft'
        ],
        TaskType.PROJECT_SETUP: [
            r'项目', r'搭建', r'配置', r'部署', r'初始化',
            r'project', r'setup', r'configure', r'deploy', r'init'
        ],
        TaskType.SEARCH: [
            r'搜索', r'查找', r'查询', r'找找', r'搜一下',
            r'search', r'find', r'lookup', r'google', r'query'
        ]
    }
    
    def __init__(self):
        """初始化意图分析器"""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译正则表达式模式"""
        self.greeting_patterns = [re.compile(p, re.IGNORECASE) for p in self.GREETING_PATTERNS]
        self.question_patterns = [re.compile(p, re.IGNORECASE) for p in self.QUESTION_PATTERNS]
        self.task_patterns = [re.compile(p, re.IGNORECASE) for p in self.TASK_PATTERNS]
        self.command_patterns = [re.compile(p, re.IGNORECASE) for p in self.COMMAND_PATTERNS]
        
        self.task_type_patterns = {
            task_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for task_type, patterns in self.TASK_TYPE_RULES.items()
        }
    
    def analyze(self, user_input: str, context: Dict[str, Any] = None) -> IntentAnalysis:
        """
        分析用户输入意图
        
        Args:
            user_input: 用户输入文本
            context: 上下文信息（可选）
            
        Returns:
            IntentAnalysis: 意图分析结果
        """
        if not user_input or not user_input.strip():
            return IntentAnalysis(
                intent_type=IntentType.QUESTION,
                raw_input=user_input,
                confidence=0.0
            )
        
        user_input = user_input.strip()
        
        # 1. 识别意图类型
        intent_type = self._classify_intent(user_input)
        
        # 2. 如果是任务型，识别具体任务类型
        task_type = None
        if intent_type == IntentType.TASK:
            task_type = self._classify_task_type(user_input)
        
        # 3. 提取实体
        entities = self._extract_entities(user_input)
        
        # 4. 计算置信度
        confidence = self._calculate_confidence(user_input, intent_type, entities)
        
        # 5. 确定任务范围
        task_scope = self._determine_scope(user_input, task_type) if task_type else None
        
        return IntentAnalysis(
            intent_type=intent_type,
            task_type=task_type,
            raw_input=user_input,
            extracted_entities=entities,
            task_scope=task_scope,
            confidence=confidence
        )
    
    def _classify_intent(self, user_input: str) -> IntentType:
        """分类意图类型"""
        # 检查问候语
        for pattern in self.greeting_patterns:
            if pattern.search(user_input):
                return IntentType.GREETING
        
        # 检查问答型（疑问句）
        if any(pattern.search(user_input) for pattern in self.question_patterns):
            return IntentType.QUESTION
        
        # 检查命令型
        if any(pattern.search(user_input) for pattern in self.command_patterns):
            return IntentType.COMMAND
        
        # 检查任务型
        if any(pattern.search(user_input) for pattern in self.task_patterns):
            return IntentType.TASK
        
        # 默认任务型
        return IntentType.TASK
    
    def _classify_task_type(self, user_input: str) -> Optional[TaskType]:
        """分类任务类型"""
        scores = {}
        
        for task_type, patterns in self.task_type_patterns.items():
            score = sum(1 for p in patterns if p.search(user_input))
            if score > 0:
                scores[task_type] = score
        
        if not scores:
            return TaskType.GENERAL
        
        # 返回得分最高的任务类型
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _extract_entities(self, user_input: str) -> Dict[str, Any]:
        """提取关键实体"""
        entities = {}
        
        # 提取地点
        location_patterns = [
            r'去(\w+)', r'到(\w+)', r'在(\w+)',
            r'前往(\w+)', r'目的地[是为]?\s*(\w+)',
            r'to\s+(\w+)', r'in\s+(\w+)'
        ]
        for pattern in location_patterns:
            match = re.search(pattern, user_input)
            if match:
                entities['destination'] = match.group(1).strip()
                break
        
        # 提取时间
        time_patterns = [
            r'(今天|明天|后天|周末|下周|下个月)',
            r'(\d{4}年?\d{1,2}月?\d{1,2}日?)',
            r'(tomorrow|next week|next month|weekend)'
        ]
        for pattern in time_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                entities['time'] = match.group(1).strip()
                break
        
        # 提取文件
        file_patterns = [
            r'(\w+\.\w+)',  # filename.ext
            r'(\w+)文件',
            r'(\w+) file'
        ]
        for pattern in file_patterns:
            match = re.search(pattern, user_input)
            if match:
                entities['file'] = match.group(1).strip()
                break
        
        # 提取数字
        number_pattern = r'(\d+)'
        numbers = re.findall(number_pattern, user_input)
        if numbers:
            entities['numbers'] = [int(n) for n in numbers]
        
        return entities
    
    def _calculate_confidence(self, user_input: str, intent_type: IntentType, entities: Dict) -> float:
        """计算置信度"""
        score = 0.5  # 基础分
        
        # 输入长度适中加分
        length = len(user_input)
        if 10 < length < 100:
            score += 0.1
        
        # 提取到实体加分
        entity_count = len(entities)
        score += min(entity_count * 0.1, 0.3)
        
        # 明确意图加分
        if intent_type in [IntentType.GREETING, IntentType.QUESTION]:
            score += 0.2
        
        return min(score, 1.0)
    
    def _determine_scope(self, user_input: str, task_type: Optional[TaskType]) -> Optional[str]:
        """确定任务范围"""
        if task_type == TaskType.TRAVEL_PLANNING:
            if '周末' in user_input or 'weekend' in user_input.lower():
                return "weekend_trip"
            if '一周' in user_input or '7天' in user_input or 'seven days' in user_input.lower():
                return "week_long_trip"
        
        elif task_type == TaskType.CODE_GENERATION:
            if '函数' in user_input or 'function' in user_input.lower():
                return "function"
            if '类' in user_input or 'class' in user_input.lower():
                return "class"
            if '脚本' in user_input or 'script' in user_input.lower():
                return "script"
        
        return None


# 便捷函数
def analyze_intent(user_input: str, context: Dict[str, Any] = None) -> IntentAnalysis:
    """便捷函数：分析意图"""
    analyzer = IntentAnalyzer()
    return analyzer.analyze(user_input, context)
