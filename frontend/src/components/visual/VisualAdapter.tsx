import { useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
} from '@xyflow/react';
import { X, Play, Info, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolItem } from './ToolDock';

interface VisualAdapterProps {
  droppedItems: ToolItem[];
  onItemUse?: (item: ToolItem, target: 'thinking' | 'execution') => void;
  onEdit?: (item: ToolItem) => void;
}

interface OpenedItem extends ToolItem {
  openedAt: number;
}

// Vis节点组件
interface VisNodeProps {
  data: {
    item: ToolItem;
    onClick: () => void;
  };
}

function VisNodeComponent({ data }: VisNodeProps) {
  const { item, onClick } = data;
  const Icon = item.icon;
  
  return (
    <div 
      onClick={onClick}
      className={cn(
        "w-[140px] rounded-xl border-2 cursor-pointer transition-all duration-200 overflow-hidden",
        "hover:scale-105 hover:shadow-xl"
      )}
      style={{ borderColor: item.color, backgroundColor: `${item.color}20` }}
    >
      {/* 头部 */}
      <div 
        className="px-3 py-2 flex items-center gap-2"
        style={{ backgroundColor: item.color }}
      >
        <Icon className="w-4 h-4 text-slate-900" />
        <span className="text-xs font-medium text-slate-900 truncate">{item.name}</span>
      </div>
      
      {/* 内容 */}
      <div className="p-2">
        <span className={cn(
          "text-[10px] px-1.5 py-0.5 rounded",
          item.type === 'mcp' && "bg-blue-500/30 text-blue-200",
          item.type === 'skill' && "bg-purple-500/30 text-purple-200",
          item.type === 'setting' && "bg-green-500/30 text-green-200",
          item.type === 'file' && "bg-orange-500/30 text-orange-200"
        )}>
          {item.type.toUpperCase()}
        </span>
        <p className="text-[10px] text-white/60 mt-1 line-clamp-2">{item.description}</p>
      </div>
    </div>
  );
}

const nodeTypes: NodeTypes = {
  visNode: VisNodeComponent,
};

