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
  tool?: string; // 绑定的 Skill / 工具名称
}

export interface AnnotationBox {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  label?: string;
}

export interface FreezeState {
  isFrozen: boolean;
  freezeToken: string | null;
  stepId: string | null;
  screenshot: string | null; // base64 PNG
  annotations: AnnotationBox[];
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
  
  // 实时模式
  isRealtimeMode: boolean;
  isConnected: boolean;
  currentTaskId: string | null;
  currentBlueprintId: string | null;
  
  // 冻结 / 截图 / 标注
  freeze: FreezeState;
  screenshots: { stepId: string; image: string; timestamp: number }[];
  
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
  handleIntervention: (action: 'continue' | 'newBranch' | 'stop', customInput?: string) => void;
  hideIntervention: () => void;
  reset: () => void;
  
  // 画布配置
  canvasConfig: CanvasConfig;
  updateCanvasConfig: (config: Partial<CanvasConfig>) => void;
  resetCanvasConfig: () => void;
  
  // 实时模式控制
  setRealtimeMode: (enabled: boolean) => void;
  setConnectionStatus: (connected: boolean) => void;
  setCurrentTaskId: (taskId: string | null) => void;
  
  // 外部状态同步
  setThinkingNodes: (nodes: ThinkingNodeType[]) => void;
  setExecutionSteps: (steps: ExecutionStep[]) => void;
  setPhase: (phase: AppPhase) => void;
  updateThinkingNode: (nodeId: string, updates: Partial<ThinkingNodeType>) => void;
  updateExecutionStep: (stepId: string, updates: Partial<ExecutionStep>) => void;
  
  // 冻结 / 截图 / 标注
  setFreezeState: (state: Partial<FreezeState>) => void;
  addScreenshot: (screenshot: { stepId: string; image: string; timestamp: number }) => void;
  clearScreenshots: () => void;
  clearFreeze: () => void;
}
