# -*- coding: utf-8 -*-
"""
option_generator.py - 选项生成器

职责: 根据意图和上下文生成3-4个选项
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


class OptionType(Enum):
    """选项类型"""
    SPECIFIC = "specific"    # 具体选项
    OPEN = "open"            # 开放输入
    DEFAULT = "default"      # 默认推荐


@dataclass
class Option:
    """选项定义"""
    id: str  # "A", "B", "C", "D"
    label: str  # 选项标题
    description: str  # 详细描述
    example: str  # 示例
    confidence: float  # AI对这个选项的置信度
    option_type: OptionType = OptionType.SPECIFIC
    is_recommended: bool = False  # 是否推荐
    metadata: Dict[str, Any] = field(default_factory=dict)


class OptionGenerator:
    """选项生成器"""
    
    # 任务类型对应的选项模板
    OPTION_TEMPLATES = {
        'travel_planning': [
            {
                'label': '自然风光路线',
                'description': '推荐山水、森林、户外景点，适合喜欢大自然的旅行者',
                'example': '西湖、黄山、九寨沟等自然风景区'
            },
            {
                'label': '城市探索路线',
                'description': '推荐城市建筑、美食、文化体验，适合喜欢都市生活的人',
                'example': '上海外滩、北京胡同、成都宽窄巷子'
            },
            {
                'label': '历史文化路线',
                'description': '推荐古迹、博物馆、人文景点，适合喜欢历史的旅行者',
                'example': '故宫、兵马俑、敦煌莫高窟'
            },
        ],
        'code_generation': [
            {
                'label': '完整脚本',
                'description': '提供独立可运行的完整脚本，包含所有功能',
                'example': '包含输入处理、核心逻辑、错误处理的完整程序'
            },
            {
                'label': '核心函数',
                'description': '提供核心功能函数，方便集成到现有项目',
                'example': 'def process_data(data): ...'
            },
            {
                'label': '代码示例',
                'description': '提供简洁示例代码，展示主要用法',
                'example': '简短的代码片段演示关键功能'
            },
        ],
        'file_operation': [
            {
                'label': '批量重命名',
                'description': '按照日期/序号等规则批量重命名文件',
                'example': 'IMG001.jpg -> 20240330_IMG001.jpg'
            },
            {
                'label': '整理归档',
                'description': '按类型/日期自动分类文件到不同目录',
                'example': '图片放入Images，文档放入Documents'
            },
            {
                'label': '数据提取',
                'description': '从文件中提取关键信息并生成报告',
                'example': '提取CSV中的统计数据并生成图表'
            },
        ],
        'data_analysis': [
            {
                'label': '描述性分析',
                'description': '统计基本指标：平均值、分布、趋势等',
                'example': '生成数据的统计摘要和分布图表'
            },
            {
                'label': '相关性分析',
                'description': '分析不同变量之间的关系和相关性',
                'example': '找出影响销售的关键因素'
            },
            {
                'label': '预测分析',
                'description': '基于历史数据预测未来趋势',
                'example': '预测下个月的销售额'
            },
        ],
    }
    
    def __init__(self):
        """初始化选项生成器"""
        pass
    
    def generate(
        self,
        intent_analysis,
        current_node_id: str,
        context: Dict[str, Any] = None
    ) -> List[Option]:
        """
        生成澄清选项
        
        策略：
        - 根据缺失信息生成针对性选项
        - 通常3个具体选项 + 1个开放输入
        - 每个选项带示例说明
        
        Args:
            intent_analysis: 意图分析结果
            current_node_id: 当前节点ID
            context: 上下文信息
            
        Returns:
            List[Option]: 选项列表
        """
        context = context or {}
        
        task_type = getattr(intent_analysis, 'task_type', None)
        task_type_str = str(task_type) if task_type else 'general'
        entities = getattr(intent_analysis, 'extracted_entities', {}) or {}
        
        options = []
        option_id = 'A'
        
        # 1. 根据任务类型生成特定选项
        templates = self.OPTION_TEMPLATES.get(task_type_str, [])
        for template in templates[:3]:
            options.append(Option(
                id=option_id,
                label=template['label'],
                description=template['description'],
                example=template['example'],
                confidence=0.8,
                option_type=OptionType.SPECIFIC
            ))
            option_id = chr(ord(option_id) + 1)
        
        # 2. 如果选项不足3个，补充通用选项
        if len(options) < 3:
            generic_options = self._generate_generic_options(
                intent_analysis, entities
            )
            for opt in generic_options[:3 - len(options)]:
                opt.id = option_id
                options.append(opt)
                option_id = chr(ord(option_id) + 1)
        
        # 3. 添加开放输入选项
        options.append(Option(
            id=option_id,
            label='自定义输入',
            description='请用自己的话描述具体需求',
            example='我想要...',
            confidence=0.6,
            option_type=OptionType.OPEN
        ))
        
        return options
    
    def _generate_generic_options(
        self,
        intent_analysis,
        entities: Dict[str, Any]
    ) -> List[Option]:
        """生成通用选项"""
        options = []
        
        # 基于缺失实体生成选项
        if 'destination' not in entities:
            options.append(Option(
                id='',  # 稍后分配
                label='选择目的地',
                description='告诉我您想去哪里',
                example='北京、上海、杭州...',
                confidence=0.7
            ))
        
        if 'time' not in entities:
            options.append(Option(
                id='',
                label='确定时间',
                description='您计划什么时候进行',
                example='明天、下周、下个月...',
                confidence=0.7
            ))
        
        if 'budget' not in entities:
            options.append(Option(
                id='',
                label='设定预算',
                description='您的预算范围是多少',
                example='5000元以内、经济实惠...',
                confidence=0.7
            ))
        
        return options
    
    def generate_with_default(
        self,
        intent_analysis,
        current_node_id: str,
        default_option: Option
    ) -> List[Option]:
        """
        生成带默认推荐的选项
        
        Args:
            intent_analysis: 意图分析结果
            current_node_id: 当前节点ID
            default_option: 默认选项
            
        Returns:
            List[Option]: 选项列表（含推荐标记）
        """
        options = self.generate(intent_analysis, current_node_id)
        
        # 标记默认推荐
        for opt in options:
            if opt.id == default_option.id:
                opt.is_recommended = True
                opt.confidence = max(opt.confidence, 0.9)
        
        return options
    
    def generate_for_missing_entity(
        self,
        entity_type: str,
        entity_name: str,
        current_node_id: str
    ) -> List[Option]:
        """
        针对缺失实体生成选项
        
        Args:
            entity_type: 实体类型
            entity_name: 实体名称
            current_node_id: 当前节点ID
            
        Returns:
            List[Option]: 选项列表
        """
        # 根据实体类型生成特定选项
        entity_options = {
            'destination': [
                Option('A', '杭州', '西湖、灵隐寺、宋城', '西子湖畔赏景，品尝龙井茶', 0.85),
                Option('B', '苏州', '园林、古镇、水乡', '拙政园、周庄古镇、评弹欣赏', 0.82),
                Option('C', '厦门', '鼓浪屿、海滩、文艺', '海岛风光、文艺小资、海鲜美食', 0.80),
            ],
            'time': [
                Option('A', '本周末', '周六周日两天', '短途周末游，不用请假', 0.85),
                Option('B', '下周', '工作日出行', '人少价格低，体验更好', 0.80),
                Option('C', '下个月', '提前规划', '有更充裕的时间准备', 0.75),
            ],
            'style': [
                Option('A', '悠闲舒适', '慢节奏，不赶路', '充分休息，享受过程', 0.85),
                Option('B', '紧凑充实', '多景点，丰富体验', '行程满满，不留遗憾', 0.80),
                Option('C', '深度体验', '少而精，深入了解', '专注几个地方，深度游玩', 0.78),
            ],
        }
        
        options = entity_options.get(entity_type, [])
        
        # 添加自定义选项
        if options:
            options.append(Option(
                chr(ord('A') + len(options)),
                '其他',
                f'自定义{entity_name}',
                '请输入您的具体选择',
                0.6,
                option_type=OptionType.OPEN
            ))
        
        return options


# 便捷函数
def generate_options(
    intent_analysis,
    current_node_id: str,
    context: Dict[str, Any] = None
) -> List[Option]:
    """便捷函数：生成选项"""
    generator = OptionGenerator()
    return generator.generate(intent_analysis, current_node_id, context)
