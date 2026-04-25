/**
 * RealtimeProvider
 * 初始化 WebSocket 连接，并将后端消息同步到 Zustand Store
 */
import { useEffect, useRef } from 'react';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { useBlueprintStore } from '@/store/useBlueprintStore';
import type { ThinkingNodeType, ExecutionStep } from '@/types';

interface Props {
  children: React.ReactNode;
}

export function RealtimeProvider({ children }: Props) {
  const { isConnected, messageVersion, consumeMessages } = useWebSocketContext();
  const processedMessages = useRef<Set<string>>(new Set());
  
  // 使用独立的 hook 调用，避免依赖问题
  const setConnectionStatus = useBlueprintStore(s => s.setConnectionStatus);
  const setRealtimeMode = useBlueprintStore(s => s.setRealtimeMode);
  const setCurrentTaskId = useBlueprintStore(s => s.setCurrentTaskId);
  const setUserInput = useBlueprintStore(s => s.setUserInput);
  const setPhase = useBlueprintStore(s => s.setPhase);
  const setThinkingNodes = useBlueprintStore(s => s.setThinkingNodes);
  const setExecutionSteps = useBlueprintStore(s => s.setExecutionSteps);
  const updateThinkingNode = useBlueprintStore(s => s.updateThinkingNode);
  const updateExecutionStep = useBlueprintStore(s => s.updateExecutionStep);
  const setCurrentBlueprintId = useBlueprintStore(s => s.setCurrentBlueprintId);
  const setIsGeneratingBlueprint = useBlueprintStore(s => s.setIsGeneratingBlueprint);
  const setShowConfirmExecution = useBlueprintStore(s => s.setShowConfirmExecution);
  const isRealtimeMode = useBlueprintStore(s => s.isRealtimeMode);
  const thinkingNodes = useBlueprintStore(s => s.thinkingNodes);
  const setFreezeState = useBlueprintStore(s => s.setFreezeState);
  const addScreenshot = useBlueprintStore(s => s.addScreenshot);

  // 同步连接状态
  useEffect(() => {
    setConnectionStatus(isConnected);
  }, [isConnected, setConnectionStatus]);

  // 处理 WebSocket 消息队列（修复 React 18 批处理导致的消息丢失）
  useEffect(() => {
    const messages = consumeMessages();
    if (messages.length === 0) return;

    for (const msg of messages) {
      // 避免重复处理
      const msgId = msg.message_id || `${msg.type}_${msg.timestamp}_${Math.random().toString(36).substr(2, 9)}`;
      if (processedMessages.current.has(msgId)) continue;
      processedMessages.current.add(msgId);

      console.log('[RealtimeProvider] Processing:', msg.type);

      switch (msg.type) {
      case 'task.started': {
        console.log('[RealtimeProvider] Task started, switching to thinking phase');
        setRealtimeMode(true);
        setCurrentTaskId(msg.payload?.task_id);
        setUserInput(msg.payload?.user_input || '');
        setPhase('thinking');
        break;
      }

      case 'thinking.node_created':
      case 'thinking.node_selected': {
        console.log('[RealtimeProvider] thinking.node_created/selected payload:', msg.payload);
        const nodeData = msg.payload?.node;
        console.log('[RealtimeProvider] nodeData:', nodeData);
        if (nodeData) {
          const newNode: ThinkingNodeType = {
            id: nodeData.id,
            question: nodeData.question,
            options: nodeData.options?.map((o: any) => ({
              id: o.id,
              label: o.label,
              description: o.description,
              confidence: o.confidence,
              isDefault: o.is_default,
            })) || [],
            allowCustom: nodeData.allow_custom ?? true,
            status: 'pending',
          };
          // 使用函数式更新获取最新状态（修复闭包问题）
          const currentNodes = useBlueprintStore.getState().thinkingNodes;
          console.log('[RealtimeProvider] currentNodes before:', currentNodes.length);
          setThinkingNodes([...currentNodes, newNode]);
          console.log('[RealtimeProvider] currentNodes after:', useBlueprintStore.getState().thinkingNodes.length);
        } else {
          console.log('[RealtimeProvider] nodeData is falsy!');
        }
        break;
      }

      case 'thinking.option_selected': {
        const { option_id, current_node_id } = msg.payload || {};
        if (current_node_id && option_id) {
          updateThinkingNode(current_node_id, { 
            status: 'selected', 
            selectedOption: option_id 
          });
        }
        break;
      }

      case 'thinking.custom_input_received': {
        const { current_node_id, custom_input } = msg.payload || {};
        if (current_node_id) {
          updateThinkingNode(current_node_id, { 
            status: 'selected', 
            customInput: custom_input 
          });
        }
        break;
      }

      case 'execution.blueprint_loaded': {
        const blueprint = msg.payload?.blueprint;
        console.log('[RealtimeProvider] Blueprint loaded:', blueprint);
        if (blueprint) {
          const stepsData = blueprint.steps || [];
          const steps: ExecutionStep[] = stepsData.map((s: any) => ({
            id: s.id,
            name: s.name,
            description: s.description,
            status: (s.status?.toLowerCase() || 'pending') as ExecutionStep['status'],
            dependencies: s.dependencies || [],
            position: s.position || { x: 0, y: 0 },
            isMainPath: s.is_main_path ?? true,
            isConvergence: s.is_convergence ?? false,
            convergenceType: s.convergence_type,
            result: s.result,
            needsIntervention: s.needs_intervention ?? false,
            isArchived: s.is_archived ?? false,
            tool: s.tool,
          }));
          console.log('[RealtimeProvider] Setting execution steps:', steps.length);
          setExecutionSteps(steps);
          setPhase('execution');
          setCurrentBlueprintId(blueprint.id);
          setShowConfirmExecution(false);
          setIsGeneratingBlueprint(false);
        }
        break;
      }

      case 'execution.returned_to_thinking': {
        console.log('[RealtimeProvider] Execution returned to thinking');
        const archivedIds: string[] = msg.payload?.archived_step_ids || [];
        // 清空旧思考节点，等待新的根节点推送
        setThinkingNodes([]);
        setPhase('thinking');
        // 将相关执行步骤标记为归档
        const currentSteps = useBlueprintStore.getState().executionSteps;
        setExecutionSteps(
          currentSteps.map((s) =>
            archivedIds.includes(s.id) ? { ...s, isArchived: true } : s
          )
        );
        setCurrentBlueprintId(null);
        break;
      }

      case 'execution.step_started': {
        const { step_id, name, status } = msg.payload || {};
        console.log('[RealtimeProvider] Step started:', step_id, name, status);
        if (step_id) {
          updateExecutionStep(step_id, { status: status?.toLowerCase() || 'running' });
        }
        break;
      }

      case 'execution.step_completed': {
        const { step_id, name, status, result } = msg.payload || {};
        console.log('[RealtimeProvider] Step completed:', step_id, name, status, result);
        if (step_id) {
          updateExecutionStep(step_id, { 
            status: status?.toLowerCase() || 'completed',
            result: result,
            tool: msg.payload?.tool,
          });
        }
        break;
      }

      case 'execution.completed': {
        console.log('[RealtimeProvider] Execution completed!');
        setPhase('completed');
        break;
      }

      case 'freeze.confirmed': {
        const { stepId, screenshot, freezeToken } = msg.payload || {};
        console.log('[RealtimeProvider] Freeze confirmed for step:', stepId);
        setFreezeState({
          isFrozen: true,
          stepId: stepId || null,
          screenshot: screenshot || null,
          freezeToken: freezeToken || null,
          annotations: [],
        });
        break;
      }

      case 'screenshot': {
        const { stepId, image, timestamp } = msg.payload || {};
        console.log('[RealtimeProvider] Screenshot received for step:', stepId);
        if (image && stepId) {
          addScreenshot({ stepId, image, timestamp: timestamp || Date.now() });
        }
        break;
      }

      case 'error':
        console.error('[RealtimeProvider] Server error:', msg.payload?.message || msg.error);
        break;
      }
    }

    // 清理旧消息
    if (processedMessages.current.size > 1000) {
      processedMessages.current.clear();
    }
  }, [messageVersion, consumeMessages, setRealtimeMode, setCurrentTaskId, setUserInput, setPhase, setThinkingNodes, setExecutionSteps, updateThinkingNode, updateExecutionStep, setCurrentBlueprintId, setIsGeneratingBlueprint, setShowConfirmExecution, setFreezeState, addScreenshot, isRealtimeMode, thinkingNodes]);

  return <>{children}</>;
}
