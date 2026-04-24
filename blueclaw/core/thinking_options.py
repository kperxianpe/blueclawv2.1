# -*- coding: utf-8 -*-
"""
Thinking Options - 四选一交互模式 (Blueclaw v1.0)
在 OpenClaw 基础上增加：
1. 意图识别显示
2. 思考过程可视化
3. 四选一选项（带置信度）
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid


class IntentType(Enum):
    """用户意图类型"""
    CREATE = "create"
    MODIFY = "modify"
    QUERY = "query"
    EXECUTE = "execute"
    CHAT = "chat"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class ActionOption:
    """行动选项（四选一）"""
    option_id: str           # A, B, C, D
    title: str               # 选项标题
    description: str         # 详细描述
    action_type: str         # 行动类型
    icon: str = "🔹"
    confidence: int = 80     # 匹配度 0-100
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThinkingStep:
    """思考步骤"""
    step_number: int
    title: str
    content: str
    icon: str = "💭"


@dataclass
class ThinkingBlueprintResult:
    """思考蓝图结果"""
    user_input: str
    intent: IntentType
    intent_confidence: float
    
    thinking_steps: List[ThinkingStep]
    options: List[ActionOption]  # 四选一选项
    
    context_analysis: str
    suggested_next: Optional[str] = None


class ThinkingBlueprintEngine:
    """
    思考蓝图引擎（带四选一交互）
    
    类似 OpenClaw，但增加：
    1. 意图识别（带置信度）
    2. 思考过程可视化
    3. 四选一选项
    """
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())[:8]
        self.conversation_history: List[Dict] = []
        self.context: Dict[str, Any] = {}
        
    def analyze(self, user_input: str) -> ThinkingBlueprintResult:
        """分析用户输入，生成思考蓝图"""
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # 1. 意图识别
        intent, confidence = self._recognize_intent(user_input)
        
        # 2. 生成思考链
        thinking_steps = self._generate_thinking_chain(user_input, intent)
        
        # 3. 生成四选一选项
        options = self._generate_options(user_input, intent)
        
        # 4. 上下文分析
        context_analysis = self._analyze_context(user_input, intent)
        
        return ThinkingBlueprintResult(
            user_input=user_input,
            intent=intent,
            intent_confidence=confidence,
            thinking_steps=thinking_steps,
            options=options,
            context_analysis=context_analysis
        )
    
    def _recognize_intent(self, input_text: str) -> tuple[IntentType, float]:
        """识别用户意图和置信度"""
        text = input_text.lower()
        
        patterns = {
            IntentType.CREATE: [
                ("创建", 0.9), ("生成", 0.9), ("新建", 0.9),
                ("做一个", 0.8), ("帮我写", 0.8), ("想要个", 0.7),
                ("create", 0.9), ("generate", 0.9), ("make", 0.8),
            ],
            IntentType.MODIFY: [
                ("修改", 0.9), ("编辑", 0.9), ("调整", 0.8),
                ("改一下", 0.8), ("更新", 0.8),
                ("modify", 0.9), ("edit", 0.9), ("change", 0.8),
            ],
            IntentType.QUERY: [
                ("是什么", 0.9), ("怎么做", 0.9), ("为什么", 0.9),
                ("查询", 0.8), ("查找", 0.8), ("搜索", 0.8),
                ("what", 0.9), ("how", 0.9), ("why", 0.9),
                ("?", 0.7)
            ],
            IntentType.EXECUTE: [
                ("运行", 0.9), ("执行", 0.9), ("启动", 0.8),
                ("开始", 0.7), ("加载", 0.7),
                ("run", 0.9), ("execute", 0.9), ("start", 0.8),
            ],
            IntentType.HELP: [
                ("帮助", 0.9), ("怎么用", 0.9), ("教教我", 0.9),
                ("不会", 0.8), ("求助", 0.9),
                ("help", 0.9), ("how to use", 0.9),
            ],
            IntentType.CHAT: [
                ("你好", 0.8), ("在吗", 0.7), ("谢谢", 0.7),
                ("hi", 0.8), ("hello", 0.8), ("thanks", 0.7),
            ]
        }
        
        scores = {}
        for intent, keywords in patterns.items():
            score = 0
            for keyword, weight in keywords:
                if keyword in text:
                    score = max(score, weight)
            scores[intent] = score
        
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        
        if best_score < 0.3:
            return IntentType.UNKNOWN, 0.3
        
        return best_intent, best_score
    
    def _generate_thinking_chain(self, input_text: str, intent: IntentType) -> List[ThinkingStep]:
        """生成思考链"""
        steps = [
            ThinkingStep(
                step_number=1,
                title="输入解析",
                content=f"识别用户意图: {intent.value}",
                icon="🔍"
            ),
            ThinkingStep(
                step_number=2,
                title="上下文分析",
                content="检查对话历史..." if self.conversation_history else "新对话，无历史上下文",
                icon="🧠"
            ),
            ThinkingStep(
                step_number=3,
                title="方案生成",
                content=f"基于意图 '{intent.value}' 生成行动方案...",
                icon="💡"
            )
        ]
        return steps
    
    def _generate_options(self, input_text: str, intent: IntentType) -> List[ActionOption]:
        """生成四选一选项"""
        if intent == IntentType.CREATE:
            return [
                ActionOption("A", "快速模板创建", "使用预设模板快速开始", "quick_template", "🚀", 90),
                ActionOption("B", "自定义创建", "根据需求定制细节", "custom_create", "⚙️", 85),
                ActionOption("C", "查看示例", "先看看别人怎么做", "show_examples", "👀", 70),
                ActionOption("D", "AI推荐方案", "让AI分析后推荐", "ai_recommend", "🤖", 75),
            ]
        elif intent == IntentType.QUERY:
            return [
                ActionOption("A", "直接回答", "基于知识库回答", "direct_answer", "💬", 90),
                ActionOption("B", "详细解释", "提供背景信息和原理", "detailed_explain", "📚", 85),
                ActionOption("C", "实际操作", "通过演示展示答案", "demo", "🎮", 70),
                ActionOption("D", "推荐资源", "推荐相关文档教程", "recommend", "🔗", 75),
            ]
        elif intent == IntentType.CHAT:
            return [
                ActionOption("A", "继续闲聊", "随便聊聊", "chat", "💭", 90),
                ActionOption("B", "讲个笑话", "轻松一下", "joke", "😄", 70),
                ActionOption("C", "开始工作", "转入任务模式", "work", "💼", 85),
                ActionOption("D", "介绍功能", "了解我能做什么", "introduce", "📖", 75),
            ]
        else:
            return [
                ActionOption("A", "执行任务", "直接执行指令", "execute", "▶️", 80),
                ActionOption("B", "询问详情", "先了解更多信息", "ask_details", "❓", 85),
                ActionOption("C", "查看帮助", "查看使用帮助", "show_help", "❔", 70),
                ActionOption("D", "重新表述", "请更清晰地描述", "clarify", "🔄", 60),
            ]
    
    def _analyze_context(self, input_text: str, intent: IntentType) -> str:
        """分析上下文"""
        if self.conversation_history:
            return "基于对话历史"
        return "新对话"
    
    def execute_option(self, result: ThinkingBlueprintResult, option_id: str) -> Dict[str, Any]:
        """执行用户选择的选项"""
        option = next((o for o in result.options if o.option_id == option_id), None)
        
        if not option:
            return {"success": False, "message": f"无效选项: {option_id}", "action": "error"}
        
        return {
            "success": True,
            "message": f"执行选项 {option_id}: {option.title}",
            "action": option.action_type,
            "params": option.params,
            "option": option
        }
