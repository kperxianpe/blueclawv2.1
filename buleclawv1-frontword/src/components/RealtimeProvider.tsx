/**
 * RealtimeProvider - API V2 WebSocket message processor
 * Maps backend messages (old API format) to Zustand store actions
 */
import { useEffect, useRef } from 'react';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { useBlueprintStore } from '@/store/useBlueprintStore';
import type { ThinkingNodeType, ExecutionStep } from '@/types';

interface Props {
  children: React.ReactNode;
}

export function RealtimeProvider({ children }: Props) {
  const { messageVersion, consumeMessages } = useWebSocketContext();
  const processedMessages = useRef<Set<string>>(new Set());
  
  const setPhase = useBlueprintStore(s => s.setPhase);
  const setUserInput = useBlueprintStore(s => s.setUserInput);
  const setThinkingNodes = useBlueprintStore(s => s.setThinkingNodes);
  const updateThinkingNode = useBlueprintStore(s => s.updateThinkingNode);
  const setCurrentThinkingIndex = useBlueprintStore(s => s.setCurrentThinkingIndex);
  const setSelectedThinkingNodeId = useBlueprintStore(s => s.setSelectedThinkingNodeId);
  const setExecutionSteps = useBlueprintStore(s => s.setExecutionSteps);
  const updateExecutionStep = useBlueprintStore(s => s.updateExecutionStep);
  const selectExecutionStep = useBlueprintStore(s => s.selectExecutionStep);

  useEffect(() => {
    const messages = consumeMessages();
    if (messages.length === 0) return;

    for (const msg of messages) {
      const msgId = msg.message_id || `${msg.type}_${msg.timestamp}_${Math.random().toString(36).substr(2, 9)}`;
      if (processedMessages.current.has(msgId)) continue;
      processedMessages.current.add(msgId);

      console.log('[RealtimeProvider] Processing:', msg.type);

      switch (msg.type) {
        case 'task.started': {
          const taskId = msg.payload?.task_id;
          const userInput = msg.payload?.user_input || '';
          console.log('[RealtimeProvider] Task started:', taskId);
          setUserInput(userInput);
          setPhase('thinking');
          break;
        }

        case 'thinking.node_created':
        case 'thinking.node_selected': {
          const nodeData = msg.payload?.node;
          if (nodeData) {
            const newNode: ThinkingNodeType = {
              id: nodeData.id,
              question: nodeData.question,
              options: (nodeData.options || []).map((o: any) => ({
                id: o.id,
                label: o.label,
                description: o.description,
                confidence: o.confidence,
                isDefault: o.is_default ?? false,
              })),
              allowCustom: nodeData.allow_custom ?? true,
              status: 'pending',
            };
            const currentNodes = useBlueprintStore.getState().thinkingNodes;
            // Avoid duplicates
            if (!currentNodes.find(n => n.id === newNode.id)) {
              setThinkingNodes([...currentNodes, newNode]);
              setCurrentThinkingIndex(currentNodes.length);
              setSelectedThinkingNodeId(newNode.id);
            }
          }
          break;
        }

        case 'thinking.option_selected': {
          const { option_id, current_node_id } = msg.payload || {};
          if (current_node_id && option_id) {
            updateThinkingNode(current_node_id, { status: 'selected', selectedOption: option_id });
          }
          break;
        }

        case 'thinking.custom_input_received': {
          const { current_node_id, custom_input } = msg.payload || {};
          if (current_node_id) {
            updateThinkingNode(current_node_id, { status: 'selected', customInput: custom_input });
          }
          break;
        }

        case 'thinking.completed':
        case 'thinking.converged': {
          console.log('[RealtimeProvider] Thinking completed/converged');
          // Phase will switch on blueprint_loaded
          break;
        }

        case 'execution.blueprint_loaded': {
          const blueprint = msg.payload?.blueprint;
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
            }));
            setExecutionSteps(steps);
            setPhase('execution');
            selectExecutionStep(steps[0]?.id || null);
          }
          break;
        }

        case 'execution.step_started': {
          const stepId = msg.payload?.step_id || msg.payload?.id;
          if (stepId) {
            updateExecutionStep(stepId, { status: 'running' });
          }
          break;
        }

        case 'execution.step_completed': {
          const stepId = msg.payload?.step_id || msg.payload?.id;
          const result = msg.payload?.result;
          if (stepId) {
            updateExecutionStep(stepId, { status: 'completed', result });
          }
          break;
        }

        case 'execution.step_failed': {
          const stepId = msg.payload?.step_id;
          if (stepId) {
            updateExecutionStep(stepId, { status: 'failed', error: msg.payload?.error });
          }
          break;
        }

        case 'execution.intervention_needed': {
          const stepId = msg.payload?.step_id;
          if (stepId) {
            updateExecutionStep(stepId, { status: 'failed', needsIntervention: true });
          }
          break;
        }

        case 'execution.returned_to_thinking': {
          const archivedIds = msg.payload?.archived_step_ids || [];
          const currentSteps = useBlueprintStore.getState().executionSteps;
          setExecutionSteps(
            currentSteps.map(s =>
              archivedIds.includes(s.id) ? { ...s, isArchived: true } : s
            )
          );
          setPhase('thinking');
          break;
        }

        case 'execution.completed': {
          setPhase('completed');
          break;
        }

        case 'error':
          console.error('[RealtimeProvider] Server error:', msg.payload?.message || msg.error);
          break;
      }
    }

    if (processedMessages.current.size > 1000) {
      processedMessages.current.clear();
    }
  }, [messageVersion, consumeMessages, setPhase, setUserInput, setThinkingNodes, updateThinkingNode, setCurrentThinkingIndex, setSelectedThinkingNodeId, setExecutionSteps, updateExecutionStep, selectExecutionStep]);

  return <>{children}</>;
}
