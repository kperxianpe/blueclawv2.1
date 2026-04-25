import { useState } from 'react';
import { Play, Brain, Snowflake } from 'lucide-react';
import { cn } from '@/lib/utils';

export type InterferenceAction = 'reexecute' | 'rethink' | 'freeze';

interface InterferencePanelProps {
  isOpen: boolean;
  onClose: () => void;
  onAction: (action: InterferenceAction) => void;
}

const interferenceButtons = [
  {
    id: 'reexecute' as const,
    title: '从当前节点重新执行',
    icon: Play,
    color: 'bg-blue-500 hover:bg-blue-400',
    ring: 'ring-blue-300',
  },
  {
    id: 'rethink' as const,
    title: '从当前节点前开始重新思考',
    icon: Brain,
    color: 'bg-purple-500 hover:bg-purple-400',
    ring: 'ring-purple-300',
  },
  {
    id: 'freeze' as const,
    title: '冻结执行',
    icon: Snowflake,
    color: 'bg-cyan-500 hover:bg-cyan-400',
    ring: 'ring-cyan-300',
  },
];

export function InterferencePanel({
  isOpen,
  onClose,
  onAction,
}: InterferencePanelProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  if (!isOpen) return null;

  return (
    <div className="absolute -right-2 top-7 z-[70]">
      <div className="flex flex-col gap-1 p-1.5 bg-slate-800/95 rounded-xl border border-slate-600/50 shadow-xl backdrop-blur-sm">
        {interferenceButtons.map((btn) => {
          const Icon = btn.icon;
          return (
            <div key={btn.id} className="relative">
              {/* Tooltip */}
              {hoveredId === btn.id && (
                <div
                  className={cn(
                    "absolute right-full mr-2 top-1/2 -translate-y-1/2 px-2.5 py-1 rounded-lg text-[11px] font-medium whitespace-nowrap z-[80]",
                    "bg-slate-700 text-white border border-slate-600 shadow-lg"
                  )}
                >
                  {btn.title}
                  {/* 小三角箭头 */}
                  <div className="absolute right-[-4px] top-1/2 -translate-y-1/2 w-2 h-2 bg-slate-700 border-r border-t border-slate-600 rotate-45" />
                </div>
              )}

              {/* 按钮 */}
              <button
                onMouseEnter={() => setHoveredId(btn.id)}
                onMouseLeave={() => setHoveredId(null)}
                onClick={(e) => {
                  e.stopPropagation();
                  onAction(btn.id);
                  onClose();
                }}
                className={cn(
                  "w-7 h-7 rounded-lg flex items-center justify-center transition-all",
                  "text-white shadow-md border border-white/20",
                  btn.color,
                  "hover:scale-110 active:scale-95"
                )}
                title={btn.title}
              >
                <Icon className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>

      {/* 点击外部关闭 */}
      <div
        className="fixed inset-0 z-[60]"
        onClick={onClose}
      />
    </div>
  );
}
