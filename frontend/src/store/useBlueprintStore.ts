import { create } from 'zustand';
import type { BlueprintState, AppPhase, ThinkingNodeType, ExecutionStep } from '@/types';
import { defaultCanvasConfig } from '@/types';
import { generateThinkingNode, generateExecutionBlueprint } from '@/mock/mockEngine';

const initialState = {
  phase: 'input' as AppPhase,
  userInput: '',
  thinkingNodes: [] as ThinkingNodeType[],
  currentThinkingIndex: 0,
  selectedThinkingNodeId: null as string | null,
  executionSteps: [] as ExecutionStep[],
  selectedExecutionStepId: null as string | null,
  showInterventionPanel: false,
  interventionStepId: null as string | null,
  canvasConfig: defaultCanvasConfig,
  
  // 实时模式标志
  isRealtimeMode: false,
  isConnected: false,
  currentTaskId: null as string | null,
  currentBlueprintId: null as string | null,
  // 过渡 UI 状态（从 WS 消息同步）
  isGeneratingBlueprint: false,
  showConfirmExecution: false,
  
  // 冻结 / 截图 / 标注
  freeze: {
    isFrozen: false,
    freezeToken: null as string | null,
    stepId: null as string | null,
    screenshot: null as string | null,
    annotations: [] as any[],
  },
  screenshots: [] as { stepId: string; image: string; timestamp: number }[],
};

