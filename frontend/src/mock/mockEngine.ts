// Blueclaw AI Canvas - Mock Data Engine

import type { ThinkingNodeType, ExecutionStep, ThinkingOption } from '@/types';

let thinkingNodeCounter = 0;
let executionStepCounter = 0;

export function generateThinkingNode(index: number, customQuestion?: string): ThinkingNodeType {
  thinkingNodeCounter++;
  
  const questions = [
    '你想规划什么样的旅行？',
    '你计划去哪里旅行？',
    '你计划什么时候出发？',
  ];
  
  const defaultOptions: ThinkingOption[][] = [
    [
      { id: 'A', label: '自然风光', description: '山水、森林、户外活动', confidence: 0.85 },
      { id: 'B', label: '城市探索', description: '建筑、美食、文化体验', confidence: 0.78 },
      { id: 'C', label: '休闲度假', description: '温泉、海滩、慢生活', confidence: 0.72 },
    ],
    [
      { id: 'A', label: '杭州', description: '西湖、灵隐寺、龙井茶', confidence: 0.88, isDefault: true },
      { id: 'B', label: '苏州', description: '园林、古镇、小桥流水', confidence: 0.82 },
      { id: 'C', label: '黄山', description: '奇松、怪石、云海日出', confidence: 0.75 },
    ],
    [
      { id: 'A', label: '本周末', description: '2天1晚短途游', confidence: 0.90, isDefault: true },
      { id: 'B', label: '下周末', description: '提前规划更从容', confidence: 0.85 },
      { id: 'C', label: '国庆假期', description: '7天长假深度游', confidence: 0.70 },
    ],
  ];
  
  // 干预模式的选项
  const interventionOptions: ThinkingOption[] = [
    { id: 'A', label: '调整当前步骤', description: '修改当前执行策略', confidence: 0.85 },
    { id: 'B', label: '添加分支步骤', description: '并行执行额外任务', confidence: 0.78 },
    { id: 'C', label: '跳过当前步骤', description: '直接进入后续执行', confidence: 0.72 },
    { id: 'D', label: '完全重新规划', description: '基于已完成结果重新设计', confidence: 0.80 },
  ];
  
  const isIntervention = !!customQuestion;
  
  return {
    id: `thinking_${thinkingNodeCounter.toString().padStart(3, '0')}`,
    question: customQuestion || questions[index % questions.length],
    options: isIntervention ? interventionOptions : defaultOptions[index % defaultOptions.length],
    allowCustom: true,
    status: 'pending',
  };
}

// 生成多路径执行蓝图 - 正确汇合布局
// 布局设计：
// 主路径: 查询天气 → 搜索景点 → 规划交通 ──────→ 对比方案 → 推荐酒店 → 生成行程
//                          │                      ↗
//                          ├────→ 查询高铁 ──────┘
//                          │
//                          ├────→ 查询航班 ──────┘
//                          │
//                          └────→ 查询自驾 ──────┘
export function generateExecutionBlueprint(
  spacing: number = 140
): ExecutionStep[] {
  executionStepCounter = 0;
  
  const steps: ExecutionStep[] = [];
  
  // 布局参数 - 使用统一的间距
  const START_X = 20;           // 起始X坐标
  const MAIN_Y = 80;            // 主路径Y坐标
  const BRANCH_Y_START = MAIN_Y + spacing;  // 分支起始Y坐标
  const SPACING = spacing;      // 统一间距
  
  // ===== 主路径 =====
  // 1. 查询天气
  executionStepCounter++;
  steps.push({
    id: `step_${executionStepCounter.toString().padStart(3, '0')}`,
    name: '查询天气',
    description: '获取目的地未来3天天气预报',
    status: 'pending',
    dependencies: [],
    position: { x: START_X, y: MAIN_Y },
    isMainPath: true,
  });
  
  // 2. 搜索景点
  executionStepCounter++;
  steps.push({
    id: `step_${executionStepCounter.toString().padStart(3, '0')}`,
    name: '搜索景点',
    description: '查找当地热门景点和必去打卡地',
    status: 'pending',
    dependencies: ['step_001'],
    position: { x: START_X + SPACING, y: MAIN_Y },
    isMainPath: true,
  });
  
  // 3. 规划交通 (分支起点)
  executionStepCounter++;
  steps.push({
    id: `step_${executionStepCounter.toString().padStart(3, '0')}`,
    name: '规划交通',
    description: '规划从出发地到目的地的最佳路线',
    status: 'pending',
    dependencies: ['step_002'],
    position: { x: START_X + SPACING * 2, y: MAIN_Y },
    isMainPath: true,
  });
  
  // ===== 分路径（都依赖规划交通，都汇合到对比方案）=====
  // 4. 查询高铁
  executionStepCounter++;
  steps.push({
    id: `branch_${(1).toString().padStart(2, '0')}`,
    name: '查询高铁',
    description: '搜索高铁班次和票价信息',
    status: 'pending',
    dependencies: ['step_003'],
    position: { x: START_X + SPACING * 2, y: BRANCH_Y_START },
    isMainPath: false,
  });
  
  // 5. 查询航班
  executionStepCounter++;
  steps.push({
    id: `branch_${(2).toString().padStart(2, '0')}`,
    name: '查询航班',
    description: '搜索航班时刻和价格',
    status: 'pending',
    dependencies: ['step_003'],
    position: { x: START_X + SPACING * 2, y: BRANCH_Y_START + SPACING },
    isMainPath: false,
  });
  
  // 6. 查询自驾
  executionStepCounter++;
  steps.push({
    id: `branch_${(3).toString().padStart(2, '0')}`,
    name: '查询自驾',
    description: '计算自驾路线和预计成本',
    status: 'pending',
    dependencies: ['step_003'],
    position: { x: START_X + SPACING * 2, y: BRANCH_Y_START + SPACING * 2 },
    isMainPath: false,
  });
  
  // ===== 汇合点 =====
  // 7. 对比方案（汇合所有分支）- 使用统一间距
  executionStepCounter++;
  steps.push({
    id: `step_${executionStepCounter.toString().padStart(3, '0')}`,
    name: '对比方案',
    description: '对比高铁/航班/自驾的成本和时间',
    status: 'pending',
    dependencies: ['branch_01', 'branch_02', 'branch_03'],
    position: { x: START_X + SPACING * 3, y: MAIN_Y },
    isMainPath: true,
    isConvergence: true,
    convergenceType: 'parallel',
  });
  
  // 8. 推荐酒店
  executionStepCounter++;
  steps.push({
    id: `step_${executionStepCounter.toString().padStart(3, '0')}`,
    name: '推荐酒店',
    description: '根据预算和位置推荐合适的住宿',
    status: 'pending',
    dependencies: ['step_004'],
    position: { x: START_X + SPACING * 4, y: MAIN_Y },
    isMainPath: true,
  });
  
  // 9. 生成行程
  executionStepCounter++;
  steps.push({
    id: `step_${executionStepCounter.toString().padStart(3, '0')}`,
    name: '生成行程',
    description: '整合所有信息生成完整行程单',
    status: 'pending',
    dependencies: ['step_005'],
    position: { x: START_X + SPACING * 5, y: MAIN_Y },
    isMainPath: true,
  });
  
  return steps;
}

export function resetCounters(): void {
  thinkingNodeCounter = 0;
  executionStepCounter = 0;
}
