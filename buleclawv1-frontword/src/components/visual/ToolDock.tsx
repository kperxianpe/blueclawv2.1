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
import type { ContentUnit, ContentConnection } from './ContentBlueprintNode';

export interface ToolBlueprint {
  title: string;          // 标题目标形容
  condition: string;      // 判断条件形容
  media: {
    images: string[];     // 图片URL数组
    text: string;         // 文字描述
  };
  connectedToolIds?: string[]; // 连线的其他黄色方块ID
  units?: ContentUnit[];       // 内容蓝图内部单元
  connections?: ContentConnection[]; // 内容蓝图内部连线
}

export interface ToolConnections {
  from: string[];          // 连入此方块的其他方块ID
  to: string[];            // 从此方块连出的其他方块ID
}

export interface ToolItem {
  id: string;
  name: string;
  icon: LucideIcon;
  color: string;
  description: string;
  type: 'mcp' | 'skill' | 'setting' | 'file';
  content?: string;             // 兼容旧字段
  blueprint?: ToolBlueprint;    // 内容蓝图
  connections?: ToolConnections; // 连线关系
}

// 预定义的工具列表
export const DEFAULT_TOOLS: ToolItem[] = [
  { id: 'mcp-1', name: 'Web Search', icon: Globe, color: '#F59E0B', description: 'Search the web for information', type: 'mcp', blueprint: { title: '通过网络搜索获取实时信息', condition: '当需要外部数据或最新信息时', media: { images: [], text: '使用搜索引擎查询相关信息，返回结构化结果' } } },
  { id: 'mcp-2', name: 'Code Runner', icon: Code, color: '#F59E0B', description: 'Execute code snippets', type: 'mcp', blueprint: { title: '执行代码片段', condition: '当需要运行代码验证结果时', media: { images: [], text: '在沙箱环境中执行代码并返回输出' } } },
  { id: 'skill-1', name: 'Image Gen', icon: Image, color: '#FBBF24', description: 'Generate images from text', type: 'skill', blueprint: { title: '根据描述生成对应图像', condition: '当需要视觉内容或创意图像时', media: { images: [], text: '将文字描述转换为高质量图像输出' } } },
  { id: 'skill-2', name: 'Data Analysis', icon: Database, color: '#FBBF24', description: 'Analyze data and create charts', type: 'skill', blueprint: { title: '分析数据并生成图表', condition: '当需要数据洞察或可视化时', media: { images: [], text: '对数据进行统计分析并生成图表' } } },
  { id: 'file-1', name: 'Document', icon: FileText, color: '#FDE68A', description: 'Document processing', type: 'file', blueprint: { title: '处理文档内容', condition: '当需要解析或生成文档时', media: { images: [], text: '读取、解析、生成各类文档格式' } } },
  { id: 'file-2', name: 'Tools', icon: Wrench, color: '#FEF3C7', description: 'Utility tools', type: 'file', blueprint: { title: '通用工具集合', condition: '当需要辅助功能或工具调用时', media: { images: [], text: '提供各类实用工具和功能' } } },
  { id: 'skill-3', name: 'AI Assist', icon: Sparkles, color: '#FBBF24', description: 'AI-powered assistance', type: 'skill', blueprint: { title: 'AI辅助推理和生成', condition: '当需要智能推理或内容生成时', media: { images: [], text: '利用AI能力进行推理、总结、生成' } } },
  { id: 'mcp-3', name: 'API Call', icon: Cpu, color: '#F59E0B', description: 'Call external APIs', type: 'mcp', blueprint: { title: '调用外部API接口', condition: '当需要外部服务数据时', media: { images: [], text: '通过HTTP请求调用第三方API' } } },
];

// 全局工具查找函数
export function findToolById(toolId: string): ToolItem | undefined {
  return DEFAULT_TOOLS.find(t => t.id === toolId);
}

// 迷你工具方块 — 只显示彩色方块，hover显示名字
export function ToolBadgeMini({ toolId, onRemove }: { toolId: string; onRemove?: () => void }) {
  const [hovered, setHovered] = useState(false);
  const tool = findToolById(toolId);
  if (!tool) return null;

  return (
    <div className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Hover tooltip */}
      {hovered && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 
                      bg-slate-800 text-white text-[10px] rounded-lg whitespace-nowrap 
                      border border-slate-600 shadow-lg z-50 pointer-events-none">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: tool.color }} />
            <span>{tool.name}</span>
            <span className="text-slate-400">({tool.type})</span>
          </div>
          <div className="absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-800 border-b border-r border-slate-600 rotate-45 -mt-1" />
        </div>
      )}
      {/* 彩色方块 */}
      <div className="group relative w-5 h-5 rounded-sm flex-shrink-0 cursor-pointer"
        style={{ backgroundColor: tool.color }}
        title={`${tool.name} (${tool.type})`}
      >
        {/* 移除按钮 */}
        {onRemove && (
          <button onClick={(e) => { e.stopPropagation(); onRemove(); }}
            className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-red-500 
                     flex items-center justify-center opacity-0 group-hover:opacity-100 
                     transition-opacity z-10">
            <X className="w-2 h-2 text-white" />
          </button>
        )}
      </div>
    </div>
  );
}

// 工具卡片组件（用于显示关联的工具）
export function ToolBadge({ toolId, onRemove, draggable = false, onDragStart }: { 
  toolId: string; 
  onRemove?: () => void;
  draggable?: boolean;
  onDragStart?: (e: React.DragEvent) => void;
}) {
  const tool = findToolById(toolId);
  if (!tool) {
    return (
      <div className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] bg-gray-700 border border-gray-600 text-gray-400">
        <span>Unknown: {toolId}</span>
        {onRemove && (
          <button onClick={onRemove} className="ml-1 w-3 h-3 rounded-full hover:bg-gray-600 flex items-center justify-center">
            <X className="w-2 h-2" />
          </button>
        )}
      </div>
    );
  }
  
  const Icon = tool.icon;
  return (
    <div
      draggable={draggable}
      onDragStart={onDragStart}
      className={cn(
        "group flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-[11px] border transition-all",
        "bg-slate-800 hover:shadow-md",
        draggable && "cursor-grab active:cursor-grabbing"
      )}
      style={{ borderColor: tool.color + '60' }}
      title={tool.description}
    >
      {/* 颜色条 */}
      <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: tool.color }} />
      {/* 图标 */}
      <Icon className="w-3 h-3 flex-shrink-0" style={{ color: tool.color }} />
      {/* 名称 */}
      <span className="text-white font-medium truncate max-w-[90px]">{tool.name}</span>
      {/* 类型标签 */}
      <span 
        className="text-[8px] px-1 rounded flex-shrink-0"
        style={{ backgroundColor: tool.color + '30', color: tool.color }}
      >
        {tool.type}
      </span>
      {/* 移除按钮 */}
      {onRemove && (
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          className="opacity-0 group-hover:opacity-100 w-4 h-4 rounded-full hover:bg-red-500/30 flex items-center justify-center transition-opacity ml-0.5"
        >
          <X className="w-2.5 h-2.5 text-red-400" />
        </button>
      )}
    </div>
  );
}

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
    const itemData = JSON.stringify(item);
    try { e.dataTransfer.setData('application/json', itemData); } catch {}
    try { e.dataTransfer.setData('text/plain', itemData); } catch {}
    e.dataTransfer.effectAllowed = 'copy';
    const el = e.currentTarget as HTMLElement;
    if (el && e.dataTransfer.setDragImage) {
      e.dataTransfer.setDragImage(el, 20, 20);
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