export function VisualAdapter({ droppedItems, onItemUse, onEdit }: VisualAdapterProps) {
  const [openedItems, setOpenedItems] = useState<OpenedItem[]>([]);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<ToolItem | null>(null);
  
  // ReactFlow状态
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, , onEdgesChange] = useEdgesState<Edge>([]);



  // 打开项目详情
  const openItem = (item: ToolItem) => {
    const existing = openedItems.find(i => i.id === item.id);
    if (!existing) {
      setOpenedItems(prev => [...prev, { ...item, openedAt: Date.now() }]);
    }
    setActiveTab(item.id);
    setSelectedItem(item);
  };

  // 关闭项目详情
  const closeItem = (itemId: string) => {
    setOpenedItems(prev => prev.filter(i => i.id !== itemId));
    if (activeTab === itemId) {
      const remaining = openedItems.filter(i => i.id !== itemId);
      setActiveTab(remaining.length > 0 ? remaining[0].id : null);
      setSelectedItem(remaining.length > 0 ? remaining[0] : null);
    }
  };

  // 处理拖放
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = 'copy';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // 尝试获取拖拽数据
    let data = e.dataTransfer.getData('application/json');
    
    // 如果没有数据，尝试从dataTransfer的types中获取
    if (!data) {
      const types = e.dataTransfer.types;
      for (const type of types) {
        if (type === 'application/json' || type === 'text/plain') {
          data = e.dataTransfer.getData(type);
          break;
        }
      }
    }
    
    if (data) {
      try {
        const item: ToolItem = JSON.parse(data);
        // 添加到节点列表
        const newNode: Node = {
          id: `${item.id}-${Date.now()}`,
          type: 'visNode',
          position: { 
            x: 50 + Math.random() * 200, 
            y: 50 + Math.random() * 150 
          },
          data: { 
            item,
            onClick: () => openItem(item)
          },
        };
        setNodes(prev => [...prev, newNode]);
        // 添加到已拖入列表
        setOpenedItems(prev => {
          if (prev.find(i => i.id === item.id)) return prev;
          return [...prev, { ...item, openedAt: Date.now() }];
        });
        // 打开编辑界面
        onEdit?.(item);
      } catch (err) {
        console.error('Drop error:', err);
      }
    }
  };



  return (
    <div className="w-full h-full flex flex-col bg-gradient-to-br from-pink-500/20 via-pink-400/30 to-yellow-400/20">
      {/* 顶部标签栏 */}
      <div className="flex items-center gap-1 px-2 py-2 bg-slate-900/60 border-b border-white/10 overflow-x-auto">
        <span className="text-xs text-white/60 mr-2 flex-shrink-0">vis-adapter</span>
        
        {openedItems.map((item) => (
          <button
            key={item.id}
            onClick={() => {
              setActiveTab(item.id);
              setSelectedItem(item);
            }}
            className={cn(
              "flex items-center gap-1 px-2 py-1 rounded text-xs transition-all flex-shrink-0",
              activeTab === item.id 
                ? "bg-white/20 text-white" 
                : "bg-white/5 text-white/60 hover:bg-white/10"
            )}
          >
            <div 
              className="w-2 h-2 rounded-sm" 
              style={{ backgroundColor: item.color }}
            />
            <span className="truncate max-w-[80px]">{item.name}</span>
            <X 
              className="w-3 h-3 hover:text-red-400 cursor-pointer ml-1" 
              onClick={(e) => {
                e.stopPropagation();
                closeItem(item.id);
              }}
            />
          </button>
        ))}
        
        {openedItems.length === 0 && (
          <span className="text-xs text-white/30 italic">拖拽工具到此处查看详情</span>
        )}
      </div>

      {/* 主内容区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧：ReactFlow画布 */}
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.3}
            maxZoom={2}
            className="w-full h-full"
          >
            <Background color="#ffffff30" gap={20} size={1} />
            <Controls className="bg-slate-800/80 border border-white/20" />
          </ReactFlow>
          
          {/* 拖放覆盖层 - 处理拖放事件 */}
          <div 
            className="absolute inset-0 z-50"
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            style={{ pointerEvents: 'auto' }}
          />
          
          {/* 空状态提示 */}
          {nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-40">
              <div className="text-center text-white/30">
                <Layers className="w-16 h-16 mx-auto mb-3" />
                <p className="text-sm">拖拽工具到此处</p>
                <p className="text-xs mt-1">或点击左侧工具栏图标</p>
              </div>
            </div>
          )}
        </div>

        {/* 右侧：详情面板 */}
        {selectedItem && (
          <div className="w-[280px] bg-slate-900/90 border-l border-white/10 p-4 overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs text-white/60">工具详情</span>
              <button 
                onClick={() => setSelectedItem(null)}
                className="w-6 h-6 rounded hover:bg-white/10 flex items-center justify-center"
              >
                <X className="w-4 h-4 text-white/60" />
              </button>
            </div>
            
            {(() => {
              const ItemIcon = selectedItem.icon;
              return (
                <div>
                  {/* 头部 */}
                  <div 
                    className="w-16 h-16 rounded-xl flex items-center justify-center mx-auto mb-4"
                    style={{ backgroundColor: selectedItem.color }}
                  >
                    <ItemIcon className="w-8 h-8 text-slate-900" />
                  </div>
                  
                  <h3 className="text-center text-lg font-semibold text-white mb-2">
                    {selectedItem.name}
                  </h3>
                  
                  <div className="flex justify-center mb-4">
                    <span className={cn(
                      "text-xs px-2 py-1 rounded-full",
                      selectedItem.type === 'mcp' && "bg-blue-500/30 text-blue-300",
                      selectedItem.type === 'skill' && "bg-purple-500/30 text-purple-300",
                      selectedItem.type === 'setting' && "bg-green-500/30 text-green-300",
                      selectedItem.type === 'file' && "bg-orange-500/30 text-orange-300"
                    )}>
                      {selectedItem.type.toUpperCase()}
                    </span>
                  </div>

                  {/* 描述 */}
                  <div className="bg-white/5 rounded-lg p-3 mb-4">
                    <div className="flex items-center gap-2 text-white/60 text-xs mb-2">
                      <Info className="w-3 h-3" />
                      <span>描述</span>
                    </div>
                    <p className="text-white/80 text-sm">{selectedItem.description}</p>
                  </div>

                  {/* 使用按钮 */}
                  <div className="space-y-2">
                    <button
                      onClick={() => onItemUse?.(selectedItem, 'thinking')}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm transition-colors"
                    >
                      <Play className="w-4 h-4" />
                      用于思考蓝图
                    </button>
                    <button
                      onClick={() => onItemUse?.(selectedItem, 'execution')}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm transition-colors"
                    >
                      <Play className="w-4 h-4" />
                      用于执行蓝图
                    </button>
                  </div>
                </div>
              );
            })()}
          </div>
        )}
      </div>

      {/* 底部已拖入项目 */}
      {droppedItems.length > 0 && (
        <div className="px-3 py-2 bg-slate-900/60 border-t border-white/10">
          <div className="text-xs text-white/40 mb-2">已拖入的项目：</div>
          <div className="flex flex-wrap gap-2">
            {droppedItems.map((item) => (
              <button
                key={item.id}
                onClick={() => openItem(item)}
                className={cn(
                  "flex items-center gap-2 px-2 py-1 rounded text-xs transition-colors",
                  selectedItem?.id === item.id
                    ? "bg-white/20 text-white"
                    : "bg-white/5 text-white/60 hover:bg-white/10"
                )}
              >
                <div 
                  className="w-2 h-2 rounded-sm" 
                  style={{ backgroundColor: item.color }}
                />
                {item.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
