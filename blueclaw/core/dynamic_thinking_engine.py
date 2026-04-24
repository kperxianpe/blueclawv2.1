# -*- coding: utf-8 -*-
"""
dynamic_thinking_engine.py - Blueclaw v1.0 动态思考引擎

80%场景0-1次选择目标：
- 高置信度(>0.85): 直接生成执行预览
- 中置信度+探索性: 1轮澄清问题
- 低置信度: 带默认值的选项
"""

from __future__ import annotations

import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum, auto


class ThinkingResultType(Enum):
    """思考结果类型"""
    DIRECT_ANSWER = "direct_answer"           # 直接回答（非任务型）
    EXECUTION_PREVIEW = "execution_preview"   # 执行预览（高置信度）
    CLARIFICATION_QUESTION = "clarification_question"  # 1轮澄清
    OPTIONS_WITH_DEFAULT = "options_with_default"      # 带默认选项
    NEEDS_DECOMPOSITION = "needs_decomposition"        # 需要分解


@dataclass
class ClarificationQuestion:
    """澄清问题"""
    id: str
    text: str
    question_type: str  # "single_choice", "text_input", "multi_choice"
    options: Optional[List[Dict[str, str]]] = None
    default_answer: Optional[str] = None
    context: str = ""  # 为什么问这个问题


@dataclass
class ThinkingOption:
    """思考选项"""
    id: str
    label: str
    description: str
    confidence: float  # 0-1
    is_default: bool = False
    is_custom: bool = False


@dataclass
class ExecutionPreview:
    """执行预览"""
    task_type: str
    complexity: str  # simple, medium, complex
    steps: List[Dict[str, Any]]
    estimated_time: str
    required_confirmations: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)


@dataclass
class IntentAnalysis:
    """意图分析结果"""
    intent: str
    confidence: float
    is_task: bool  # 是否任务型（需要执行）
    is_exploratory: bool  # 是否探索性（用户不确定要什么）
    key_entities: Dict[str, Any] = field(default_factory=dict)
    missing_info: List[str] = field(default_factory=list)
    suggested_approach: str = ""


@dataclass
class ThinkingResult:
    """思考结果"""
    result_type: ThinkingResultType
    confidence: float
    direct_answer: Optional[str] = None
    clarification_question: Optional[ClarificationQuestion] = None
    options: Optional[List[ThinkingOption]] = None
    execution_preview: Optional[ExecutionPreview] = None
    context: Dict[str, Any] = field(default_factory=dict)


