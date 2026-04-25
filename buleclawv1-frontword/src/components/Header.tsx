import { Sparkles, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { AppPhase } from '@/types';

interface HeaderProps {
  phase: AppPhase;
  onReset: () => void;
}

const phaseLabels: Record<AppPhase, string> = {
  input: '准备中',
  thinking: '思考中',
  execution: '执行中',
  completed: '已完成',
};

const phaseColors: Record<AppPhase, string> = {
  input: 'bg-gray-100 text-gray-600',
  thinking: 'bg-blue-100 text-blue-600',
  execution: 'bg-green-100 text-green-600',
  completed: 'bg-green-100 text-green-600',
};

export function Header({ phase, onReset }: HeaderProps) {
  return (
    <header className="fixed top-0 left-0 right-0 z-40 bg-white/80 backdrop-blur-md border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-gray-900">Blueclaw</span>
          </div>

          {/* Status & Actions */}
          <div className="flex items-center gap-3">
            {/* Phase Badge */}
            <span className={cn(
              "px-3 py-1 rounded-full text-xs font-medium",
              phaseColors[phase]
            )}>
              {phaseLabels[phase]}
            </span>

            {/* Reset Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={onReset}
              className="text-gray-500 hover:text-gray-700 hover:bg-gray-100"
            >
              <RotateCcw className="w-4 h-4 mr-1" />
              重置
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
