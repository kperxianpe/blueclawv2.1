# -*- coding: utf-8 -*-
"""
confidence_scorer.py - 置信度评分器

职责: 计算对任务理解的置信度
影响因素：
- 实体提取完整度 (0-0.3)
- 任务范围清晰度 (0-0.3)
- 历史对话一致性 (0-0.2)
- 输入明确程度 (0-0.2)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum


class ConfidenceLevel(Enum):
    """置信度级别"""
    HIGH = "high"       # >= 0.85, 可以直接执行
    MEDIUM = "medium"   # 0.6 - 0.85, 提供选项
    LOW = "low"         # < 0.6, 需要澄清


@dataclass
class ConfidenceScore:
    """置信度评分结果"""
    value: float  # 0.0 - 1.0
    level: ConfidenceLevel
    factors: Dict[str, float]  # 各因子得分明细
    reasoning: str  # 计算理由
    suggestions: List[str] = field(default_factory=list)  # 改进建议
    
    def can_auto_execute(self) -> bool:
        """判断是否可以自动执行（高置信度）"""
        return self.level == ConfidenceLevel.HIGH
    
    def should_ask_clarification(self) -> bool:
        """判断是否需要澄清"""
        return self.level in [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM]


class ConfidenceScorer:
    """置信度评分器"""
    
    # 权重配置
    WEIGHTS = {
        'entity_completeness': 0.30,  # 实体完整度
        'scope_clarity': 0.30,        # 范围清晰度
        'history_consistency': 0.20,  # 历史一致性
        'input_clarity': 0.20,        # 输入明确度
    }
    
    # 阈值配置
    THRESHOLDS = {
        'high': 0.85,    # 高置信度阈值
        'medium': 0.60,  # 中等置信度阈值
    }
    
    def __init__(self, weights: Dict[str, float] = None):
        """
        初始化评分器
        
        Args:
            weights: 自定义权重配置
        """
        self.weights = weights or self.WEIGHTS.copy()
        self._validate_weights()
    
    def _validate_weights(self):
        """验证权重总和为1"""
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            # 归一化
            for key in self.weights:
                self.weights[key] /= total
    
    def score(
        self,
        intent_analysis,
        context: Dict[str, Any] = None,
        history: List[Dict] = None
    ) -> ConfidenceScore:
        """
        计算置信度
        
        Args:
            intent_analysis: 意图分析结果
            context: 上下文信息
            history: 历史对话记录
            
        Returns:
            ConfidenceScore: 置信度评分结果
        """
        context = context or {}
        history = history or []
        
        factors = {}
        
        # 1. 计算实体完整度
        factors['entity_completeness'] = self._score_entity_completeness(
            intent_analysis
        )
        
        # 2. 计算范围清晰度
        factors['scope_clarity'] = self._score_scope_clarity(
            intent_analysis
        )
        
        # 3. 计算历史一致性
        factors['history_consistency'] = self._score_history_consistency(
            intent_analysis, history
        )
        
        # 4. 计算输入明确度
        factors['input_clarity'] = self._score_input_clarity(
            intent_analysis
        )
        
        # 计算总分
        total_score = sum(
            score * self.weights.get(factor, 0)
            for factor, score in factors.items()
        )
        
        # 确定级别
        level = self._determine_level(total_score)
        
        # 生成理由和建议
        reasoning = self._generate_reasoning(factors, total_score)
        suggestions = self._generate_suggestions(factors)
        
        return ConfidenceScore(
            value=round(total_score, 3),
            level=level,
            factors=factors,
            reasoning=reasoning,
            suggestions=suggestions
        )
    
    def _score_entity_completeness(self, intent_analysis) -> float:
        """评分：实体完整度"""
        entities = getattr(intent_analysis, 'extracted_entities', {}) or {}
        task_type = getattr(intent_analysis, 'task_type', None)
        
        if not entities:
            return 0.2
        
        # 根据任务类型判断需要的实体
        required_entities = self._get_required_entities(task_type)
        
        if not required_entities:
            return 0.5 + min(len(entities) * 0.1, 0.5)
        
        # 计算已提取的必需实体比例
        found = sum(1 for e in required_entities if e in entities)
        ratio = found / len(required_entities)
        
        # 基础分 + 比例分
        return 0.3 + ratio * 0.7
    
    def _get_required_entities(self, task_type) -> List[str]:
        """获取任务类型需要的实体"""
        entity_map = {
            'travel_planning': ['destination', 'time'],
            'code_generation': ['language', 'function_type'],
            'file_operation': ['file', 'operation'],
            'data_analysis': ['data_source', 'analysis_type'],
        }
        return entity_map.get(str(task_type), [])
    
    def _score_scope_clarity(self, intent_analysis) -> float:
        """评分：范围清晰度"""
        task_scope = getattr(intent_analysis, 'task_scope', None)
        raw_input = getattr(intent_analysis, 'raw_input', "")
        
        # 有明确的任务范围
        if task_scope:
            return 0.8
        
        # 根据输入明确程度评分
        score = 0.4  # 基础分
        
        # 包含具体数字/时间加分
        indicators = ['具体', '详细', '明确', '只需要', '只要', '仅']
        for indicator in indicators:
            if indicator in raw_input:
                score += 0.1
        
        return min(score, 0.9)
    
    def _score_history_consistency(
        self,
        intent_analysis,
        history: List[Dict]
    ) -> float:
        """评分：历史一致性"""
        if not history:
            return 0.5  # 无历史，中等分
        
        # 检查是否延续之前的上下文
        current_intent = getattr(intent_analysis, 'intent_type', None)
        
        # 获取最近的历史意图
        recent_history = history[-3:] if len(history) >= 3 else history
        consistent_count = 0
        
        for h in recent_history:
            hist_intent = h.get('intent_type')
            if hist_intent == current_intent:
                consistent_count += 1
        
        if consistent_count == 0:
            return 0.5
        
        ratio = consistent_count / len(recent_history)
        return 0.4 + ratio * 0.6
    
    def _score_input_clarity(self, intent_analysis) -> float:
        """评分：输入明确度"""
        raw_input = getattr(intent_analysis, 'raw_input', "")
        
        if not raw_input:
            return 0.0
        
        score = 0.4  # 基础分
        length = len(raw_input)
        
        # 长度适中加分
        if 10 <= length <= 200:
            score += 0.2
        elif length > 200:
            score += 0.1  # 过长略微减分
        
        # 包含动词加分
        verbs = ['需要', '想要', '帮我', '请', '能不能', '可以']
        for verb in verbs:
            if verb in raw_input:
                score += 0.05
        
        # 包含具体名词加分
        if any(c.isdigit() for c in raw_input):
            score += 0.1
        
        return min(score, 1.0)
    
    def _determine_level(self, score: float) -> ConfidenceLevel:
        """确定置信度级别"""
        if score >= self.THRESHOLDS['high']:
            return ConfidenceLevel.HIGH
        elif score >= self.THRESHOLDS['medium']:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _generate_reasoning(self, factors: Dict[str, float], total: float) -> str:
        """生成评分理由"""
        reasons = []
        
        # 找出最高和最低分因子
        sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_factors:
            best = sorted_factors[0]
            worst = sorted_factors[-1]
            
            reasons.append(f"优势: {best[0]} ({best[1]:.2f})")
            if worst[1] < 0.5:
                reasons.append(f"待改进: {worst[0]} ({worst[1]:.2f})")
        
        return "; ".join(reasons) if reasons else f"综合得分: {total:.2f}"
    
    def _generate_suggestions(self, factors: Dict[str, float]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if factors.get('entity_completeness', 1) < 0.5:
            suggestions.append("请提供更多具体信息，如地点、时间等")
        
        if factors.get('scope_clarity', 1) < 0.5:
            suggestions.append("请明确任务范围或约束条件")
        
        if factors.get('input_clarity', 1) < 0.5:
            suggestions.append("请用更明确的语言描述需求")
        
        return suggestions
    
    def should_ask_clarification(self, score: ConfidenceScore) -> bool:
        """判断是否需要澄清"""
        return score.level in [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM]
    
    def can_auto_execute(self, score: ConfidenceScore) -> bool:
        """判断是否可以直接执行"""
        return score.level == ConfidenceLevel.HIGH
    
    def get_missing_info_types(
        self,
        intent_analysis,
        score: ConfidenceScore
    ) -> List[str]:
        """获取缺失的信息类型"""
        missing = []
        
        factors = score.factors
        
        if factors.get('entity_completeness', 1) < 0.5:
            task_type = getattr(intent_analysis, 'task_type', None)
            required = self._get_required_entities(task_type)
            entities = getattr(intent_analysis, 'extracted_entities', {})
            
            for entity in required:
                if entity not in entities:
                    missing.append(entity)
        
        if factors.get('scope_clarity', 1) < 0.5:
            missing.append('scope')
        
        return missing


# 便捷函数
def calculate_confidence(
    intent_analysis,
    context: Dict[str, Any] = None,
    history: List[Dict] = None
) -> ConfidenceScore:
    """便捷函数：计算置信度"""
    scorer = ConfidenceScorer()
    return scorer.score(intent_analysis, context, history)