class DynamicThinkingEngine:
    """
    动态思考引擎 - 80%场景0-1次选择
    
    目标：减少用户决策负担，AI主动承担更多判断
    """
    
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    MEDIUM_CONFIDENCE_THRESHOLD = 0.6
    
    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.current_context: Dict[str, Any] = {}
    
    def process(self, user_input: str, context: Optional[Dict] = None) -> ThinkingResult:
        """
        处理用户输入，返回思考结果
        
        Args:
            user_input: 用户输入
            context: 可选上下文
        
        Returns:
            ThinkingResult: 思考结果
        """
        # 更新上下文
        if context:
            self.current_context.update(context)
        
        # 1. 意图分析
        analysis = self._analyze_intent(user_input)
        
        # 2. 根据分析结果路由到不同处理
        if not analysis.is_task:
            # 非任务型：直接回答（处理问候和问答）
            return self._generate_direct_answer(analysis, user_input)
        
        if analysis.confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            # 高置信度：直接生成执行预览
            return self._generate_execution_preview(analysis)
        
        elif analysis.is_exploratory:
            # 探索性：澄清问题（1轮）
            return self._generate_clarification_question(analysis)
        
        else:
            # 其他情况：带默认值的选项
            return self._generate_options_with_default(analysis)
    
    def _analyze_intent(self, user_input: str) -> IntentAnalysis:
        """
        分析用户意图
        
        识别：
        - 任务类型（旅行规划/代码生成/数据分析等）
        - 置信度（信息完整度）
        - 关键实体提取
        """
        input_lower = user_input.lower()
        
        # 判断是否为任务型（排除问答类关键词）
        task_keywords = [
            '规划', 'plan', '旅行', 'travel', 'trip', '旅游', 'tourism', '游', 'tour',
            '写', 'write', '生成', 'generate', '创建', 'create', '搭建', 'build',
            '脚本', 'script', '代码', 'code', '程序', 'program', '工具', 'tool',
            '列出', 'list', '显示', 'show', '查看', 'view', '获取', 'get', '查询', 'search',
            '重命名', 'rename', '移动', 'move', '复制', 'copy', '删除', 'delete',
            '执行', 'run', '启动', 'start', '停止', 'stop',
            '推荐', 'recommend', '建议', 'suggest', '统计', 'stats', '图表', 'chart',
            '分析', 'analyze', '做', 'do', '去哪里', 'where to'
        ]
        
        # 问答类关键词（如果不是问句，只是包含这些词，可能是任务）
        qa_indicators = ['是什么', '是谁', '是谁', '你能', '你会', 'what can', 'who are', 'what is', '你能做什么', '你会什么']
        is_likely_qa = any(kw in input_lower for kw in qa_indicators)
        has_task_keyword = any(kw in input_lower for kw in task_keywords)
        is_task = has_task_keyword and not is_likely_qa
        
        # 提取关键实体
        entities = self._extract_entities(user_input)
        
        # 计算置信度
        confidence = self._calculate_confidence(user_input, entities)
        
        # 判断是否探索性
        exploratory_keywords = ['想', 'want', '考虑', 'considering', '看看', '看看', 'explore']
        is_exploratory = any(kw in input_lower for kw in exploratory_keywords)
        
        # 识别缺失信息
        missing = self._identify_missing_info(user_input, entities)
        
        return IntentAnalysis(
            intent=self._classify_intent(input_lower),
            confidence=confidence,
            is_task=is_task,
            is_exploratory=is_exploratory,
            key_entities=entities,
            missing_info=missing,
            suggested_approach=self._suggest_approach(entities, missing)
        )
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """提取关键实体"""
        entities = {}
        
        # 提取地点
        # 简单模式匹配，实际应用中使用NER
        location_patterns = [
            r'去(\w+)', r'到(\w+)', r'在(\w+)',
            r'去 ([\w\s]+)', r'到 ([\w\s]+)'
        ]
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                entities['location'] = match.group(1).strip()
                break
        
        # 提取时间
        time_keywords = ['周末', '明天', '下周', '下个月', 'spring', 'summer']
        for kw in time_keywords:
            if kw in text:
                entities['time'] = kw
                break
        
        # 提取偏好/风格
        if any(kw in text for kw in ['自然', 'nature', '风景', 'scenery']):
            entities['style'] = 'nature'
        elif any(kw in text for kw in ['城市', 'city', 'urban', '购物', 'shopping']):
            entities['style'] = 'urban'
        elif any(kw in text for kw in ['历史', 'history', '文化', 'culture']):
            entities['style'] = 'culture'
        
        # 提取文件类型（用于文件操作）
        file_patterns = [
            r'(\w+\.\w+)',  # filename.ext
            r'(\w+)文件',    # XX文件
            r'(\w+) file'    # XX file
        ]
        for pattern in file_patterns:
            match = re.search(pattern, text)
            if match:
                entities['file'] = match.group(1)
                break
        
        return entities
    
    def _calculate_confidence(self, text: str, entities: Dict) -> float:
        """计算意图置信度"""
        score = 0.5  # 基础分
        
        # 输入长度（适中长度加分）
        if 10 < len(text) < 100:
            score += 0.1
        
        # 实体数量
        score += min(len(entities) * 0.15, 0.3)
        
        # 具体性指标
        specific_keywords = ['具体', '详细', '明确', '详细', 'specific', 'detailed']
        if any(kw in text for kw in specific_keywords):
            score += 0.1
        
        return min(score, 1.0)
    
    def _identify_missing_info(self, text: str, entities: Dict) -> List[str]:
        """识别缺失的关键信息"""
        missing = []
        
        # 旅行相关
        if any(kw in text for kw in ['旅行', 'travel', 'trip', '旅游', '游玩']):
            if 'location' not in entities:
                missing.append('destination')
            if 'time' not in entities:
                missing.append('time')
            if 'style' not in entities:
                missing.append('preference')
        
        # 代码相关
        if any(kw in text for kw in ['代码', 'code', '脚本', 'script', '程序']):
            if 'language' not in entities:
                missing.append('language')
            if 'file' not in entities and 'folder' not in entities:
                missing.append('target')
        
        return missing
    
    def _classify_intent(self, text_lower: str) -> str:
        """分类意图类型"""
        if any(kw in text_lower for kw in ['旅行', 'travel', 'trip', '旅游']):
            return 'travel_planning'
        elif any(kw in text_lower for kw in ['代码', 'code', '脚本', 'script', '程序', 'program']):
            return 'code_generation'
        elif any(kw in text_lower for kw in ['分析', 'analyze', '数据', 'data', 'csv', 'excel']):
            return 'data_analysis'
        elif any(kw in text_lower for kw in ['写', 'write', '文章', 'article', '内容', 'content']):
            return 'content_creation'
        elif any(kw in text_lower for kw in ['搭建', 'build', '部署', 'deploy', '配置', 'setup']):
            return 'project_setup'
        elif any(kw in text_lower for kw in ['文件', 'file', '目录', 'folder', '重命名', 'rename', '批量', '列出', 'list']):
            return 'file_operation'
        else:
            return 'general_task'
    
    def _suggest_approach(self, entities: Dict, missing: List[str]) -> str:
        """建议处理方案"""
        if not missing:
            return "direct_execution"
        elif len(missing) <= 2:
            return "minimal_clarification"
        else:
            return "structured_questioning"
    
    def _generate_direct_answer(self, analysis: IntentAnalysis, user_input: str = "") -> ThinkingResult:
        """生成直接回答 - 处理问候和问答"""
        # If it's a task but with low confidence, provide options instead of just asking
        if analysis.is_task:
            # Try to generate options or execution preview based on intent
            if analysis.intent == 'file_operation':
                # For file operations, generate execution preview directly
                return self._generate_execution_preview(analysis)
            elif analysis.intent == 'general_task':
                # For general tasks, provide options
                return self._generate_options_with_default(analysis)
        
        # Check for greetings and questions
        input_lower = user_input.lower()
        
        # Greetings
        if any(kw in input_lower for kw in ['你好', 'hello', 'hi', 'hey', '在吗']):
            return ThinkingResult(
                result_type=ThinkingResultType.DIRECT_ANSWER,
                confidence=1.0,
                direct_answer="你好！我是Blueclaw，你的AI助手。\n\n我可以帮你：\n- 规划旅行\n- 编写代码\n- 分析数据\n- 执行文件操作\n\n请告诉我你想做什么？"
            )
        
        # Identity questions
        if any(kw in input_lower for kw in ['你是谁', '你是什么', 'what are you', 'who are you']):
            return ThinkingResult(
                result_type=ThinkingResultType.DIRECT_ANSWER,
                confidence=1.0,
                direct_answer="我是Blueclaw v1.0，一个AI自执行画布框架。\n\n我的特点：\n- 动态思考引擎：理解你的需求并提供选项\n- 执行蓝图：可视化任务执行流程\n- 真实执行：可以操作文件、执行代码、搜索网络\n- 干预机制：随时暂停、调整、重新规划\n\n有什么我可以帮你的吗？"
            )
        
        # Capability questions
        if any(kw in input_lower for kw in ['你能做什么', '你会什么', 'what can you do', 'help']):
            return ThinkingResult(
                result_type=ThinkingResultType.DIRECT_ANSWER,
                confidence=1.0,
                direct_answer="我可以帮你完成各种任务：\n\n[文件操作]\n- 列出、读取、写入文件\n- 批量重命名\n- 目录管理\n\n[代码执行]\n- 编写Python脚本\n- 执行代码\n- 数据分析\n\n[网络操作]\n- 网页搜索\n- 浏览器自动化\n\n[任务规划]\n- 旅行规划\n- 项目搭建\n- 流程自动化\n\n试试输入：'列出当前目录的文件' 或 '规划一个周末旅行'"
            )
        
        # Default greeting
        return ThinkingResult(
            result_type=ThinkingResultType.DIRECT_ANSWER,
            confidence=analysis.confidence,
            direct_answer=f"你好！我是Blueclaw，你的AI助手。\n\n我可以帮你：\n- 规划旅行\n- 编写代码\n- 分析数据\n- 执行文件操作\n\n请告诉我你想做什么？"
        )
    
    def _generate_execution_preview(self, analysis: IntentAnalysis) -> ThinkingResult:
        """生成执行预览（高置信度）"""
        # 根据意图类型生成相应的步骤
        steps = self._generate_steps_for_intent(analysis)
        
        preview = ExecutionPreview(
            task_type=analysis.intent,
            complexity="medium",
            steps=steps,
            estimated_time="2-5分钟"
        )
        
        return ThinkingResult(
            result_type=ThinkingResultType.EXECUTION_PREVIEW,
            confidence=analysis.confidence,
            execution_preview=preview
        )
    
    def _generate_clarification_question(self, analysis: IntentAnalysis) -> ThinkingResult:
        """生成澄清问题（1轮）或选项"""
        # 对于旅行规划，提供选项而不是直接提问
        if analysis.intent == 'travel_planning':
            return self._generate_options_with_default(analysis)
        
        # 根据缺失信息生成问题
        question = self._create_question_for_missing(analysis)
        
        return ThinkingResult(
            result_type=ThinkingResultType.CLARIFICATION_QUESTION,
            confidence=analysis.confidence,
            clarification_question=question
        )
    
    def _generate_options_with_default(self, analysis: IntentAnalysis) -> ThinkingResult:
        """生成带默认值的选项"""
        options = self._create_options_for_intent(analysis)
        
        return ThinkingResult(
            result_type=ThinkingResultType.OPTIONS_WITH_DEFAULT,
            confidence=analysis.confidence,
            options=options
        )
    
    def _generate_steps_for_intent(self, analysis: IntentAnalysis) -> List[Dict[str, Any]]:
        """根据意图生成执行步骤"""
        intent = analysis.intent
        entities = analysis.key_entities
        
        if intent == 'travel_planning':
            return [
                {"name": "查询目的地天气", "description": f"查询{entities.get('location', '目的地')}天气情况"},
                {"name": "搜索景点推荐", "description": "搜索热门景点和活动"},
                {"name": "规划交通路线", "description": "规划最佳交通方案"},
                {"name": "生成行程计划", "description": "整合信息生成完整行程"}
            ]
        elif intent == 'code_generation':
            return [
                {"name": "分析需求", "description": "分析代码需求和约束条件"},
                {"name": "生成代码", "description": "编写核心代码逻辑"},
                {"name": "添加注释", "description": "添加文档和注释"},
                {"name": "测试验证", "description": "验证代码正确性"}
            ]
        elif intent == 'file_operation':
            return [
                {"name": "扫描目标文件", "description": "扫描目录中的目标文件"},
                {"name": "分析文件属性", "description": "提取文件元数据"},
                {"name": "生成操作预览", "description": "展示操作效果预览"},
                {"name": "执行文件操作", "description": "执行实际文件操作"},
                {"name": "生成操作报告", "description": "总结操作结果"}
            ]
        elif intent == 'data_analysis':
            return [
                {"name": "读取数据文件", "description": "加载并解析数据"},
                {"name": "数据清洗", "description": "处理缺失值和异常"},
                {"name": "数据分析", "description": "执行统计分析"},
                {"name": "生成可视化", "description": "创建图表展示"},
                {"name": "输出报告", "description": "生成分析报告"}
            ]
        else:
            return [
                {"name": "理解需求", "description": "分析任务需求"},
                {"name": "规划方案", "description": "制定执行方案"},
                {"name": "执行任务", "description": "执行具体任务"},
                {"name": "验证结果", "description": "检查结果正确性"}
            ]
    
    def _create_question_for_missing(self, analysis: IntentAnalysis) -> ClarificationQuestion:
        """根据缺失信息创建问题"""
        missing = analysis.missing_info
        intent = analysis.intent
        
        if intent == 'travel_planning':
            if 'destination' in missing:
                # Provide options instead of asking "where do you want to go"
                return ClarificationQuestion(
                    id="travel_dest",
                    text="请选择旅行目的地或风格：",
                    question_type="single_choice",
                    options=[
                        {"id": "A", "label": "杭州 - 西湖茶文化", "description": "适合喜欢自然风光和茶文化的旅行者"},
                        {"id": "B", "label": "苏州 - 园林古镇", "description": "适合喜欢古典园林和水乡风情的旅行者"},
                        {"id": "C", "label": "厦门 - 海岛文艺", "description": "适合喜欢海滨风光和文艺气息的旅行者"},
                        {"id": "D", "label": "其他城市", "description": "自定义目的地"}
                    ],
                    context="根据您的偏好推荐目的地"
                )
            elif 'style' in missing:
                return ClarificationQuestion(
                    id="travel_style",
                    text="你喜欢什么样的旅行风格？",
                    question_type="single_choice",
                    options=[
                        {"id": "A", "label": "自然风光", "description": "山水、森林、户外"},
                        {"id": "B", "label": "城市探索", "description": "建筑、美食、购物"},
                        {"id": "C", "label": "历史文化", "description": "古迹、博物馆、人文"},
                        {"id": "D", "label": "休闲度假", "description": "温泉、海滩、慢生活"}
                    ],
                    context="旅行风格影响景点推荐和活动安排"
                )
        
        elif intent == 'file_operation':
            return ClarificationQuestion(
                id="file_pattern",
                text="请选择日期格式和来源：",
                question_type="single_choice",
                options=[
                    {"id": "A", "label": "YYYYMMDD_原文件名", "description": "如：20240330_IMG001.jpg"},
                    {"id": "B", "label": "原文件名_YYYYMMDD", "description": "如：IMG001_20240330.jpg"},
                    {"id": "C", "label": "其他", "description": "自定义格式"}
                ],
                context="日期格式决定重命名后的文件外观"
            )
        
        # 默认问题
        return ClarificationQuestion(
            id="general",
            text="请告诉我更多信息，以便我更好地帮助你。",
            question_type="text_input",
            context="需要更多信息才能继续"
        )
    
    def _create_options_for_intent(self, analysis: IntentAnalysis) -> List[ThinkingOption]:
        """根据意图创建选项"""
        intent = analysis.intent
        
        if intent == 'travel_planning':
            return [
                ThinkingOption(
                    id="A",
                    label="自然风光路线",
                    description="适合喜欢山水、户外活动的旅行者",
                    confidence=0.75,
                    is_default=True
                ),
                ThinkingOption(
                    id="B",
                    label="城市探索路线",
                    description="适合喜欢建筑、美食、文化的旅行者",
                    confidence=0.70
                ),
                ThinkingOption(
                    id="C",
                    label="休闲度假路线",
                    description="适合想要放松、慢节奏旅行的旅行者",
                    confidence=0.65
                )
            ]
        elif intent == 'code_generation':
            return [
                ThinkingOption(
                    id="A",
                    label="完整脚本",
                    description="包含所有功能的独立可运行脚本",
                    confidence=0.80,
                    is_default=True
                ),
                ThinkingOption(
                    id="B",
                    label="核心函数",
                    description="提供核心功能函数，方便集成",
                    confidence=0.75
                ),
                ThinkingOption(
                    id="C",
                    label="示例代码",
                    description="简单示例展示主要用法",
                    confidence=0.70
                )
            ]
        else:
            return [
                ThinkingOption(
                    id="A",
                    label="标准方案",
                    description="适合大多数情况的推荐方案",
                    confidence=0.75,
                    is_default=True
                ),
                ThinkingOption(
                    id="B",
                    label="简化方案",
                    description="快速完成，功能精简",
                    confidence=0.70
                ),
                ThinkingOption(
                    id="C",
                    label="详细方案",
                    description="包含完整配置和优化",
                    confidence=0.65
                )
            ]
    
    def continue_with_clarification(
        self,
        answer: str,
        question: ClarificationQuestion
    ) -> ThinkingResult:
        """
        根据澄清回答继续思考
        
        更新上下文，重新评估是否需要更多信息
        """
        # 记录回答
        self.conversation_history.append({
            'question': question,
            'answer': answer
        })
        
        # 更新实体
        if question.id == "travel_dest":
            self.current_context['destination'] = answer
        elif question.id == "travel_style":
            self.current_context['style'] = answer
        
        # 基于已有信息生成执行预览
        analysis = IntentAnalysis(
            intent='travel_planning',
            confidence=0.9,  # 回答后置信度提高
            is_task=True,
            is_exploratory=False,
            key_entities=self.current_context,
            missing_info=[]
        )
        
        return self._generate_execution_preview(analysis)
    
    def continue_with_option(
        self,
        option_id: str,
        option: ThinkingOption
    ) -> ThinkingResult:
        """根据选项选择继续"""
        self.current_context['selected_option'] = option_id
        
        analysis = IntentAnalysis(
            intent='general_task',
            confidence=option.confidence,
            is_task=True,
            is_exploratory=False,
            key_entities=self.current_context
        )
        
        return self._generate_execution_preview(analysis)


def create_dynamic_thinking_engine() -> DynamicThinkingEngine:
    """创建思考引擎实例"""
    return DynamicThinkingEngine()
