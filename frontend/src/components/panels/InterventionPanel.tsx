import { useState } from 'react';
import { AlertCircle, Play, GitBranch, Square, X, Clock, Loader2, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SuggestedAction } from '@/types/websocket';

interface InterventionPanelProps {
  isOpen: boolean;
  onClose: () => void;
  stepName: string;
  stepStatus?: 'failed' | 'paused' | 'running';
  stepDurationMs?: number;
  suggestedActions?: SuggestedAction[];
  onAction: (action: 'continue' | 'newBranch' | 'stop', customInput?: string) => void;
}

const defaultOptions = [
  {
    id: 'continue' as const,
    title: '继续执行',
    description: '跳过当前步骤，继续后续执行',
    icon: Play,
  },
  {
    id: 'newBranch' as const,
    title: '重新规划',
    description: '从当前步骤后重新思考并生成新蓝图',
    icon: GitBranch,
  },
  {
    id: 'stop' as const,
    title: '完全停止',
    description: '终止当前任务执行',
    icon: Square,
  },
];

const statusConfig = {
  failed: { label: '执行失败', color: 'text-red-600', bg: 'bg-red-50', icon: AlertCircle },
  paused: { label: '已暂停', color: 'text-amber-600', bg: 'bg-amber-50', icon: Loader2 },
  running: { label: '执行中', color: 'text-blue-600', bg: 'bg-blue-50', icon: CheckCircle2 },
};

function formatDuration(ms?: number): string {
  if (!ms || ms <= 0) return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}min`;
}

export function InterventionPanel({
  isOpen,
  onClose,
  stepName,
  stepStatus = 'failed',
  stepDurationMs,
  suggestedActions,
  onAction,
}: InterventionPanelProps) {
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  const [customInput, setCustomInput] = useState('');

  if (!isOpen) return null;

  const status = statusConfig[stepStatus] || statusConfig.failed;
  const StatusIcon = status.icon;

  const options = suggestedActions
    ? suggestedActions.map((sa, idx) => {
        const fallback = defaultOptions[idx] || defaultOptions[0];
        return {
          id: sa.id as 'continue' | 'newBranch' | 'stop',
          title: sa.label || fallback.title,
          description: sa.description || fallback.description,
          icon: fallback.icon,
        };
      })
    : defaultOptions;

  const handleConfirm = () => {
    if (selectedAction) {
      onAction(
        selectedAction as 'continue' | 'newBranch' | 'stop',
        selectedAction === 'newBranch' ? customInput : undefined
      );
      setSelectedAction(null);
      setCustomInput('');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className={cn('px-6 py-4 border-b', status.bg)}>
          <div className="flex items-center gap-3">
            <div className={cn('w-10 h-10 rounded-full flex items-center justify-center', status.color.replace('text-', 'bg-'))}>
              <StatusIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">需要干预</h3>
              <p className="text-sm text-gray-500">"{stepName}" {status.label}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Step Info Card */}
          <div className="mb-4 p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">当前步骤</span>
              <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', status.bg, status.color)}>
                {status.label}
              </span>
            </div>
            <div className="mt-1 font-medium text-gray-900">{stepName}</div>
            <div className="mt-1 flex items-center gap-1 text-xs text-gray-400">
              <Clock className="w-3 h-3" />
              <span>已耗时: {formatDuration(stepDurationMs)}</span>
            </div>
          </div>

          <p className="text-sm text-gray-600 mb-4">请选择处理方式：</p>

          {/* Dynamic Options */}
          <div className="space-y-3">
            {options.map((option) => {
              const OptionIcon = option.icon;
              return (
                <button
                  key={option.id}
                  onClick={() => setSelectedAction(option.id)}
                  className={cn(
                    'w-full p-4 rounded-xl border-2 text-left transition-all duration-200',
                    selectedAction === option.id
                      ? 'border-red-500 bg-red-50'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={cn(
                        'w-10 h-10 rounded-lg flex items-center justify-center transition-colors',
                        selectedAction === option.id ? 'bg-red-500' : 'bg-gray-100'
                      )}
                    >
                      <OptionIcon
                        className={cn('w-5 h-5', selectedAction === option.id ? 'text-white' : 'text-gray-500')}
                      />
                    </div>
                    <div className="flex-1">
                      <h4 className={cn('font-medium', selectedAction === option.id ? 'text-red-900' : 'text-gray-900')}>
                        {option.title}
                      </h4>
                      <p
                        className={cn(
                          'text-sm mt-0.5',
                          selectedAction === option.id ? 'text-red-600' : 'text-gray-500'
                        )}
                      >
                        {option.description}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Custom Input for Replan */}
          {selectedAction === 'newBranch' && (
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">调整方向（可选）</label>
              <textarea
                value={customInput}
                onChange={(e) => setCustomInput(e.target.value)}
                placeholder="例如：改为亲子游路线，增加科技馆和动物园"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent text-sm"
                rows={3}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-between">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors">
            取消
          </button>
          <button
            onClick={handleConfirm}
            disabled={!selectedAction}
            className={cn(
              'px-6 py-2 rounded-lg text-sm font-medium transition-all',
              selectedAction
                ? 'bg-red-500 text-white hover:bg-red-600'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            )}
          >
            确认
          </button>
        </div>
      </div>
    </div>
  );
}
