import { useState } from 'react';
import { Brain, Cpu, ChevronDown, ChevronUp, AlertCircle, Sparkles, CheckCircle2, XCircle, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useBlueprintStore } from '@/store/useBlueprintStore';
import type { ThinkingNodeType, ExecutionStep } from '@/types';

interface DetailPanelProps {
  thinkingNode: ThinkingNodeType | undefined;
  executionStep: ExecutionStep | undefined;
  phase: string;
}

export function DetailPanel({ thinkingNode, executionStep, phase }: DetailPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const interveneThinking = useBlueprintStore(state => state.interveneExecution);
  const interveneExecution = useBlueprintStore(state => state.interveneExecution);

  // 判断显示什么内容
  const showThinkingDetail = thinkingNode && (phase === 'thinking' || phase === 'execution' || phase === 'completed');
  const showExecutionDetail = executionStep && (phase === 'execution' || phase === 'completed');

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Zap className="w-4 h-4 text-blue-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <div className="w-4 h-4 rounded-full border-2 border-gray-300" />;
    }
  };

  return (
    <div className="h-[280px] border-t-2 border-gray-200 bg-white flex flex-col">
      {/* Header */}
      <div 
        onClick={() => setIsExpanded(!isExpanded)}
        className="px-4 py-2 flex items-center justify-between bg-gray-50 border-b border-gray-100 cursor-pointer hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          {showExecutionDetail ? (
            <Cpu className="w-4 h-4 text-green-600" />
          ) : (
            <Brain className="w-4 h-4 text-blue-600" />
          )}
          <span className="font-medium text-gray-700 text-sm">
            {showExecutionDetail ? '执行详情' : '思考详情'}
          </span>
        </div>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        )}
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="flex-1 p-4 overflow-auto">
          {/* 思考详情 */}
          {showThinkingDetail && !showExecutionDetail && (
            <div className="h-full flex">
              {/* 左侧 - 详细信息 */}
              <div className="flex-1 pr-4">
                <div className="mb-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {thinkingNode.question}
                  </h3>
                  <p className="text-sm text-gray-500">
                    状态: {thinkingNode.status === 'selected' ? '已选择' : '待选择'}
                  </p>
                </div>

                {thinkingNode.selectedOption && (
                  <div className="p-3 bg-blue-50 rounded-lg mb-3">
                    <p className="text-xs text-gray-500 mb-1">当前选择:</p>
                    <p className="font-medium text-blue-700">
                      {thinkingNode.options.find(o => o.id === thinkingNode.selectedOption)?.label}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {thinkingNode.options.find(o => o.id === thinkingNode.selectedOption)?.description}
                    </p>
                  </div>
                )}

                {thinkingNode.customInput && (
                  <div className="p-3 bg-purple-50 rounded-lg">
                    <p className="text-xs text-gray-500 mb-1">自定义输入:</p>
                    <p className="font-medium text-purple-700">{thinkingNode.customInput}</p>
                  </div>
                )}

                {/* 选项列表 */}
                {thinkingNode.status !== 'selected' && (
                  <div className="mt-4 space-y-2">
                    <p className="text-xs text-gray-500">可选方案:</p>
                    {thinkingNode.options.map((option) => (
                      <div 
                        key={option.id}
                        className="p-2 bg-gray-100 rounded-lg flex items-center gap-2"
                      >
                        <span className="text-xs font-medium text-blue-600">{option.id}.</span>
                        <span className="text-sm text-gray-700">{option.label}</span>
                        <span className="text-xs text-gray-400 ml-auto">{option.description}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 右侧 - 红色干预按钮 */}
              {thinkingNode.status === 'selected' && phase === 'thinking' && (
                <div className="w-20 flex flex-col items-center justify-start pt-4">
                  <button
                    onClick={() => interveneThinking(thinkingNode.id)}
                    className="w-12 h-12 rounded-full bg-red-500 hover:bg-red-600 flex items-center justify-center shadow-lg shadow-red-200 transition-all hover:scale-110 animate-bounce-subtle"
                  >
                    <AlertCircle className="w-6 h-6 text-white" />
                  </button>
                  <span className="text-[10px] text-red-500 font-medium mt-1">重新思考</span>
                </div>
              )}
            </div>
          )}

          {/* 执行详情 */}
          {showExecutionDetail && (
            <div className="h-full flex">
              {/* 左侧 - 详细信息 */}
              <div className="flex-1 pr-4">
                <div className="flex items-center gap-2 mb-4">
                  {getStatusIcon(executionStep.status)}
                  <h3 className="text-lg font-semibold text-gray-900">
                    {executionStep.name}
                  </h3>
                  <span className={cn(
                    "px-2 py-0.5 rounded text-xs font-medium",
                    executionStep.status === 'running' && "bg-blue-100 text-blue-700",
                    executionStep.status === 'completed' && "bg-green-100 text-green-700",
                    executionStep.status === 'failed' && "bg-red-100 text-red-700",
                    executionStep.status === 'pending' && "bg-gray-100 text-gray-600",
                  )}>
                    {executionStep.status === 'running' && '执行中'}
                    {executionStep.status === 'completed' && '已完成'}
                    {executionStep.status === 'failed' && '失败'}
                    {executionStep.status === 'pending' && '待执行'}
                  </span>
                  {executionStep.isMainPath && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                      主路径
                    </span>
                  )}
                  {executionStep.isConvergence && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-700">
                      汇合点
                    </span>
                  )}
                </div>

                <p className="text-sm text-gray-600 mb-4">
                  {executionStep.description}
                </p>

                {/* 执行进度/结果 */}
                {executionStep.status === 'running' && (
                  <div className="mb-4">
                    <div className="flex items-center gap-2 text-sm text-blue-600 mb-2">
                      <Zap className="w-4 h-4 animate-pulse" />
                      <span>正在执行中...</span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full animate-[loading_2s_ease-in-out_infinite]" 
                           style={{ width: '60%' }} />
                    </div>
                  </div>
                )}

                {executionStep.result && (
                  <div className="p-3 bg-green-50 rounded-lg mb-3">
                    <p className="text-xs text-gray-500 mb-1">执行结果:</p>
                    <p className="text-sm text-green-700">{executionStep.result}</p>
                  </div>
                )}

                {executionStep.error && (
                  <div className="p-3 bg-red-50 rounded-lg mb-3">
                    <p className="text-xs text-gray-500 mb-1">错误信息:</p>
                    <p className="text-sm text-red-700">{executionStep.error}</p>
                  </div>
                )}

                {/* 依赖关系 */}
                {executionStep.dependencies.length > 0 && (
                  <div className="mt-4">
                    <p className="text-xs text-gray-500 mb-2">前置依赖:</p>
                    <div className="flex flex-wrap gap-2">
                      {executionStep.dependencies.map((depId) => (
                        <span key={depId} className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-600">
                          {depId}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* 右侧 - 红色干预按钮 */}
              {(executionStep.status === 'failed' || executionStep.needsIntervention) && (
                <div className="w-20 flex flex-col items-center justify-start pt-4">
                  <button
                    onClick={() => interveneExecution(executionStep.id)}
                    className="w-12 h-12 rounded-full bg-red-500 hover:bg-red-600 flex items-center justify-center shadow-lg shadow-red-200 transition-all hover:scale-110 animate-bounce-subtle"
                  >
                    <AlertCircle className="w-6 h-6 text-white" />
                  </button>
                  <span className="text-[10px] text-red-500 font-medium mt-1">干预</span>
                </div>
              )}
            </div>
          )}

          {/* 空状态 */}
          {!showThinkingDetail && !showExecutionDetail && (
            <div className="h-full flex items-center justify-center text-gray-400">
              <div className="text-center">
                <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">点击节点查看详细信息</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
