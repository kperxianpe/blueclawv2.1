/**
 * ExecutionNode 组件
 * 执行蓝图节点，支持 Adapter 绑定显示
 */
import React from 'react';
import { AdapterAttachments } from './AdapterAttachments';
import { useAdapter } from '../../hooks/useAdapter';
import './AdapterAttachments.css';

export interface ExecutionStep {
  id: string;
  name: string;
  description?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused';
  dependencies: string[];
  result?: string;
  error?: string;
  // Week 21 新增
  attachedAdapters?: Array<{
    adapterId: string;
    adapterRef: {
      id: string;
      name: string;
      icon: string;
      color: string;
      type: string;
    };
    locked: boolean;
  }>;
}

interface ExecutionNodeProps {
  step: ExecutionStep;
  onStepClick?: (stepId: string) => void;
}

export const ExecutionNode: React.FC<ExecutionNodeProps> = ({
  step,
  onStepClick
}) => {
  const { enterEditMode } = useAdapter();

  const handleAttachmentClick = (adapterId: string) => {
    // 进入 Adapter 编辑模式
    enterEditMode(adapterId);
  };

  // 转换 attachedAdapters 格式
  const attachments = step.attachedAdapters?.map(att => ({
    adapterId: att.adapterId,
    adapterRef: {
      id: att.adapterRef.id,
      name: att.adapterRef.name,
      icon: att.adapterRef.icon,
      color: att.adapterRef.color,
      type: (att.adapterRef.type as 'single' | 'blueprint' | 'agent') || 'single',
      inputCount: 0,
      hasChildren: false
    },
    locked: att.locked
  })) || [];

  return (
    <div 
      className={`execution-node status-${step.status}`}
      onClick={() => onStepClick?.(step.id)}
    >
      {/* 节点主体 */}
      <div className="node-header">
        <span className="node-status-indicator" />
        <span className="node-name">{step.name}</span>
      </div>
      
      {step.description && (
        <div className="node-description">{step.description}</div>
      )}
      
      {/* Week 21 新增：右上角 Adapter 绑定区 */}
      <div className="node-adapters">
        <AdapterAttachments
          stepId={step.id}
          attachments={attachments}
          onAttachmentClick={handleAttachmentClick}
        />
      </div>
    </div>
  );
};
