import { useState } from 'react';
import { 
  FileText, 
  Settings, 
  Wrench, 
  Database, 
  Image, 
  Code,
  Globe,
  Sparkles,
  type LucideIcon
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ToolItem {
  id: string;
  name: string;
  icon: LucideIcon;
  color: string;
  description: string;
  type: 'mcp' | 'skill' | 'setting' | 'file';
}

// 预定义的工具列表
export const TOOL_ITEMS: ToolItem[] = [
  { id: 'mcp-1', name: 'Web Search', icon: Globe, color: '#F59E0B', description: 'Search the web for information', type: 'mcp' },
  { id: 'mcp-2', name: 'Code Runner', icon: Code, color: '#F59E0B', description: 'Execute code snippets', type: 'mcp' },
  { id: 'skill-1', name: 'Image Gen', icon: Image, color: '#FBBF24', description: 'Generate images from text', type: 'skill' },
  { id: 'skill-2', name: 'Data Analysis', icon: Database, color: '#FBBF24', description: 'Analyze data and create charts', type: 'skill' },
  { id: 'setting-1', name: 'Config', icon: Settings, color: '#FCD34D', description: 'System configuration', type: 'setting' },
  { id: 'file-1', name: 'Document', icon: FileText, color: '#FDE68A', description: 'Document processing', type: 'file' },
  { id: 'file-2', name: 'Tools', icon: Wrench, color: '#FEF3C7', description: 'Utility tools', type: 'file' },
  { id: 'skill-3', name: 'AI Assist', icon: Sparkles, color: '#FBBF24', description: 'AI-powered assistance', type: 'skill' },
];

interface VisualToolBarProps {
  onDragStart?: (item: ToolItem) => void;
  onItemClick?: (item: ToolItem) => void;
}

export function VisualToolBar({ onDragStart, onItemClick }: VisualToolBarProps) {
  const [draggedItem, setDraggedItem] = useState<string | null>(null);

  const handleDragStart = (e: React.DragEvent, item: ToolItem) => {
    setDraggedItem(item.id);
    
    // 设置拖拽数据
    e.dataTransfer.setData('application/json', JSON.stringify(item));
    e.dataTransfer.effectAllowed = 'copy';
    
    // 创建自定义拖拽图像
    const dragImage = document.createElement('div');
    dragImage.className = 'w-12 h-12 rounded-lg flex items-center justify-center shadow-lg';
    dragImage.style.backgroundColor = item.color;
    dragImage.innerHTML = '<svg class="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/></svg>';
    document.body.appendChild(dragImage);
    e.dataTransfer.setDragImage(dragImage, 24, 24);
    setTimeout(() => document.body.removeChild(dragImage), 0);
    
    onDragStart?.(item);
  };

  const handleDragEnd = () => {
    setDraggedItem(null);
  };

  return (
    <div className="w-[60px] h-full bg-slate-800/90 border-r border-slate-700/50 flex flex-col items-center py-3 gap-2 overflow-y-auto">
      <div className="text-[10px] text-slate-400 font-medium mb-1">工具</div>
      
      {TOOL_ITEMS.map((item) => {
        const Icon = item.icon;
        const isDragged = draggedItem === item.id;
        
        return (
          <div
            key={item.id}
            draggable
            onDragStart={(e) => handleDragStart(e, item)}
            onDragEnd={handleDragEnd}
            onClick={() => onItemClick?.(item)}
            className={cn(
              "w-10 h-10 rounded-lg flex items-center justify-center cursor-grab active:cursor-grabbing transition-all duration-200 group relative",
              "hover:scale-110 hover:shadow-lg",
              isDragged && "opacity-50 scale-95"
            )}
            style={{ backgroundColor: item.color }}
            title={item.name}
          >
            <Icon className="w-5 h-5 text-slate-900" />
            
            {/* 悬停提示 */}
            <div className="absolute left-full ml-2 px-2 py-1 bg-slate-900 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
              {item.name}
              <div className="text-[10px] text-slate-400">{item.description}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
