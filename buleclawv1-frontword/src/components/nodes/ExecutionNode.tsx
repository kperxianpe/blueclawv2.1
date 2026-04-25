import { useState } from 'react';
import { Handle, Position } from '@xyflow/react';
import { useBlueprintStore } from '@/store/useBlueprintStore';
import { cn } from '@/lib/utils';
import {
  Circle, Zap, CheckCircle2, XCircle, Cpu,
  ChevronDown, ChevronUp, AlertTriangle,
  Settings2, Save
} from 'lucide-react';
import { InterferencePanel, type InterferenceAction } from '../panels/InterferencePanel';
import type { ToolItem } from '../visual/ToolDock';
import { ToolBadgeMini } from '../visual/ToolDock';

interface ExecutionNodeProps {
  data: { stepId: string; onFreeze?: (stepName: string) => void };
}

const statusConfig = {
  pending: {
    bgColor: 'bg-white/95',
    borderColor: 'border-gray-300',
    iconColor: 'text-gray-400',
    icon: Circle,
    label: '待执行',
    darkBg: 'bg-gray-800',
  },
  running: {
    bgColor: 'bg-blue-50/95',
    borderColor: 'border-blue-500',
    iconColor: 'text-blue-600',
    icon: Zap,
    label: '执行中',
    darkBg: 'bg-blue-900/50',
  },
  completed: {
    bgColor: 'bg-green-50/95',
    borderColor: 'border-green-500',
    iconColor: 'text-green-600',
    icon: CheckCircle2,
    label: '已完成',
    darkBg: 'bg-green-900/50',
  },
  failed: {
    bgColor: 'bg-red-50/95',
    borderColor: 'border-red-500',
    iconColor: 'text-red-600',
    icon: XCircle,
    label: '失败',
    darkBg: 'bg-red-900/50',
  },
};