export const useBlueprintStore = create<BlueprintState & {
  // 实时模式控制
  isRealtimeMode: boolean;
  isConnected: boolean;
  currentTaskId: string | null;
  currentBlueprintId: string | null;
  setRealtimeMode: (enabled: boolean) => void;
  setConnectionStatus: (connected: boolean) => void;
  setCurrentTaskId: (taskId: string | null) => void;
  setCurrentBlueprintId: (blueprintId: string | null) => void;
  setIsGeneratingBlueprint: (value: boolean) => void;
  setShowConfirmExecution: (value: boolean) => void;
  
  // 外部状态同步
  setThinkingNodes: (nodes: ThinkingNodeType[]) => void;
  setExecutionSteps: (steps: ExecutionStep[]) => void;
  setPhase: (phase: AppPhase) => void;
  updateThinkingNode: (nodeId: string, updates: Partial<ThinkingNodeType>) => void;
  updateExecutionStep: (stepId: string, updates: Partial<ExecutionStep>) => void;
}>((set, get) => ({
  ...initialState,

  setUserInput: (input) => set({ userInput: input }),
  
  startThinking: () => {
    const { isRealtimeMode } = get();
    if (isRealtimeMode) {
      // 实时模式下不生成 mock 节点，等待后端推送
      set({
        phase: 'thinking',
        thinkingNodes: [],
        currentThinkingIndex: 0,
        selectedThinkingNodeId: null,
      });
      return;
    }
    const firstNode = generateThinkingNode(0);
    set({
      phase: 'thinking',
      thinkingNodes: [firstNode],
      currentThinkingIndex: 0,
      selectedThinkingNodeId: firstNode.id,
    });
  },
  
  selectThinkingOption: (nodeId, optionId) => {
    const { thinkingNodes, currentThinkingIndex, isRealtimeMode } = get();
    
    // 实时模式下不自动生成节点，等待后端推送
    if (isRealtimeMode) {
      set({
        thinkingNodes: thinkingNodes.map((node) => {
          if (node.id === nodeId) {
            return { ...node, status: 'selected' as const, selectedOption: optionId };
          }
          return node;
        }),
      });
      return;
    }
    
    // Mock 模式下的原有逻辑
    const updatedNodes = thinkingNodes.map((node) => {
      if (node.id === nodeId) {
        return { ...node, status: 'selected' as const, selectedOption: optionId };
      }
      return node;
    });
    
    if (currentThinkingIndex >= 2) {
      set({ thinkingNodes: updatedNodes });
      setTimeout(() => {
        get().completeThinking();
      }, 500);
    } else {
      const nextNode = generateThinkingNode(currentThinkingIndex + 1);
      set({
        thinkingNodes: [...updatedNodes, nextNode],
        currentThinkingIndex: currentThinkingIndex + 1,
        selectedThinkingNodeId: nextNode.id,
      });
    }
  },
  
  setCustomInput: (nodeId, input) => {
    const { thinkingNodes, currentThinkingIndex, isRealtimeMode } = get();
    
    if (isRealtimeMode) {
      set({
        thinkingNodes: thinkingNodes.map((node) => {
          if (node.id === nodeId) {
            return { ...node, status: 'selected' as const, customInput: input };
          }
          return node;
        }),
      });
      return;
    }
    
    const updatedNodes = thinkingNodes.map((node) => {
      if (node.id === nodeId) {
        return { ...node, status: 'selected' as const, customInput: input };
      }
      return node;
    });
    
    if (currentThinkingIndex >= 2) {
      set({ thinkingNodes: updatedNodes });
      setTimeout(() => {
        get().completeThinking();
      }, 500);
    } else {
      const nextNode = generateThinkingNode(currentThinkingIndex + 1);
      set({
        thinkingNodes: [...updatedNodes, nextNode],
        currentThinkingIndex: currentThinkingIndex + 1,
        selectedThinkingNodeId: nextNode.id,
      });
    }
  },

  selectThinkingNode: (nodeId) => {
    set({ selectedThinkingNodeId: nodeId });
  },

  completeThinking: () => {
    const { canvasConfig, isRealtimeMode } = get();
    
    if (isRealtimeMode) {
      // 实时模式下等待后端推送蓝图
      set({ phase: 'thinking' });
      return;
    }
    
    const steps = generateExecutionBlueprint(canvasConfig.executionNodeSpacing);
    set({
      phase: 'execution',
      executionSteps: steps,
      selectedExecutionStepId: steps[0]?.id || null,
    });
    
    setTimeout(() => {
      get().executeNextStep();
    }, 500);
  },
  
  startExecution: () => {
    const { canvasConfig, isRealtimeMode } = get();
    
    if (isRealtimeMode) {
      // 实时模式下由后端控制执行
      return;
    }
    
    const steps = generateExecutionBlueprint(canvasConfig.executionNodeSpacing);
    set({ executionSteps: steps });
    get().executeNextStep();
  },
  
  executeNextStep: () => {
    const { executionSteps, isRealtimeMode } = get();
    
    if (isRealtimeMode) {
      // 实时模式下由后端推送状态更新
      return;
    }
    
    // Mock 模式下的执行逻辑
    const readySteps = executionSteps.filter(step => {
      if (step.status !== 'pending') return false;
      return step.dependencies.every(depId => {
        const dep = executionSteps.find(s => s.id === depId);
        return dep?.status === 'completed';
      });
    });
    
    const mainSteps = readySteps.filter(s => s.isMainPath);
    const branchSteps = mainSteps.length === 0 ? readySteps.filter(s => !s.isMainPath) : [];
    const finalSteps = [...mainSteps, ...branchSteps];
    
    if (finalSteps.length === 0) {
      const pendingSteps = executionSteps.filter(s => s.status === 'pending');
      const runningSteps = executionSteps.filter(s => s.status === 'running');
      
      if (pendingSteps.length === 0 && runningSteps.length === 0) {
        if (!executionSteps.some(s => s.id === 'summary')) {
          const lastCompletedStep = executionSteps.filter(s => s.status === 'completed').pop();
          const summaryStep: ExecutionStep = {
            id: 'summary',
            name: '执行摘要',
            description: '点击查看执行结果',
            status: 'completed',
            dependencies: lastCompletedStep ? [lastCompletedStep.id] : [],
            position: { x: 800, y: 200 },
            result: '执行完成',
            isMainPath: true,
          };
          set({
            executionSteps: [...executionSteps, summaryStep],
            phase: 'completed',
          });
        }
      }
      return;
    }
    
    finalSteps.forEach(step => {
      set({
        executionSteps: executionSteps.map(s => 
          s.id === step.id ? { ...s, status: 'running' as const } : s
        ),
      });
      
      setTimeout(() => {
        const { executionSteps: updatedSteps } = get();
        
        if (step.id === 'step_003') {
          set({
            executionSteps: updatedSteps.map(s => 
              s.id === step.id 
                ? { ...s, status: 'failed' as const, needsIntervention: true }
                : s
            ),
          });
        } else {
          set({
            executionSteps: updatedSteps.map(s => 
              s.id === step.id ? { ...s, status: 'completed' as const, result: '完成' } : s
            ),
          });
          
          setTimeout(() => {
            get().executeNextStep();
          }, 800);
        }
      }, 2000);
    });
  },
  
  selectExecutionStep: (stepId) => {
    set({ selectedExecutionStepId: stepId });
  },
  
  interveneExecution: async (stepId) => {
    const { executionSteps, isRealtimeMode } = get();
    
    if (isRealtimeMode) {
      // 实时模式下由后端处理干预
      set({ 
        showInterventionPanel: true, 
        interventionStepId: stepId 
      });
      return;
    }
    
    const stepIndex = executionSteps.findIndex(s => s.id === stepId);
    const stepsBeforeAndIncluding = executionSteps.slice(0, stepIndex + 1);
    const completedSteps = stepsBeforeAndIncluding.filter(s => s.status === 'completed');
    const currentStep = executionSteps.find(s => s.id === stepId);
    
    const contextSummary = completedSteps.map(s => `${s.name}: ${s.result || '完成'}`).join('; ');
    const currentStepName = currentStep?.name || '当前步骤';
    const interventionQuestion = `在"${currentStepName}"处重新规划。已完成: ${contextSummary}。如何调整后续执行？`;
    
    const { generateThinkingNode } = await import('@/mock/mockEngine');
    const interventionNode = generateThinkingNode(0, interventionQuestion);
    
    set({
      phase: 'thinking',
      thinkingNodes: [interventionNode],
      currentThinkingIndex: 0,
      selectedThinkingNodeId: interventionNode.id,
      executionSteps: executionSteps.map((s, idx) => 
        idx <= stepIndex ? { ...s, isArchived: true } : s
      ),
      showInterventionPanel: false,
      interventionStepId: null,
    });
  },
  
  handleIntervention: (action, customInput) => {
    const { interventionStepId, executionSteps, isRealtimeMode } = get();
    if (!interventionStepId) return;
    
    if (isRealtimeMode) {
      // 实时模式下发送 WS 消息已由 BlueprintCanvas 处理，这里仅关闭面板
      set({ showInterventionPanel: false, interventionStepId: null });
      return;
    }
    
    switch (action) {
      case 'continue':
        set({
          executionSteps: executionSteps.map(s => 
            s.id === interventionStepId 
              ? { ...s, status: 'completed' as const, needsIntervention: false, result: '已继续' }
              : s
          ),
          showInterventionPanel: false,
          interventionStepId: null,
        });
        setTimeout(() => {
          get().executeNextStep();
        }, 500);
        break;
        
      case 'newBranch':
        const stepIndex = executionSteps.findIndex(s => s.id === interventionStepId);
        const newBranchSteps: ExecutionStep[] = [
          {
            id: `new_${Date.now()}_1`,
            name: '替代方案A',
            description: '用户干预生成的新步骤',
            status: 'pending',
            dependencies: [interventionStepId],
            position: { x: 400, y: 300 },
            isMainPath: false,
          },
          {
            id: `new_${Date.now()}_2`,
            name: '替代方案B',
            description: '用户干预生成的新步骤',
            status: 'pending',
            dependencies: [interventionStepId],
            position: { x: 600, y: 300 },
            isMainPath: false,
          },
        ];
        
        set({
          executionSteps: [
            ...executionSteps.slice(0, stepIndex + 1),
            ...newBranchSteps,
            ...executionSteps.slice(stepIndex + 1),
          ].map(s => s.id === interventionStepId ? { ...s, needsIntervention: false } : s),
          showInterventionPanel: false,
          interventionStepId: null,
        });
        
        setTimeout(() => {
          get().executeNextStep();
        }, 500);
        break;
        
      case 'stop':
        set({
          phase: 'completed',
          showInterventionPanel: false,
          interventionStepId: null,
        });
        break;
    }
  },
  
  hideIntervention: () => {
    set({
      showInterventionPanel: false,
      interventionStepId: null,
    });
  },
  
  reset: () => {
    set({ ...initialState });
  },
  
  // 冻结 / 截图 / 标注
  setFreezeState: (state) => {
    set((prev) => ({
      freeze: { ...prev.freeze, ...state },
    }));
  },
  addScreenshot: (screenshot) => {
    set((prev) => ({
      screenshots: [...prev.screenshots, screenshot],
    }));
  },
  clearScreenshots: () => set({ screenshots: [] }),
  clearFreeze: () => set({
    freeze: {
      isFrozen: false,
      freezeToken: null,
      stepId: null,
      screenshot: null,
      annotations: [],
    },
  }),
  
  // 画布配置操作
  updateCanvasConfig: (config) => {
    set((state) => {
      const newConfig = { ...state.canvasConfig, ...config };
      
      let updatedExecutionSteps = state.executionSteps;
      const spacingChanged = config.executionNodeSpacing !== undefined && 
          config.executionNodeSpacing !== state.canvasConfig.executionNodeSpacing;
      
      if (spacingChanged && state.executionSteps.length > 0) {
        updatedExecutionSteps = regenerateExecutionPositions(
          state.executionSteps, 
          newConfig.executionNodeSpacing
        );
      }
      
      return {
        canvasConfig: newConfig,
        executionSteps: updatedExecutionSteps,
      };
    });
  },
  
  resetCanvasConfig: () => {
    set({ canvasConfig: defaultCanvasConfig });
  },

  // ============ 实时模式方法 ============
  setRealtimeMode: (enabled) => set({ isRealtimeMode: enabled }),
  setConnectionStatus: (connected) => set({ isConnected: connected }),
  setCurrentTaskId: (taskId) => set({ currentTaskId: taskId }),
  setCurrentBlueprintId: (blueprintId) => set({ currentBlueprintId: blueprintId }),
  setIsGeneratingBlueprint: (value) => set({ isGeneratingBlueprint: value }),
  setShowConfirmExecution: (value) => set({ showConfirmExecution: value }),
  
  // 外部状态同步
  setThinkingNodes: (nodes) => set({ thinkingNodes: nodes }),
  setExecutionSteps: (steps) => set({ executionSteps: steps }),
  setPhase: (phase) => set({ phase }),
  
  updateThinkingNode: (nodeId, updates) => {
    set((state) => ({
      thinkingNodes: state.thinkingNodes.map(n => 
        n.id === nodeId ? { ...n, ...updates } : n
      ),
    }));
  },
  
  updateExecutionStep: (stepId, updates) => {
    set((state) => ({
      executionSteps: state.executionSteps.map(s => 
        s.id === stepId ? { ...s, ...updates } : s
      ),
    }));
  },
}));

