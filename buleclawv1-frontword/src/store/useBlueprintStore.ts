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
};

export const useBlueprintStore = create<BlueprintState>((set, get) => ({
  ...initialState,

  setUserInput: (input) => set({ userInput: input }),
  
  startThinking: () => {
    const firstNode = generateThinkingNode(0);
    set({
      phase: 'thinking',
      thinkingNodes: [firstNode],
      currentThinkingIndex: 0,
      selectedThinkingNodeId: firstNode.id,
    });
  },
  
  selectThinkingOption: (nodeId, optionId) => {
    const { thinkingNodes, currentThinkingIndex } = get();
    
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
    const { thinkingNodes, currentThinkingIndex } = get();
    
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
    const { canvasConfig } = get();
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
    const { canvasConfig } = get();
    const steps = generateExecutionBlueprint(canvasConfig.executionNodeSpacing);
    set({ executionSteps: steps });
    get().executeNextStep();
  },
  
  executeNextStep: () => {
    const { executionSteps } = get();
    
    // 找可以执行的步骤（依赖已完成）
    const readySteps = executionSteps.filter(step => {
      if (step.status !== 'pending') return false;
      return step.dependencies.every(depId => {
        const dep = executionSteps.find(s => s.id === depId);
        return dep?.status === 'completed';
      });
    });
    
    // 优先执行主路径
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
    
    // 执行步骤
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
  
  interveneExecution: (stepId) => {
    const { executionSteps } = get();
    
    // 找到当前步骤及其之前的已完成步骤
    const stepIndex = executionSteps.findIndex(s => s.id === stepId);
    const stepsBeforeAndIncluding = executionSteps.slice(0, stepIndex + 1);
    const completedSteps = stepsBeforeAndIncluding.filter(s => s.status === 'completed');
    const currentStep = executionSteps.find(s => s.id === stepId);
    
    // 生成新的思考节点，带上已执行的结果作为上下文
    const contextSummary = completedSteps.map(s => `${s.name}: ${s.result || '完成'}`).join('; ');
    const currentStepName = currentStep?.name || '当前步骤';
    const interventionQuestion = `在"${currentStepName}"处重新规划。已完成: ${contextSummary}。如何调整后续执行？`;
    
    const interventionNode = generateThinkingNode(0, interventionQuestion);
    
    set({
      phase: 'thinking',
      thinkingNodes: [interventionNode],
      currentThinkingIndex: 0,
      selectedThinkingNodeId: interventionNode.id,
      // 保留当前步骤及之前的步骤，标记为已归档
      executionSteps: executionSteps.map((s, idx) => 
        idx <= stepIndex ? { ...s, isArchived: true } : s
      ),
      showInterventionPanel: false,
      interventionStepId: null,
    });
  },
  
  handleIntervention: (action) => {
    const { interventionStepId, executionSteps } = get();
    if (!interventionStepId) return;
    
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
  
  // 画布配置操作
  updateCanvasConfig: (config) => {
    set((state) => {
      const newConfig = { ...state.canvasConfig, ...config };
      
      // 如果执行节点间距变化且执行蓝图已存在，重新计算节点位置
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

  // 工具关联操作
  addToolToThinkingNode: (nodeId, toolId) => {
    set((state) => ({
      thinkingNodes: state.thinkingNodes.map((node) =>
        node.id === nodeId
          ? { ...node, associatedTools: [...(node.associatedTools || []), toolId] }
          : node
      ),
    }));
  },

  removeToolFromThinkingNode: (nodeId, toolId) => {
    set((state) => ({
      thinkingNodes: state.thinkingNodes.map((node) =>
        node.id === nodeId
          ? { ...node, associatedTools: (node.associatedTools || []).filter((id) => id !== toolId) }
          : node
      ),
    }));
  },

  addToolToExecutionStep: (stepId, toolId) => {
    set((state) => ({
      executionSteps: state.executionSteps.map((step) =>
        step.id === stepId
          ? { ...step, associatedTools: [...(step.associatedTools || []), toolId] }
          : step
      ),
    }));
  },

  removeToolFromExecutionStep: (stepId, toolId) => {
    set((state) => ({
      executionSteps: state.executionSteps.map((step) =>
        step.id === stepId
          ? { ...step, associatedTools: (step.associatedTools || []).filter((id) => id !== toolId) }
          : step
      ),
    }));
  },
}));

// 重新计算执行蓝图节点位置（保留状态）
function regenerateExecutionPositions(
  steps: ExecutionStep[], 
  spacing: number
): ExecutionStep[] {
  const START_X = 20;
  const MAIN_Y = 80;
  const BRANCH_Y_START = MAIN_Y + spacing;
  const SPACING = spacing;
  
  // 提取步骤序号
  const getStepIndex = (id: string): number => {
    const match = id.match(/(\d+)/);
    return match ? parseInt(match[1]) : 0;
  };
  
  return steps.map((step) => {
    const stepIndex = getStepIndex(step.id);
    let newPosition = step.position;
    
    // 根据步骤类型和序号重新计算位置
    if (step.id.startsWith('step_')) {
      // 主路径节点 - 水平排列
      newPosition = { x: START_X + SPACING * (stepIndex - 1), y: MAIN_Y };
    } else if (step.id.startsWith('branch_')) {
      // 分支节点 - 垂直排列，与 step_003 同一X位置
      const branchIndex = stepIndex - 1; // branch_01 -> 0, branch_02 -> 1, branch_03 -> 2
      newPosition = { x: START_X + SPACING * 2, y: BRANCH_Y_START + SPACING * branchIndex };
    }
    
    return { ...step, position: newPosition };
  });
}
