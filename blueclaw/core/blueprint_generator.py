# -*- coding: utf-8 -*-
"""
blueprint_generator.py - 执行蓝图生成器

职责: 从思考结果生成执行步骤
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ExecutionStep:
    """执行步骤"""
    step_id: str
    name: str
    description: str
    direction: str  # AI要做什么
    expected_result: str  # 预期结果
    validation_rule: str  # 验证规则
    tool: str  # 使用的工具/Skill
    dependencies: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class BlueprintGenerator:
    """执行蓝图生成器"""
    
    # 任务类型到步骤模板的映射
    STEP_TEMPLATES = {
        'travel_planning': [
            {
                'name': '查询目的地信息',
                'description': '获取目的地的天气、交通等基本信息',
                'direction': '搜索{destination}的最新天气、交通状况',
                'expected_result': '获取天气、交通等基础信息',
                'validation_rule': '非空',
                'tool': 'search'
            },
            {
                'name': '搜索景点推荐',
                'description': '根据偏好搜索推荐景点',
                'direction': '搜索{destination}的{style}风格景点推荐',
                'expected_result': '获得景点列表和介绍',
                'validation_rule': '非空',
                'tool': 'search'
            },
            {
                'name': '规划路线',
                'description': '制定合理的游览路线',
                'direction': '根据景点位置规划最优游览路线',
                'expected_result': '生成路线规划方案',
                'validation_rule': '非空',
                'tool': 'code'
            },
            {
                'name': '生成行程文档',
                'description': '整合信息生成完整行程',
                'direction': '生成包含路线、时间、注意事项的行程文档',
                'expected_result': '完整的行程计划文档',
                'validation_rule': '非空',
                'tool': 'file'
            },
        ],
        'code_generation': [
            {
                'name': '分析需求',
                'description': '理解并分析代码需求',
                'direction': '分析{function_type}的需求和约束条件',
                'expected_result': '明确的功能规格说明',
                'validation_rule': '非空',
                'tool': 'code'
            },
            {
                'name': '设计实现',
                'description': '设计代码结构和算法',
                'direction': '设计代码结构、接口和核心算法',
                'expected_result': '代码设计方案',
                'validation_rule': '非空',
                'tool': 'code'
            },
            {
                'name': '编写代码',
                'description': '实现核心功能代码',
                'direction': '用{language}编写实现代码',
                'expected_result': '可运行的代码',
                'validation_rule': '语法正确',
                'tool': 'code'
            },
            {
                'name': '测试验证',
                'description': '测试代码正确性',
                'direction': '编写并运行测试用例',
                'expected_result': '测试通过',
                'validation_rule': '无错误',
                'tool': 'code'
            },
        ],
        'file_operation': [
            {
                'name': '扫描目标文件',
                'description': '扫描目录中的目标文件',
                'direction': '扫描{path}中的文件',
                'expected_result': '文件列表',
                'validation_rule': '非空',
                'tool': 'file'
            },
            {
                'name': '分析文件属性',
                'description': '提取文件元数据',
                'direction': '分析文件的类型、大小、日期等属性',
                'expected_result': '文件属性信息',
                'validation_rule': '非空',
                'tool': 'file'
            },
            {
                'name': '执行文件操作',
                'description': '执行实际文件操作',
                'direction': '执行{operation}操作',
                'expected_result': '操作完成',
                'validation_rule': '无错误',
                'tool': 'file'
            },
            {
                'name': '生成操作报告',
                'description': '总结操作结果',
                'direction': '生成操作摘要报告',
                'expected_result': '操作报告',
                'validation_rule': '非空',
                'tool': 'file'
            },
        ],
        'data_analysis': [
            {
                'name': '加载数据',
                'description': '读取并解析数据文件',
                'direction': '加载{data_source}中的数据',
                'expected_result': '数据结构',
                'validation_rule': '非空',
                'tool': 'file'
            },
            {
                'name': '数据清洗',
                'description': '处理缺失值和异常',
                'direction': '清洗数据，处理缺失值和异常',
                'expected_result': '清洗后的数据',
                'validation_rule': '数据完整',
                'tool': 'code'
            },
            {
                'name': '数据分析',
                'description': '执行统计分析',
                'direction': '执行{analysis_type}分析',
                'expected_result': '分析结果',
                'validation_rule': '非空',
                'tool': 'code'
            },
            {
                'name': '生成报告',
                'description': '生成可视化报告',
                'direction': '生成图表和分析报告',
                'expected_result': '报告文档',
                'validation_rule': '非空',
                'tool': 'file'
            },
        ],
    }
    
    def generate(
        self,
        thinking_chain,
        intent_analysis
    ) -> List[ExecutionStep]:
        """
        根据思考链生成执行步骤
        
        Args:
            thinking_chain: 思考链
            intent_analysis: 意图分析结果
            
        Returns:
            List[ExecutionStep]: 执行步骤列表
        """
        # 获取提取的信息
        extracted_info = thinking_chain.get_extracted_information() if thinking_chain else {}
        
        # 获取任务类型
        task_type = getattr(intent_analysis, 'task_type', None)
        task_type_str = str(task_type) if task_type else 'general'
        
        # 获取步骤模板
        templates = self.STEP_TEMPLATES.get(task_type_str, self._get_default_templates())
        
        # 生成步骤
        steps = []
        prev_step_id = None
        
        for i, template in enumerate(templates):
            step_id = f"step_{i+1:03d}"
            
            # 格式化模板内容
            direction = self._format_template(template['direction'], extracted_info)
            expected_result = self._format_template(template['expected_result'], extracted_info)
            
            step = ExecutionStep(
                step_id=step_id,
                name=template['name'],
                description=template['description'],
                direction=direction,
                expected_result=expected_result,
                validation_rule=template['validation_rule'],
                tool=template['tool'],
                dependencies=[prev_step_id] if prev_step_id else []
            )
            
            steps.append(step)
            prev_step_id = step_id
        
        return steps
    
    def _get_default_templates(self) -> List[Dict[str, str]]:
        """获取默认步骤模板"""
        return [
            {
                'name': '理解需求',
                'description': '分析和理解用户需求',
                'direction': '分析用户需求的细节和约束条件',
                'expected_result': '清晰的需求规格',
                'validation_rule': '非空',
                'tool': 'code'
            },
            {
                'name': '制定方案',
                'description': '制定执行方案',
                'direction': '根据需求制定详细执行方案',
                'expected_result': '可执行的方案',
                'validation_rule': '非空',
                'tool': 'code'
            },
            {
                'name': '执行操作',
                'description': '执行具体任务',
                'direction': '按照方案执行具体操作',
                'expected_result': '操作完成',
                'validation_rule': '无错误',
                'tool': 'shell'
            },
            {
                'name': '验证结果',
                'description': '验证执行结果',
                'direction': '检查结果是否符合预期',
                'expected_result': '验证通过',
                'validation_rule': '符合预期',
                'tool': 'code'
            },
        ]
    
    def _format_template(self, template: str, info: Dict[str, Any]) -> str:
        """格式化模板字符串"""
        result = template
        for key, value in info.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result
    
    def generate_preview(self, steps: List[ExecutionStep]) -> Dict[str, Any]:
        """
        生成执行预览（给用户确认）
        
        Args:
            steps: 执行步骤列表
            
        Returns:
            Dict[str, Any]: 预览信息
        """
        return {
            "total_steps": len(steps),
            "estimated_time": self._estimate_time(steps),
            "tools_required": list(set(s.tool for s in steps)),
            "steps_summary": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "tool": s.tool,
                    "description": s.description
                }
                for s in steps
            ]
        }
    
    def _estimate_time(self, steps: List[ExecutionStep]) -> str:
        """估算执行时间"""
        base_time = len(steps) * 30  # 每步30秒基础时间
        
        tool_multipliers = {
            'search': 20,
            'file': 10,
            'code': 45,
            'shell': 15,
        }
        
        for step in steps:
            base_time += tool_multipliers.get(step.tool, 20)
        
        # 格式化时间
        if base_time < 60:
            return f"约 {base_time} 秒"
        elif base_time < 3600:
            minutes = base_time // 60
            return f"约 {minutes} 分钟"
        else:
            hours = base_time // 3600
            minutes = (base_time % 3600) // 60
            return f"约 {hours} 小时 {minutes} 分钟"
    
    def reorder_steps(
        self,
        steps: List[ExecutionStep],
        new_order: List[str]
    ) -> List[ExecutionStep]:
        """
        重新排序步骤
        
        Args:
            steps: 原步骤列表
            new_order: 新的顺序（step_id 列表）
            
        Returns:
            List[ExecutionStep]: 重新排序后的步骤
        """
        step_map = {s.step_id: s for s in steps}
        return [step_map[sid] for sid in new_order if sid in step_map]


# 便捷函数
def generate_blueprint(
    thinking_chain,
    intent_analysis
) -> List[ExecutionStep]:
    """便捷函数：生成执行蓝图"""
    generator = BlueprintGenerator()
    return generator.generate(thinking_chain, intent_analysis)
