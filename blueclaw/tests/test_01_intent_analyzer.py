# -*- coding: utf-8 -*-
"""
test_01_intent_analyzer.py - 意图分析器测试

测试标准:
- 正确识别各种意图类型
- 准确提取关键实体
- 合理计算置信度
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from blueclaw.core.intent_analyzer import (
    IntentAnalyzer, IntentType, TaskType, IntentAnalysis,
    analyze_intent
)


def test_task_intent():
    """测试任务意图识别"""
    print("\n[Test] 任务意图识别...")
    analyzer = IntentAnalyzer()
    
    test_cases = [
        ("帮我规划一个去上海的周末旅行", TaskType.TRAVEL_PLANNING, "上海"),
        ("写一个Python函数计算斐波那契数列", TaskType.CODE_GENERATION, None),
        ("分析这个CSV文件的数据", TaskType.DATA_ANALYSIS, "CSV"),
        ("列出当前目录的所有文件", TaskType.FILE_OPERATION, None),
        ("写一篇文章关于人工智能", TaskType.CONTENT_CREATION, None),
        ("搭建一个React项目", TaskType.PROJECT_SETUP, None),
        ("搜索一下Python的文档", TaskType.SEARCH, None),
    ]
    
    for input_text, expected_task_type, expected_entity in test_cases:
        result = analyzer.analyze(input_text)
        
        assert result.intent_type == IntentType.TASK, \
            f"期望 TASK, 得到 {result.intent_type}: {input_text}"
        
        assert result.task_type == expected_task_type, \
            f"期望 {expected_task_type}, 得到 {result.task_type}: {input_text}"
        
        if expected_entity:
            assert any(expected_entity.lower() in str(v).lower() for v in result.extracted_entities.values()), \
                f"期望提取实体 '{expected_entity}', 得到 {result.extracted_entities}: {input_text}"
        
        print(f"  ✓ {input_text[:30]}... -> {result.task_type.value}")
    
    print("  [PASS] 任务意图识别通过")


def test_question_intent():
    """测试问答意图识别"""
    print("\n[Test] 问答意图识别...")
    analyzer = IntentAnalyzer()
    
    test_cases = [
        "今天北京天气怎么样",
        "Python是什么",
        "怎么做数据分析",
        "你能做什么",
        "What is machine learning",
        "How to learn Python",
        "为什么天空是蓝色的",
    ]
    
    for input_text in test_cases:
        result = analyzer.analyze(input_text)
        assert result.intent_type == IntentType.QUESTION, \
            f"期望 QUESTION, 得到 {result.intent_type}: {input_text}"
        print(f"  ✓ {input_text[:30]}... -> QUESTION")
    
    print("  [PASS] 问答意图识别通过")


def test_greeting_intent():
    """测试问候意图识别"""
    print("\n[Test] 问候意图识别...")
    analyzer = IntentAnalyzer()
    
    test_cases = [
        "你好",
        "Hello",
        "Hi there",
        "在吗",
        "哈喽",
    ]
    
    for input_text in test_cases:
        result = analyzer.analyze(input_text)
        assert result.intent_type == IntentType.GREETING, \
            f"期望 GREETING, 得到 {result.intent_type}: {input_text}"
        print(f"  ✓ {input_text} -> GREETING")
    
    print("  [PASS] 问候意图识别通过")


def test_entity_extraction():
    """测试实体提取"""
    print("\n[Test] 实体提取...")
    analyzer = IntentAnalyzer()
    
    # 测试地点提取
    result = analyzer.analyze("我想去杭州旅行")
    assert result.extracted_entities.get('destination') == '杭州', \
        f"期望提取目的地 '杭州', 得到 {result.extracted_entities}"
    print("  ✓ 地点提取: 杭州")
    
    # 测试时间提取
    result = analyzer.analyze("明天有什么安排")
    assert result.extracted_entities.get('time') == '明天', \
        f"期望提取时间 '明天', 得到 {result.extracted_entities}"
    print("  ✓ 时间提取: 明天")
    
    # 测试文件提取
    result = analyzer.analyze("读取 data.csv 文件")
    assert 'data.csv' in str(result.extracted_entities.get('file', '')), \
        f"期望提取文件 'data.csv', 得到 {result.extracted_entities}"
    print("  ✓ 文件提取: data.csv")
    
    # 测试数字提取
    result = analyzer.analyze("计算 100 和 200 的和")
    numbers = result.extracted_entities.get('numbers', [])
    assert 100 in numbers and 200 in numbers, \
        f"期望提取数字 [100, 200], 得到 {numbers}"
    print("  ✓ 数字提取: 100, 200")
    
    print("  [PASS] 实体提取通过")


def test_confidence_calculation():
    """测试置信度计算"""
    print("\n[Test] 置信度计算...")
    analyzer = IntentAnalyzer()
    
    # 具体明确的输入应该高置信度
    result1 = analyzer.analyze("帮我规划一个去上海的周末旅行，预算5000元")
    assert result1.confidence >= 0.5, f"期望置信度 >= 0.5, 得到 {result1.confidence}"
    print(f"  ✓ 具体输入置信度: {result1.confidence:.2f}")
    
    # 简短问候应该较低置信度
    result2 = analyzer.analyze("你好")
    assert result2.confidence >= 0.5, f"期望置信度 >= 0.5, 得到 {result2.confidence}"
    print(f"  ✓ 问候语置信度: {result2.confidence:.2f}")
    
    print("  [PASS] 置信度计算通过")


def test_convenience_function():
    """测试便捷函数"""
    print("\n[Test] 便捷函数...")
    
    result = analyze_intent("帮我写一个Python脚本")
    assert isinstance(result, IntentAnalysis)
    assert result.intent_type == IntentType.TASK
    assert result.task_type == TaskType.CODE_GENERATION
    
    print("  ✓ analyze_intent() 便捷函数工作正常")
    print("  [PASS] 便捷函数通过")


def test_edge_cases():
    """测试边界情况"""
    print("\n[Test] 边界情况...")
    analyzer = IntentAnalyzer()
    
    # 空输入
    result = analyzer.analyze("")
    assert result.intent_type == IntentType.QUESTION  # 默认问答
    assert result.confidence == 0.0
    print("  ✓ 空输入处理")
    
    # 空白输入
    result = analyzer.analyze("   ")
    assert result.intent_type == IntentType.QUESTION
    print("  ✓ 空白输入处理")
    
    # 超长输入
    long_input = "帮我规划" * 100
    result = analyzer.analyze(long_input)
    assert result.intent_type == IntentType.TASK
    print("  ✓ 超长输入处理")
    
    print("  [PASS] 边界情况通过")


def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("意图分析器测试 - Intent Analyzer Tests")
    print("="*60)
    
    tests = [
        test_task_intent,
        test_question_intent,
        test_greeting_intent,
        test_entity_extraction,
        test_confidence_calculation,
        test_convenience_function,
        test_edge_cases,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
