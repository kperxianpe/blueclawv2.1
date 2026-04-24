import { useState } from 'react';
import { Plus, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolItem } from './VisualToolBar';

interface DropZoneProps {
  label: string;
  onDrop: (item: ToolItem) => void;
  droppedItems?: ToolItem[];
  className?: string;
}

export function DropZone({ label, onDrop, droppedItems = [], className }: DropZoneProps) {
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setIsDraggingOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingOver(false);
    
    const data = e.dataTransfer.getData('application/json');
    if (data) {
      try {
        const item: ToolItem = JSON.parse(data);
        onDrop(item);
      } catch {
        // Ignore invalid data
      }
    }
  };

  return (
    <div
      className={cn(
        "relative rounded-lg border-2 border-dashed transition-all duration-200",
        isDraggingOver 
          ? "border-yellow-400 bg-yellow-400/20 scale-105" 
          : "border-white/20 bg-white/5 hover:border-white/40",
        className
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* 拖放提示 */}
      {droppedItems.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-white/40">
          <Plus className={cn(
            "w-6 h-6 mb-1 transition-transform",
            isDraggingOver && "scale-125 text-yellow-400"
          )} />
          <span className="text-xs">{label}</span>
        </div>
      )}

      {/* 已拖入的项目 */}
      {droppedItems.length > 0 && (
        <div className="p-2 space-y-1">
          {droppedItems.map((item, index) => (
            <div
              key={`${item.id}-${index}`}
              className="flex items-center gap-2 px-2 py-1.5 bg-white/10 rounded text-white text-xs"
            >
              <div 
                className="w-2 h-2 rounded-sm flex-shrink-0" 
                style={{ backgroundColor: item.color }}
              />
              <span className="truncate flex-1">{item.name}</span>
              <Check className="w-3 h-3 text-green-400 flex-shrink-0" />
            </div>
          ))}
        </div>
      )}

      {/* 拖拽悬停效果 */}
      {isDraggingOver && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="px-3 py-1.5 bg-yellow-400 text-slate-900 text-xs font-medium rounded-full shadow-lg">
            释放以添加
          </div>
        </div>
      )}
    </div>
  );
}
