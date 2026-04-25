// Blueclaw AI Canvas - Type Definitions

export interface ThinkingOption {
  id: string;
  label: string;
  description: string;
  confidence: number;
  isDefault?: boolean;
}

export interface ThinkingNodeType {
  id: string;
  question: string;
  options: ThinkingOption[];
  allowCustom: boolean;
  status: 'pending' | 'selected';
  selectedOption?: string;
  customInput?: string;
  associatedTools?: string[];
}

export interface ExecutionStep {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  dependencies: string[];
  result?: string;
  error?: string;
  position: { x: number; y: number };
  needsIntervention?: boolean;
  isMainPath?: boolean;
  isConvergence?: boolean;
  convergenceType?: 'parallel' | 'sequential';
  isArchived?: boolean; // 已归档（干预后保留的已完成步骤）
  associatedTools?: string[]; // 关联的黄色方块ID列表
}

export type AppPhase = 'input' | 'thinking' | 'execution' | 'completed';

// 画布配置参数
export interface CanvasConfig {
  // 左右比例 (思考:执行) = 1 : leftRightRatio
  leftRightRatio: number; // 默认 √5 ≈ 2.236
  // 执行区域上下比例 (执行蓝图:视觉) = 1 : execTopBottomRatio  
  execTopBottomRatio: number; // 默认 2
  // 思考蓝图初始缩放比例
  thinkingCanvasZoom: number; // 默认 1
  // 执行蓝图初始缩放比例
  executionCanvasZoom: number; // 默认 1
  // 画布背景样式
  canvasBackground: 'gradient' | 'solid' | 'grid' | 'dots';
  // 背景颜色 (solid模式用)
  backgroundColor: string;
  // 思考蓝图节点垂直间距
  thinkingNodeSpacing: number; // 默认 180
  // 执行蓝图节点统一间距（水平/垂直）
  executionNodeSpacing: number; // 默认 140
}

export const defaultCanvasConfig: CanvasConfig = {
  leftRightRatio: 2.236, // √5
  execTopBottomRatio: 2, // 1:2
  thinkingCanvasZoom: 1,
  executionCanvasZoom: 1,
  canvasBackground: 'gradient',
  backgroundColor: '#0f172a',
  thinkingNodeSpacing: 180,
  executionNodeSpacing: 140,
};

export interface BlueprintState {
  phase: AppPhase;
  userInput: string;
  thinkingNodes: ThinkingNodeType[];
  currentThinkingIndex: number;
  selectedThinkingNodeId: string | null;
  executionSteps: ExecutionStep[];
  selectedExecutionStepId: string | null;
  showInterventionPanel: boolean;
  interventionStepId: string | null;
  
  setUserInput: (input: string) => void;
  startThinking: () => void;
  selectThinkingOption: (nodeId: string, optionId: string) => void;
  setCustomInput: (nodeId: string, input: string) => void;
  selectThinkingNode: (nodeId: string | null) => void;
  completeThinking: () => void;
  startExecution: () => void;
  executeNextStep: () => void;
  selectExecutionStep: (stepId: string | null) => void;
  interveneExecution: (stepId: string) => void;
  handleIntervention: (action: 'continue' | 'newBranch' | 'stop') => void;
  hideIntervention: () => void;
  reset: () => void;
  
  // 画布配置
  canvasConfig: CanvasConfig;
  updateCanvasConfig: (config: Partial<CanvasConfig>) => void;
  resetCanvasConfig: () => void;

  // 工具关联
  addToolToThinkingNode: (nodeId: string, toolId: string) => void;
  removeToolFromThinkingNode: (nodeId: string, toolId: string) => void;
  addToolToExecutionStep: (stepId: string, toolId: string) => void;
  removeToolFromExecutionStep: (stepId: string, toolId: string) => void;
}
