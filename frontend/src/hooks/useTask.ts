/**
 * useTask Hook
 * 管理任务生命周期和 WebSocket 通信
 */
import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import type { ThinkingNodeType, ExecutionStep } from '@/types';

export interface Task {
  id: string;
  userInput: string;
  status: 'THINKING' | 'EXECUTING' | 'COMPLETED' | 'PAUSED';
  currentBlueprintId?: string;
}

export function useTask() {
  const { send, lastMessage, isConnected } = useWebSocket();
  
  const [currentTask, setCurrentTask] = useState<Task | null>(null);
  const [thinkingNodes, setThinkingNodes] = useState<ThinkingNodeType[]>([]);
  const [executionSteps, setExecutionSteps] = useState<ExecutionStep[]>([]);
  const [phase, setPhase] = useState<'input' | 'thinking' | 'execution' | 'completed'>('input');
  const [isLoading, setIsLoading] = useState(false);
  
  // 用于缓存消息队列（如果需要）
  // const messageQueueRef = useRef<WebSocketMessage[]>([]);

  // 处理 WebSocket 消息
  useEffect(() => {
    if (!lastMessage) return;

    console.log('[useTask] Received:', lastMessage.type, lastMessage.payload);

    switch (lastMessage.type) {
      // Task 相关
      case 'task.started':
        const taskData = lastMessage.payload;
        setCurrentTask({
          id: taskData.task_id,
          userInput: taskData.user_input,
          status: 'THINKING'
        });
        setPhase('thinking');
        setIsLoading(false);
        break;

      case 'task.interrupted':
        setCurrentTask(prev => prev ? { ...prev, status: 'PAUSED' } : null);
        break;

      // Thinking 相关
      case 'thinking.node_created':
        const newNode = lastMessage.payload?.node;
        if (newNode) {
          const thinkingNode: ThinkingNodeType = {
            id: newNode.id,
            question: newNode.question,
            options: newNode.options?.map((o: any) => ({
              id: o.id,
              label: o.label,
              description: o.description,
              confidence: o.confidence,
              isDefault: o.is_default
            })) || [],
            allowCustom: newNode.allow_custom ?? true,
            status: 'pending',
          };
          setThinkingNodes(prev => [...prev, thinkingNode]);
        }
        break;

      case 'thinking.option_selected':
        // 更新节点状态
        const { option_id, has_more_options } = lastMessage.payload || {};
        if (option_id) {
          setThinkingNodes(prev => 
            prev.map(n => n.status === 'pending' ? { ...n, status: 'selected' as const, selectedOption: option_id } : n)
          );
        }
        if (!has_more_options) {
          // 思考完成，等待确认执行
        }
        break;

      case 'thinking.completed':
        const finalPath = lastMessage.payload?.final_path || [];
        console.log('[useTask] Thinking completed, final path:', finalPath);
        break;

      case 'thinking.execution_confirmed':
        // 执行已确认，等待蓝图加载
        break;

      // Execution 相关
      case 'execution.blueprint_loaded':
        const blueprint = lastMessage.payload?.blueprint;
        if (blueprint?.steps) {
          const steps: ExecutionStep[] = blueprint.steps.map((s: any) => ({
            id: s.id,
            name: s.name,
            description: s.description,
            status: s.status?.toLowerCase() || 'pending',
            dependencies: s.dependencies || [],
            position: s.position || { x: 0, y: 0 },
            isMainPath: s.is_main_path ?? true,
            isConvergence: s.is_convergence ?? false,
            convergenceType: s.convergence_type,
            result: s.result,
            needsIntervention: s.needs_intervention ?? false,
            isArchived: s.is_archived ?? false,
          }));
          setExecutionSteps(steps);
          setPhase('execution');
          setCurrentTask(prev => prev ? { 
            ...prev, 
            status: 'EXECUTING',
            currentBlueprintId: blueprint.id 
          } : null);
        }
        break;

      case 'execution.started':
        setCurrentTask(prev => prev ? { ...prev, status: 'EXECUTING' } : null);
        break;

      case 'execution.step_updated':
        const updatedStep = lastMessage.payload?.step;
        if (updatedStep) {
          setExecutionSteps(prev => 
            prev.map(s => s.id === updatedStep.id ? { 
              ...s, 
              status: updatedStep.status?.toLowerCase() || s.status,
              result: updatedStep.result,
              needsIntervention: updatedStep.needs_intervention
            } : s)
          );
        }
        break;

      case 'execution.paused':
        setCurrentTask(prev => prev ? { ...prev, status: 'PAUSED' } : null);
        break;

      case 'execution.resumed':
        setCurrentTask(prev => prev ? { ...prev, status: 'EXECUTING' } : null);
        break;

      case 'execution.completed':
        setPhase('completed');
        setCurrentTask(prev => prev ? { ...prev, status: 'COMPLETED' } : null);
        break;

      case 'execution.replanned':
        // 重新规划后的新步骤
        const newSteps = lastMessage.payload?.new_steps || [];
        if (newSteps.length > 0) {
          const formattedSteps: ExecutionStep[] = newSteps.map((s: any) => ({
            id: s.id,
            name: s.name,
            description: s.description,
            status: 'pending',
            dependencies: s.dependencies || [],
            position: s.position || { x: 0, y: 0 },
            isMainPath: s.is_main_path ?? false,
          }));
          setExecutionSteps(prev => [...prev, ...formattedSteps]);
        }
        break;

      // 错误处理
      case 'error':
        console.error('[useTask] Server error:', lastMessage.payload?.message || lastMessage.error);
        setIsLoading(false);
        break;
    }
  }, [lastMessage]);

  // 启动新任务
  const startTask = useCallback((userInput: string) => {
    if (!isConnected) {
      console.error('[useTask] WebSocket not connected');
      return false;
    }
    
    // 重置状态
    setThinkingNodes([]);
    setExecutionSteps([]);
    setPhase('thinking');
    setIsLoading(true);
    
    send('task.start', { user_input: userInput });
    return true;
  }, [send, isConnected]);

  // 选择思考选项
  const selectThinkingOption = useCallback((nodeId: string, optionId: string) => {
    if (!currentTask) return;
    
    // 本地更新状态
    setThinkingNodes(prev => 
      prev.map(n => n.id === nodeId ? { ...n, status: 'selected' as const, selectedOption: optionId } : n)
    );
    
    send('thinking.select_option', {
      task_id: currentTask.id,
      current_node_id: nodeId,
      option_id: optionId
    });
  }, [send, currentTask]);

  // 自定义输入
  const submitCustomInput = useCallback((nodeId: string, customInput: string) => {
    if (!currentTask) return;
    
    setThinkingNodes(prev => 
      prev.map(n => n.id === nodeId ? { ...n, status: 'selected' as const, customInput } : n)
    );
    
    send('thinking.custom_input', {
      task_id: currentTask.id,
      current_node_id: nodeId,
      custom_input: customInput
    });
  }, [send, currentTask]);

  // 确认执行
  const confirmExecution = useCallback(() => {
    if (!currentTask) return;
    
    send('thinking.confirm_execution', {
      task_id: currentTask.id
    });
  }, [send, currentTask]);

  // 开始执行
  const startExecution = useCallback(() => {
    if (!currentTask?.currentBlueprintId) return;
    
    send('execution.start', {
      task_id: currentTask.id,
      blueprint_id: currentTask.currentBlueprintId
    });
  }, [send, currentTask]);

  // 暂停执行
  const pauseExecution = useCallback(() => {
    if (!currentTask?.currentBlueprintId) return;
    
    send('execution.pause', {
      task_id: currentTask.id,
      blueprint_id: currentTask.currentBlueprintId
    });
  }, [send, currentTask]);

  // 恢复执行
  const resumeExecution = useCallback(() => {
    if (!currentTask?.currentBlueprintId) return;
    
    send('execution.resume', {
      task_id: currentTask.id,
      blueprint_id: currentTask.currentBlueprintId
    });
  }, [send, currentTask]);

  // 干预执行
  const interveneExecution = useCallback((stepId: string, action: 'replan' | 'skip' | 'retry' | 'modify', customInput?: string) => {
    if (!currentTask?.currentBlueprintId) return;
    
    send('execution.intervene', {
      task_id: currentTask.id,
      blueprint_id: currentTask.currentBlueprintId,
      step_id: stepId,
      action,
      custom_input: customInput
    });
  }, [send, currentTask]);

  // 重置
  const reset = useCallback(() => {
    setCurrentTask(null);
    setThinkingNodes([]);
    setExecutionSteps([]);
    setPhase('input');
    setIsLoading(false);
  }, []);

  return {
    // 状态
    isConnected,
    isLoading,
    currentTask,
    thinkingNodes,
    executionSteps,
    phase,
    
    // 操作
    startTask,
    selectThinkingOption,
    submitCustomInput,
    confirmExecution,
    startExecution,
    pauseExecution,
    resumeExecution,
    interveneExecution,
    reset,
  };
}
