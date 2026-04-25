import { useState } from 'react';
import { 
  Settings, 
  Search, 
  Plus, 
  X,
  Globe,
  Code,
  Image,
  Database,
  FileText,
  Wrench,
  Sparkles,
  Cpu,
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
  content?: string;
}

// 预定义的工具列表
export const DEFAULT_TOOLS: ToolItem[] = [
  { id: 'mcp-1', name: 'Web Search', icon: Globe, color: '#F59E0B', description: 'Search the web for information', type: 'mcp' },
  { id: 'mcp-2', name: 'Code Runner', icon: Code, color: '#F59E0B', description: 'Execute code snippets', type: 'mcp' },
  { id: 'skill-1', name: 'Image Gen', icon: Image, color: '#FBBF24', description: 'Generate images from text', type: 'skill' },
  { id: 'skill-2', name: 'Data Analysis', icon: Database, color: '#FBBF24', description: 'Analyze data and create charts', type: 'skill' },
  { id: 'file-1', name: 'Document', icon: FileText, color: '#FDE68A', description: 'Document processing', type: 'file' },
  { id: 'file-2', name: 'Tools', icon: Wrench, color: '#FEF3C7', description: 'Utility tools', type: 'file' },
  { id: 'skill-3', name: 'AI Assist', icon: Sparkles, color: '#FBBF24', description: 'AI-powered assistance', type: 'skill' },
  { id: 'mcp-3', name: 'API Call', icon: Cpu, color: '#F59E0B', description: 'Call external APIs', type: 'mcp' },
];

interface ToolDockProps {
  tools: ToolItem[];
  onDragStart: (item: ToolItem) => void;
  onToolClick: (item: ToolItem) => void;
  onAddTool: () => void;
  onSearch: (query: string) => void;
  onSettings: () => void;
}

export function ToolDock({ 
  tools, 
  onDragStart, 
  onToolClick, 
  onAddTool, 
  onSearch, 
  onSettings 
}: ToolDockProps) {
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // 过滤工具
  const filteredTools = searchQuery 
    ? tools.filter(t => 
        t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.description.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : tools;

  const handleDragStart = (e: React.DragEvent, item: ToolItem) => {
    // 序列化工具数据
    const itemData = JSON.stringify(item);
    // 设置多种格式的数据以确保兼容性
    e.dataTransfer.setData('application/json', itemData);
    e.dataTransfer.setData('text/plain', itemData);
    e.dataTransfer.effectAllowed = 'copy';
    // 设置拖拽时的视觉效果
    if (e.dataTransfer.setDragImage) {
      const dragEl = e.currentTarget as HTMLElement;
      if (dragEl) {
        e.dataTransfer.setDragImage(dragEl, 20, 20);
      }
    }
    onDragStart?.(item);
  };

  return (
    <div className="w-[60px] h-full bg-slate-800/90 border-x border-slate-700/50 flex flex-col z-10 shadow-xl">
      {/* 顶部功能区 */}
      <div className="flex flex-col items-center py-3 gap-3 border-b border-slate-700/50">
        {/* 设置按钮 */}
        <button
          onClick={onSettings}
          className="w-9 h-9 rounded-lg bg-blue-600 hover:bg-blue-500 flex items-center justify-center transition-colors"
          title="设置"
        >
          <Settings className="w-4 h-4 text-white" />
        </button>

        {/* 搜索按钮 */}
        <button
          onClick={() => setShowSearch(!showSearch)}
          className={cn(
            "w-9 h-9 rounded-lg flex items-center justify-center transition-colors",
            showSearch ? "bg-blue-500" : "bg-blue-600 hover:bg-blue-500"
          )}
          title="搜索工具"
        >
          <Search className="w-4 h-4 text-white" />
        </button>

        {/* 添加按钮 */}
        <button
          onClick={onAddTool}
          className="w-9 h-9 rounded-lg bg-yellow-500 hover:bg-yellow-400 flex items-center justify-center transition-colors"
          title="新建工具"
        >
          <Plus className="w-4 h-4 text-slate-900" />
        </button>
      </div>

      {/* 搜索框 */}
      {showSearch && (
        <div className="px-2 py-2 border-b border-slate-700/50">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                onSearch?.(e.target.value);
              }}
              placeholder="搜索..."
              className="w-full px-2 py-1.5 bg-slate-700 text-white text-xs rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
              autoFocus
            />
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  onSearch?.('');
                }}
                className="absolute right-1 top-1/2 -translate-y-1/2"
              >
                <X className="w-3 h-3 text-slate-400" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* 工具列表 */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-2">
        {filteredTools.map((item) => {
          const Icon = item.icon;
          
          return (
            <div
              key={item.id}
              draggable
              onDragStart={(e) => handleDragStart(e, item)}
              onClick={() => onToolClick?.(item)}
              className={cn(
                "w-10 h-10 rounded-lg flex items-center justify-center cursor-grab active:cursor-grabbing transition-all duration-200 group relative",
                "hover:scale-110 hover:shadow-lg"
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

        {filteredTools.length === 0 && (
          <div className="text-center text-xs text-slate-500 py-4">
            无匹配工具
          </div>
        )}
      </div>
    </div>
  );
}
