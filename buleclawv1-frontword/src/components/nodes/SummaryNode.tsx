import { useState } from 'react';
import { CheckCircle2, Sparkles, X, RotateCcw, FileText, Check } from 'lucide-react';
import { useBlueprintStore } from '@/store/useBlueprintStore';
import { cn } from '@/lib/utils';

interface SummaryNodeProps {
  data: { stepId: string };
}

export function SummaryNodeComponent({ data }: SummaryNodeProps) {
  const { stepId } = data;
  const step = useBlueprintStore(state => state.executionSteps.find(s => s.id === stepId));
  const executionSteps = useBlueprintStore(state => state.executionSteps);
  const reset = useBlueprintStore(state => state.reset);
  
  const [isExpanded, setIsExpanded] = useState(true);

  if (!step) return null;

  // Filter out summary and get actual execution steps
  const actualSteps = executionSteps.filter(s => s.id !== 'summary');
  const completedSteps = actualSteps.filter(s => s.status === 'completed');
  const failedSteps = actualSteps.filter(s => s.status === 'failed');

  return (
    <div className="relative">
      {/* Main Node */}
      <div 
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "w-[220px] rounded-xl border-2 transition-all duration-300 cursor-pointer",
          "bg-gradient-to-br from-green-50 to-emerald-50 border-green-400",
          "shadow-lg shadow-green-200 hover:shadow-xl hover:shadow-green-200",
          "hover:scale-[1.02]"
        )}
      >
        {/* Header */}
        <div className="px-4 py-3 border-b-2 border-green-200 bg-green-100/50 rounded-t-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <span className="text-xs font-bold text-green-700 uppercase tracking-wide">
                任务完成
              </span>
            </div>
            <CheckCircle2 className="w-5 h-5 text-green-500" />
          </div>
        </div>

        {/* Content */}
        <div className="px-4 py-3">
          <h4 className="text-sm font-bold text-gray-900 mb-1">
            {step.name}
          </h4>
          <p className="text-xs text-gray-500">
            {step.description}
          </p>
          
          {/* Quick Stats */}
          <div className="mt-3 flex items-center gap-3">
            <div className="flex items-center gap-1">
              <Check className="w-3 h-3 text-green-500" />
              <span className="text-xs text-green-600 font-medium">
                {completedSteps.length} 完成
              </span>
            </div>
            {failedSteps.length > 0 && (
              <div className="flex items-center gap-1">
                <X className="w-3 h-3 text-red-500" />
                <span className="text-xs text-red-600 font-medium">
                  {failedSteps.length} 失败
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Click hint */}
        <div className="px-4 pb-3">
          <p className="text-[10px] text-green-600/70 text-center">
            {isExpanded ? '点击收起' : '点击查看详情'}
          </p>
        </div>
      </div>

      {/* Expanded Summary Panel */}
      {isExpanded && (
        <div className="absolute top-full left-0 mt-3 w-[320px] bg-white rounded-2xl border-2 border-green-200 shadow-2xl z-50 animate-slide-in">
          {/* Panel Header */}
          <div className="px-4 py-3 border-b border-green-100 bg-green-50/50 rounded-t-2xl flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-green-600" />
              <h3 className="font-semibold text-gray-900">执行摘要</h3>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsExpanded(false);
              }}
              className="w-6 h-6 rounded-full hover:bg-green-100 flex items-center justify-center transition-colors"
            >
              <X className="w-3 h-3 text-gray-500" />
            </button>
          </div>

          {/* Panel Content */}
          <div className="p-4">
            {/* Summary Stats */}
            <div className="flex items-center gap-4 mb-4 p-3 bg-green-50 rounded-xl">
              <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-lg font-bold text-gray-900">
                  {actualSteps.length} 个步骤
                </p>
                <p className="text-sm text-green-600">
                  全部执行成功
                </p>
              </div>
            </div>

            {/* Steps List */}
            <div className="space-y-2 max-h-[200px] overflow-y-auto">
              <p className="text-xs text-gray-500 font-medium mb-2">执行记录：</p>
              {actualSteps.map((s, index) => (
                <div 
                  key={s.id}
                  className="flex items-center justify-between p-2 rounded-lg bg-gray-50"
                >
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-gray-200 text-gray-600 text-[10px] flex items-center justify-center font-medium">
                      {index + 1}
                    </span>
                    <span className="text-sm text-gray-700">{s.name}</span>
                  </div>
                  <span className={cn(
                    "text-xs font-medium",
                    s.status === 'completed' && "text-green-600",
                    s.status === 'failed' && "text-red-600"
                  )}>
                    {s.status === 'completed' ? '✓' : s.status === 'failed' ? '✗' : '○'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Panel Footer */}
          <div className="px-4 py-3 border-t border-green-100 bg-gray-50/50 rounded-b-2xl">
            <button
              onClick={(e) => {
                e.stopPropagation();
                reset();
              }}
              className="w-full py-2.5 bg-green-500 hover:bg-green-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              开始新任务
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
