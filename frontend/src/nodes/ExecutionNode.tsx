import { useState } from 'react';
import { Handle, Position } from '@xyflow/react';
import { useBlueprintStore } from '@/store/useBlueprintStore';
import { cn } from '@/lib/utils';
import { 
  Circle, 
  Zap, 
  CheckCircle2, 
  XCircle, 
  Cpu,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Wrench,
  PauseCircle
} from 'lucide-react';
import { useWebSocketContext } from '@/contexts/WebSocketContext';

interface ExecutionNodeProps {
  data: { stepId: string };
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
  const { stepId } = data;
  const step = useBlueprintStore(state => state.executionSteps.find(s => s.id === stepId));
  const selectedStepId = useBlueprintStore(state => state.selectedExecutionStepId);
  const selectExecutionStep = useBlueprintStore(state => state.selectExecutionStep);
  const interveneExecution = useBlueprintStore(state => state.interveneExecution);
  const currentTaskId = useBlueprintStore(state => state.currentTaskId);
  const { send, isConnected } = useWebSocketContext();
  
  const [isExpanded, setIsExpanded] = useState(false);

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

  const handleIntervene = () => {
    if (canIntervene) {
      interveneExecution(stepId);
    }
  };

  const handleFreeze = () => {
    if (isConnected && currentTaskId && step) {
      send('freeze_request', {
        task_id: currentTaskId,
        step_id: stepId,
        reason: '用户请求冻结并标注',
      });
    }
  };

  return (
    <div className="relative">
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
      
      {/* 主节点容器 */}
      <div 
        className={cn(
          "w-[180px] rounded-xl border-2 transition-all duration-300 bg-white relative overflow-hidden",
          config.borderColor,
          isSelected && "ring-2 ring-offset-2 ring-blue-400 shadow-lg",
          isRunning && "animate-pulse"
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
            {/* 概览 + 干涉按钮行 */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-gray-400">步骤 #{stepId.replace(/[^0-9]/g, '')}</span>
                {step.tool && (
                  <div 
                    className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-yellow-500/90 border border-yellow-600 cursor-help"
                    title={`Skill: ${step.tool}`}
                  >
                    <Wrench className="w-3 h-3 text-yellow-900" />
                    <span className="text-[9px] font-medium text-yellow-900 truncate max-w-[80px]">{step.tool}</span>
                  </div>
                )}
                {step.needsIntervention && (
                  <span className="flex items-center gap-0.5 text-[9px] text-yellow-400">
                    <AlertTriangle className="w-3 h-3" />
                    需干预
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                {isRunning && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleFreeze();
                    }}
                    className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium bg-amber-500 hover:bg-amber-600 text-white transition-colors"
                    title="冻结并标注"
                  >
                    <PauseCircle className="w-3 h-3" />
                    冻结
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleIntervene();
                  }}
                  disabled={!canIntervene}
                  className={cn(
                    "px-2 py-1 rounded text-[10px] font-medium transition-colors",
                    canIntervene
                      ? "bg-red-500 hover:bg-red-600 text-white"
                      : "bg-gray-700 text-gray-500 cursor-not-allowed"
                  )}
                >
                  重新规划
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

              {/* 依赖信息 */}
              {step.dependencies.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-700/50">
                  <p className="text-[9px] text-gray-500">
                    依赖: {step.dependencies.join(', ')}
                  </p>
                </div>
              )}
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
    </div>
  );
}
