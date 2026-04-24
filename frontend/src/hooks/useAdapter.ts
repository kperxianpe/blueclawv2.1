/**
 * useAdapter Hook
 * 封装 Adapter 相关的 WebSocket 通信
 * 
 * 对外暴露：
 * - adapterList: Adapter[]  列表数据
 * - fetchAdapters(): 加载列表
 * - attachToStep(stepId, adapterId): 绑定到步骤
 * - enterEditMode(adapterId): 进入嵌套编辑
 * - executeAdapter(adapterId): 执行 Adapter
 */
import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';

export interface Adapter {
  id: string;
  name: string;
  icon: string;
  color: string;
  type: 'single' | 'blueprint' | 'agent';
  inputCount: number;
  hasChildren: boolean;
}

export interface AdapterAttachment {
  adapterId: string;
  adapterRef: Adapter;
  locked: boolean;
}

export function useAdapter(taskId?: string) {
  const { send, lastMessage, isConnected } = useWebSocket();
  
  const [adapterList, setAdapterList] = useState<Adapter[]>([]);
  const [editMode, setEditMode] = useState<{
    adapterId: string;
    name: string;
    blueprint: any;
  } | null>(null);
  const [attachments, setAttachments] = useState<Record<string, AdapterAttachment[]>>({});

  // 消息监听
  useEffect(() => {
    if (!lastMessage) return;
    
    switch (lastMessage.type) {
      case 'adapter.listed':
        setAdapterList(lastMessage.payload?.adapters || []);
        break;
        
      case 'adapter.edit_mode_entered':
        setEditMode({
          adapterId: lastMessage.payload?.adapter_id,
          name: lastMessage.payload?.name,
          blueprint: lastMessage.payload?.blueprint
        });
        break;

      case 'adapter.attached':
        // Adapter 绑定成功，更新本地状态
        const { step_id, adapter_id, locked } = lastMessage.payload || {};
        if (step_id && adapter_id) {
          setAttachments(prev => ({
            ...prev,
            [step_id]: [...(prev[step_id] || []), { 
              adapterId: adapter_id, 
              adapterRef: adapterList.find(a => a.id === adapter_id)!,
              locked: locked ?? true
            }]
          }));
        }
        break;

      case 'adapter.detached':
        // Adapter 解绑成功
        const { step_id: detach_step_id, adapter_id: detach_adapter_id } = lastMessage.payload || {};
        if (detach_step_id) {
          setAttachments(prev => ({
            ...prev,
            [detach_step_id]: (prev[detach_step_id] || []).filter(
              a => a.adapterId !== detach_adapter_id
            )
          }));
        }
        break;
    }
  }, [lastMessage, adapterList]);

  // 加载 Adapter 列表
  const fetchAdapters = useCallback(() => {
    send('adapter.list', {});
  }, [send]);

  // 绑定到步骤（拖拽用）
  const attachToStep = useCallback((stepId: string, adapterId: string, locked = true) => {
    if (!taskId) {
      console.warn('[useAdapter] No taskId provided');
      return;
    }
    
    send('adapter.attach_to_step', {
      step_id: stepId,
      adapter_id: adapterId,
      locked
    });
  }, [send, taskId]);

  // 解绑 Adapter
  const detachFromStep = useCallback((stepId: string, adapterId: string) => {
    send('adapter.detach_from_step', {
      step_id: stepId,
      adapter_id: adapterId
    });
  }, [send]);

  // 进入编辑模式（双击用）
  const enterEditMode = useCallback((adapterId: string) => {
    send('adapter.enter_edit', { adapter_id: adapterId });
  }, [send]);

  // 退出编辑模式
  const exitEditMode = useCallback(() => {
    setEditMode(null);
  }, []);

  // 执行 Adapter
  const executeAdapter = useCallback((adapterId: string) => {
    if (!taskId) {
      console.warn('[useAdapter] No taskId provided');
      return;
    }
    send('adapter.execute', { adapter_id: adapterId });
  }, [send, taskId]);

  return {
    isConnected,
    adapterList,
    editMode,
    attachments,
    setEditMode,
    exitEditMode,
    fetchAdapters,
    attachToStep,
    detachFromStep,
    enterEditMode,
    executeAdapter
  };
}
