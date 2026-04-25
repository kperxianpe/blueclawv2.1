import { useState } from 'react';
import { AlertCircle, Play, GitBranch, Square, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface InterventionPanelProps {
  isOpen: boolean;
  onClose: () => void;
  stepName: string;
  onAction: (action: 'continue' | 'newBranch' | 'stop') => void;
}

const interventionOptions = [
  {
    id: 'continue' as const,
    title: '继续执行',
    description: '跳过当前步骤，继续后续执行',
    icon: Play,
  },
  {
    id: 'newBranch' as const,
    title: '生成新分支',
    description: '从当前步骤后创建新的执行路径',
    icon: GitBranch,
  },
  {
    id: 'stop' as const,
    title: '完全停止',
    description: '终止当前任务执行',
    icon: Square,
  },
];

export function InterventionPanel({ 
  isOpen, 
  onClose, 
  stepName,
  onAction,
}: InterventionPanelProps) {
  const [selectedAction, setSelectedAction] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConfirm = () => {
    if (selectedAction) {
      onAction(selectedAction as 'continue' | 'newBranch' | 'stop');
      setSelectedAction(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 bg-red-50 border-b border-red-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-red-500 flex items-center justify-center">
              <AlertCircle className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">需要干预</h3>
              <p className="text-sm text-gray-500">
                "{stepName}" 执行遇到问题
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-8 h-8 rounded-full hover:bg-red-100 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <p className="text-sm text-gray-600 mb-4">
            请选择处理方式：
          </p>

          {/* Options */}
          <div className="space-y-3">
            {interventionOptions.map((option) => (
              <button
                key={option.id}
                onClick={() => setSelectedAction(option.id)}
                className={cn(
                  "w-full p-4 rounded-xl border-2 text-left transition-all duration-200",
                  selectedAction === option.id
                    ? "border-red-500 bg-red-50"
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                )}
              >
                <div className="flex items-start gap-3">
                  <div className={cn(
                    "w-10 h-10 rounded-lg flex items-center justify-center transition-colors",
                    selectedAction === option.id ? "bg-red-500" : "bg-gray-100"
                  )}>
                    <option.icon className={cn(
                      "w-5 h-5",
                      selectedAction === option.id ? "text-white" : "text-gray-500"
                    )} />
                  </div>
                  <div className="flex-1">
                    <h4 className={cn(
                      "font-medium",
                      selectedAction === option.id ? "text-red-900" : "text-gray-900"
                    )}>
                      {option.title}
                    </h4>
                    <p className={cn(
                      "text-sm mt-0.5",
                      selectedAction === option.id ? "text-red-600" : "text-gray-500"
                    )}>
                      {option.description}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleConfirm}
            disabled={!selectedAction}
            className={cn(
              "px-6 py-2 rounded-lg text-sm font-medium transition-all",
              selectedAction
                ? "bg-red-500 text-white hover:bg-red-600"
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
            )}
          >
            确认
          </button>
        </div>
      </div>
    </div>
  );
}