// 开发环境下暴露 store 到 window 以便调试和测试
if (typeof window !== 'undefined') {
  (window as any).__BLUECLAW_STORE__ = useBlueprintStore.getState();
  (window as any).__BLUECLAW_SET__ = (updater: any) => useBlueprintStore.setState(updater);
  // 订阅更新
  useBlueprintStore.subscribe((state) => {
    (window as any).__BLUECLAW_STORE__ = state;
  });
}

// 重新计算执行蓝图节点位置
function regenerateExecutionPositions(
  steps: ExecutionStep[], 
  spacing: number
): ExecutionStep[] {
  const START_X = 20;
  const MAIN_Y = 80;
  const BRANCH_Y_START = MAIN_Y + spacing;
  const SPACING = spacing;
  
  const getStepIndex = (id: string): number => {
    const match = id.match(/(\d+)/);
    return match ? parseInt(match[1]) : 0;
  };
  
  return steps.map((step) => {
    const stepIndex = getStepIndex(step.id);
    let newPosition = step.position;
    
    if (step.id.startsWith('step_')) {
      newPosition = { x: START_X + SPACING * (stepIndex - 1), y: MAIN_Y };
    } else if (step.id.startsWith('branch_')) {
      const branchIndex = stepIndex - 1;
      newPosition = { x: START_X + SPACING * 2, y: BRANCH_Y_START + SPACING * branchIndex };
    }
    
    return { ...step, position: newPosition };
  });
}
