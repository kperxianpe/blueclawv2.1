/**
 * useRealtimeSync Hook
 * 将 useTask (真实 WebSocket) 与 useBlueprintStore (UI 状态) 同步
 */
import { useEffect, useCallback } from 'react';
import { useTask } from './useTask';
import { useBlueprintStore } from '@/store/useBlueprintStore';

export function useRealtimeSync() {
  // 获取 useTask 的状态和操作
  const {
    isConnected,
    isLoading,
    currentTask,
    thinkingNodes,
    executionSteps,
    phase: taskPhase,
    startTask,
    selectThinkingOption,
    submitCustomInput,
    confirmExecution,
    startExecution,
    pauseExecution,
    resumeExecution,
    interveneExecution,
    reset,
  } = useTask();

  // 获取 store 的操作
  const store = useBlueprintStore();

  // 同步 phase 变化
  useEffect(() => {
    // 当 task phase 变化时，更新 store
    if (taskPhase !== store.phase) {
      // 使用 store.setState 或直接调用 actions
      // 注意：需要确保 store 的 phase 可以被外部更新
    }
  }, [taskPhase, store.phase]);

  // 包装 startThinking，使用真实后端
  const handleStartThinking = useCallback((input: string) => {
    store.setUserInput(input);
    const success = startTask(input);
    if (!success) {
      // 如果 WebSocket 未连接，回退到 mock 模式
      console.warn('[RealtimeSync] WebSocket not connected, using mock mode');
      store.startThinking();
    }
  }, [store, startTask]);

  // 包装 selectThinkingOption
  const handleSelectThinkingOption = useCallback((nodeId: string, optionId: string) => {
    if (currentTask && isConnected) {
      // 真实模式
      selectThinkingOption(nodeId, optionId);
    } else {
      // Mock 模式
      store.selectThinkingOption(nodeId, optionId);
    }
  }, [currentTask, isConnected, selectThinkingOption, store]);

  // 包装 setCustomInput
  const handleSetCustomInput = useCallback((nodeId: string, input: string) => {
    if (currentTask && isConnected) {
      submitCustomInput(nodeId, input);
    } else {
      store.setCustomInput(nodeId, input);
    }
  }, [currentTask, isConnected, submitCustomInput, store]);

  // 包装 completeThinking
  const handleCompleteThinking = useCallback(() => {
    if (currentTask && isConnected) {
      confirmExecution();
    } else {
      store.completeThinking();
    }
  }, [currentTask, isConnected, confirmExecution, store]);

  // 同步 thinkingNodes 到 store
  useEffect(() => {
    if (thinkingNodes.length > 0 && currentTask) {
      // 直接修改 store 的 thinkingNodes
      // 需要添加一个方法到 store 来设置 thinkingNodes
      // 暂时通过直接赋值方式
      (store as any).thinkingNodes = thinkingNodes;
    }
  }, [thinkingNodes, currentTask, store]);

  // 同步 executionSteps 到 store
  useEffect(() => {
    if (executionSteps.length > 0 && currentTask) {
      (store as any).executionSteps = executionSteps;
    }
  }, [executionSteps, currentTask, store]);

  return {
    // 连接状态
    isConnected,
    isLoading,
    
    // 当前任务
    currentTask,
    
    // 包装后的操作
    startThinking: handleStartThinking,
    selectThinkingOption: handleSelectThinkingOption,
    setCustomInput: handleSetCustomInput,
    completeThinking: handleCompleteThinking,
    
    // 原始操作（用于更复杂的场景）
    startExecution,
    pauseExecution,
    resumeExecution,
    interveneExecution,
    reset,
  };
}