export function ExecutionNodeComponent({ data }: ExecutionNodeProps) {
  const { stepId, onFreeze } = data;
  const step = useBlueprintStore(state => state.executionSteps.find(s => s.id === stepId));
  const selectedStepId = useBlueprintStore(state => state.selectedExecutionStepId);
  const selectExecutionStep = useBlueprintStore(state => state.selectExecutionStep);
  const interveneExecution = useBlueprintStore(state => state.interveneExecution);

  const [isExpanded, setIsExpanded] = useState(false);
  const [showInterference, setShowInterference] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  const addToolToExecutionStep = useBlueprintStore(state => state.addToolToExecutionStep);

  if (!step) return null;

  const config = statusConfig[step.status];
  const Icon = config.icon;
  const isSelected = selectedStepId === stepId;
  const isRunning = step.status === 'running';
  const canIntervene = step.status === 'running' || step.status === 'failed' || step.status === 'pending';

  const handleExpand = () => {
    setIsExpanded(!isExpanded);
    selectExecutionStep(stepId);
  };

  /** 处理干涉面板动作 */
  const handleInterferenceAction = (action: InterferenceAction) => {
    switch (action) {
      case 'reexecute':
        // 从当前节点重新执行: 重置当前及后续步骤状态
        {
          const store = useBlueprintStore.getState();
          const currentIndex = store.executionSteps.findIndex(s => s.id === stepId);
          const updatedSteps = store.executionSteps.map((s, idx) => {
            if (idx >= currentIndex) {
              return { ...s, status: 'pending' as const, result: undefined, error: undefined, needsIntervention: false };
            }
            return s;
          });
          useBlueprintStore.setState({ executionSteps: updatedSteps });
          // 开始执行
          setTimeout(() => {
            useBlueprintStore.getState().executeNextStep();
          }, 300);
        }
        break;

      case 'rethink':
        // 从当前节点前开始重新思考
        interveneExecution(stepId);
        break;

      case 'freeze':
        // 冻结执行
        if (onFreeze) {
          onFreeze(step.name);
        }
        break;
    }
    setShowInterference(false);
  };

  const hasAssociatedTools = (step.associatedTools || []).length > 0;

  // 处理拖放接收
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = 'copy';
    setDragOver(true);
  };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    const data = e.dataTransfer.getData('application/json');
    if (data) {
      try {
        const item: ToolItem = JSON.parse(data);
        if (!step.associatedTools?.includes(item.id)) {
          addToolToExecutionStep(stepId, item.id);
          setIsSaved(false);
        }
      } catch { /* ignore */ }
    }
  };
  const handleSave = () => setIsSaved(true);

  return (
    <div className="relative" onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}>
      {/* 输入连接点 */}
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        style={{
          background: '#16A34A',
          width: 8,
          height: 8,
          top: -4,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 100,
          border: '2px solid white',
          boxShadow: '0 1px 3px rgba(0,0,0,0.3)'
        }}
      />
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{
          background: '#16A34A',
          width: 8,
          height: 8,
          left: -4,
          top: '50%',
          transform: 'translateY(-50%)',
          zIndex: 100,
          border: '2px solid white',
          boxShadow: '0 1px 3px rgba(0,0,0,0.3)'
        }}
      />

      {/* ===== 右上角干涉按钮 ===== */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          setShowInterference(true);
        }}
        className={cn(
          "absolute -top-2 -right-2 z-[60] w-6 h-6 rounded-full flex items-center justify-center",
          "transition-all shadow-md border-2 border-white",
          canIntervene
            ? "bg-gradient-to-br from-amber-400 to-orange-500 hover:from-amber-300 hover:to-orange-400 cursor-pointer"
            : "bg-gray-300 cursor-not-allowed"
        )}
        title="干涉操作"
      >
        <Settings2 className="w-3 h-3 text-white" />
      </button>

      {/* 主节点容器 */}
      <div
        className={cn(
          "w-[180px] rounded-xl border-2 transition-all duration-300 bg-white relative overflow-hidden",
          config.borderColor,
          isSelected && "ring-2 ring-offset-2 ring-blue-400 shadow-lg",
          isRunning && "animate-pulse",
          dragOver && "ring-2 ring-amber-400 border-amber-400 scale-[1.02]"
        )}
      >
        {/* 顶部概览区域 - 始终显示 */}
        <div
          onClick={handleExpand}
          className={cn(
            "flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-50 transition-colors",
            isExpanded ? "border-b border-gray-200" : ""
          )}
        >
          <div className={cn(
            "w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0",
            step.status === 'running' && "bg-blue-500",
            step.status === 'completed' && "bg-green-500",
            step.status === 'failed' && "bg-red-500",
            step.status === 'pending' && "bg-gray-400"
          )}>
            {step.status === 'running' ? (
              <Cpu className="w-3 h-3 text-white animate-spin" />
            ) : (
              <Icon className="w-3 h-3 text-white" />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1">
              <span className="text-[9px] font-medium text-gray-500">
                {step.isMainPath ? '主' : '支'}
              </span>
              <span className="text-xs font-medium text-gray-700 truncate">
                {step.name}
              </span>
            </div>
            <p className="text-[10px] text-gray-500 truncate">
              {config.label}
            </p>
          </div>

          <div className="flex items-center gap-1">
            {step.isConvergence && (
              <span className="px-1 py-0.5 bg-orange-100 text-orange-700 rounded text-[7px]">
                汇合
              </span>
            )}
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </div>
        </div>

        {/* 展开后的详细内容 */}
        {isExpanded && (
          <div className={cn("bg-gray-900", config.darkBg)}>
            {/* 概览行 */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-gray-400">步骤 #{stepId.replace(/[^0-9]/g, '')}</span>
                {step.needsIntervention && (
                  <span className="flex items-center gap-0.5 text-[9px] text-yellow-400">
                    <AlertTriangle className="w-3 h-3" />
                    需干预
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                {/* 关联工具 */}
                {hasAssociatedTools && (
                  <div className="flex items-center gap-0.5 mr-1 max-w-[80px] overflow-hidden">
                    {(step.associatedTools || []).slice(0, 1).map(tid => (
                      <ToolBadgeMini key={tid} toolId={tid} />
                    ))}
                    {(step.associatedTools || []).length > 1 && (
                      <span className="text-[8px] text-amber-500 flex-shrink-0">+{(step.associatedTools || []).length - 1}</span>
                    )}
                  </div>
                )}
                {/* 干涉按钮 */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowInterference(true);
                  }}
                  className={cn(
                    "flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors",
                    canIntervene
                      ? "bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-white shadow-sm"
                      : "bg-gray-700 text-gray-500 cursor-not-allowed"
                  )}
                >
                  <Settings2 className="w-2.5 h-2.5" />
                  干涉
                </button>
              </div>
            </div>

            {/* 详细内容 */}
            <div className="p-3">
              <p className="text-xs text-gray-300 mb-2">{step.description}</p>

              {/* 进度条 */}
              {step.status === 'running' && (
                <div className="mb-2">
                  <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full animate-[loading_2s_ease-in-out_infinite]"
                      style={{ width: '60%' }} />
                  </div>
                </div>
              )}

              {/* 结果 */}
              {step.result && (
                <div className="p-2 rounded bg-green-900/30 border border-green-700/50 mb-2">
                  <p className="text-[10px] text-green-400">结果: {step.result}</p>
                </div>
              )}

              {/* 错误 */}
              {step.error && (
                <div className="p-2 rounded bg-red-900/30 border border-red-700/50 mb-2">
                  <p className="text-[10px] text-red-400">错误: {step.error}</p>
                </div>
              )}

              {/* 关联工具区域 */}
              <div className={cn(
                "border-t border-dashed border-gray-700/50 mt-2 pt-2 rounded-lg transition-colors",
                dragOver ? "bg-amber-50/30" : ""
              )}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[9px] text-gray-500 uppercase tracking-wider font-medium">
                    已关联工具 ({step.associatedTools?.length || 0})
                  </span>
                  <div className="flex items-center gap-1">
                    {hasAssociatedTools && (
                      <button
                        onClick={handleSave}
                        className={cn(
                          "flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] transition-colors",
                          isSaved ? "bg-green-500/20 text-green-400" : "bg-amber-500/20 text-amber-400 hover:bg-amber-500/30"
                        )}
                      >
                        <Save className="w-2.5 h-2.5" />
                        {isSaved ? '已保存' : '保存'}
                      </button>
                    )}
                    <span className="text-[9px] text-gray-500">从工具栏拖拽添加</span>
                  </div>
                </div>
                {(step.associatedTools || []).length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {(step.associatedTools || []).map((toolId) => (
                      <ToolBadgeMini
                        key={toolId}
                        toolId={toolId}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-2 border border-dashed border-gray-700 rounded-md">
                    <span className="text-[10px] text-gray-600">拖拽工具到此处关联</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 输出连接点 */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        style={{
          background: '#16A34A',
          width: 8,
          height: 8,
          bottom: -4,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 100,
          border: '2px solid white',
          boxShadow: '0 1px 3px rgba(0,0,0,0.3)'
        }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        style={{
          background: '#16A34A',
          width: 8,
          height: 8,
          right: -4,
          top: '50%',
          transform: 'translateY(-50%)',
          zIndex: 100,
          border: '2px solid white',
          boxShadow: '0 1px 3px rgba(0,0,0,0.3)'
        }}
      />

      {/* ===== 干涉面板按钮组 ===== */}
      <InterferencePanel
        isOpen={showInterference}
        onClose={() => setShowInterference(false)}
        onAction={handleInterferenceAction}
      />
    </div>
  );
}
