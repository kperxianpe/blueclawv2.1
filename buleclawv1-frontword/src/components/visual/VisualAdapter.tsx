import { useState, useCallback, useEffect, useRef } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge,
  type NodeTypes,
} from '@xyflow/react';
import { X, Plus, Layers, Globe, Code2, LayoutDashboard, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolItem } from './ToolDock';
import { WebBrowser } from './WebBrowser';
import { IDE } from './IDE';
import { AdapterDefault } from './AdapterDefault';
import { ContentBlueprintNodeComponent, type ContentUnit, type ContentConnection } from './ContentBlueprintNode';

// ============ 类型定义 ============

interface VisualAdapterProps {
  droppedItems: ToolItem[];
  onItemUse?: (item: ToolItem, target: 'thinking' | 'execution') => void;
  onEdit?: (item: ToolItem) => void;
  isFrozen?: boolean;
}

export type TabType = 'canvas' | 'web' | 'ide' | 'default';

export interface TabInfo {
  id: string;
  label: string;
  type: TabType;
  closable: boolean;
}

// ============ Vis节点组件 ============

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
      <div
        className="px-3 py-2 flex items-center gap-2"
        style={{ backgroundColor: item.color }}
      >
        <Icon className="w-4 h-4 text-slate-900" />
        <span className="text-xs font-medium text-slate-900 truncate">{item.name}</span>
      </div>
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
  contentBlueprint: ContentBlueprintNodeComponent,
};

// ============ 新建标签页对话框 ============

function NewTabDialog({
  isOpen,
  onClose,
  onCreate
}: {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string, type: TabType) => void;
}) {
  const [name, setName] = useState('');
  const [selectedType, setSelectedType] = useState<TabType>('default');

  if (!isOpen) return null;

  const typeOptions: { type: TabType; label: string; icon: React.ElementType; desc: string }[] = [
    { type: 'default', label: 'Adapter', icon: LayoutDashboard, desc: '任务详情与进度面板' },
    { type: 'web', label: 'Web浏览器', icon: Globe, desc: '内嵌浏览器' },
    { type: 'ide', label: 'IDE', icon: Code2, desc: '代码编辑器' },
    { type: 'canvas', label: '画布', icon: Layers, desc: '可视化画布' },
  ];

  const handleCreate = () => {
    if (name.trim()) {
      onCreate(name.trim(), selectedType);
      setName('');
      setSelectedType('default');
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-800 border border-slate-600 rounded-2xl p-6 w-[420px] shadow-2xl">
        <h3 className="text-lg font-semibold text-white mb-1">新建 Adapter 标签页</h3>
        <p className="text-sm text-slate-400 mb-4">输入名称并选择类型</p>

        <div className="mb-4">
          <label className="text-xs text-slate-400 mb-1.5 block">标签页名称</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            placeholder="例如: 任务监控、浏览器、编辑器..."
            className="w-full px-3 py-2.5 bg-slate-700/80 border border-slate-600 rounded-lg text-sm text-white placeholder:text-slate-500 outline-none focus:border-blue-500 transition-colors"
            autoFocus
          />
        </div>

        <div className="mb-6">
          <label className="text-xs text-slate-400 mb-2 block">页面类型</label>
          <div className="grid grid-cols-2 gap-2">
            {typeOptions.map(opt => {
              const Icon = opt.icon;
              return (
                <button
                  key={opt.type}
                  onClick={() => setSelectedType(opt.type)}
                  className={cn(
                    "flex items-center gap-2.5 px-3 py-2.5 rounded-lg border text-left transition-all",
                    selectedType === opt.type
                      ? "border-blue-500 bg-blue-500/10"
                      : "border-slate-600 bg-slate-700/30 hover:border-slate-500"
                  )}
                >
                  <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0", selectedType === opt.type ? "bg-blue-500/20" : "bg-slate-600/30")}>
                    <Icon className={cn("w-4 h-4", selectedType === opt.type ? "text-blue-400" : "text-slate-400")} />
                  </div>
                  <div>
                    <div className={cn("text-xs font-medium", selectedType === opt.type ? "text-blue-300" : "text-slate-300")}>{opt.label}</div>
                    <div className="text-[10px] text-slate-500">{opt.desc}</div>
                  </div>
                  {selectedType === opt.type && <Check className="w-3.5 h-3.5 text-blue-400 ml-auto flex-shrink-0" />}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-sm text-slate-300 hover:bg-slate-700 transition-colors">取消</button>
          <button onClick={handleCreate} disabled={!name.trim()} className={cn("px-4 py-2 rounded-lg text-sm font-medium transition-colors", name.trim() ? "bg-blue-600 hover:bg-blue-500 text-white" : "bg-slate-600 text-slate-400 cursor-not-allowed")}>创建</button>
        </div>
      </div>
    </div>
  );
}

// ============ 画布页面组件 ============

function CanvasPageInner({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onAddNode,
  onEdit,
}: {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: any;
  onEdgesChange: any;
  onAddNode: (node: Node) => void;
  onEdit: (item: ToolItem) => void;
}) {
  const { screenToFlowPosition } = useReactFlow();
  const [isDragOver, setIsDragOver] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // 核心drop处理函数
  const processDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    let data: string | null = null;
    try { data = e.dataTransfer?.getData('application/json') || null; } catch {}
    if (!data) try { data = e.dataTransfer?.getData('text/plain') || null; } catch {}

    if (data) {
      try {
        const item: ToolItem = JSON.parse(data);

        const newNode: Node = {
          id: `${item.id}-${Date.now()}`,
          type: 'contentBlueprint',
          position: {
            x: 50,
            y: 50,
          },
          data: {
            item,
            onClick: () => onEdit(item),
          },
        };
        onAddNode(newNode);
      } catch (err) {
        console.error('[Canvas] Drop error:', err);
      }
    }
  }, [screenToFlowPosition, onAddNode, onEdit]);

  const processDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
    setIsDragOver(true);
  }, []);

  const processDragLeave = useCallback((e: DragEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const { clientX, clientY } = e;
    if (
      clientX < rect.left ||
      clientX > rect.right ||
      clientY < rect.top ||
      clientY > rect.bottom
    ) {
      setIsDragOver(false);
    }
  }, []);

  // 使用原生事件监听作为fallback，确保真实浏览器拖放兼容
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 原生事件监听 — 确保真实拖放能工作
    container.addEventListener('dragover', processDragOver, true);
    container.addEventListener('dragleave', processDragLeave, true);
    container.addEventListener('drop', processDrop, true);

    return () => {
      container.removeEventListener('dragover', processDragOver, true);
      container.removeEventListener('dragleave', processDragLeave, true);
      container.removeEventListener('drop', processDrop, true);
    };
  }, [processDragOver, processDragLeave, processDrop]);

  // React合成事件处理（作为冗余备份）
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setIsDragOver(true);
  }, []);

  return (
    <div ref={containerRef} className="flex-1 relative w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        minZoom={0.2}
        maxZoom={3}
        className="w-full h-full"
        onDragOver={handleDragOver}
        onInit={(instance) => {
          instance.setViewport({ x: 0, y: 0, zoom: 1 });
        }}
      >
        <Background color="#ffffff30" gap={20} size={1} />
        <Controls className="bg-slate-800/80 border border-white/20" />
      </ReactFlow>

      {/* 拖放高亮层 — 只在拖拽时显示 */}
      <div
        className={cn(
          'absolute inset-0 z-50 pointer-events-none flex items-center justify-center transition-opacity duration-200',
          isDragOver ? 'opacity-100' : 'opacity-0'
        )}
        style={{
          backgroundColor: isDragOver ? 'rgba(251,191,36,0.08)' : 'transparent',
          border: isDragOver ? '2px dashed rgba(251,191,36,0.6)' : 'none',
        }}
      >
        <span
          className={cn(
            'text-yellow-400 text-sm font-medium px-4 py-2 rounded-lg bg-slate-900/60 backdrop-blur-sm transition-opacity duration-200',
            isDragOver ? 'opacity-100' : 'opacity-0'
          )}
        >
          释放创建内容蓝图
        </span>
      </div>

      {/* 空状态提示 */}
      {nodes.length === 0 && !isDragOver && (
        <div className="absolute inset-0 flex items-center justify-center z-20 pointer-events-none">
          <div className="text-center text-white/30">
            <Layers className="w-16 h-16 mx-auto mb-3" />
            <p className="text-sm">拖拽工具到此处</p>
            <p className="text-xs mt-1">创建黄色内容蓝图</p>
          </div>
        </div>
      )}
    </div>
  );
}

// 使用 Provider 包裹，使 useReactFlow 可用
function CanvasPage(props: {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: any;
  onEdgesChange: any;
  onAddNode: (node: Node) => void;
  onEdit: (item: ToolItem) => void;
}) {
  return (
    <ReactFlowProvider>
      <CanvasPageInner {...props} />
    </ReactFlowProvider>
  );
}

// ============ 主组件 ============

export function VisualAdapter({ onEdit, isFrozen = false }: VisualAdapterProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, , onEdgesChange] = useEdgesState<Edge>([]);

  const [tabs, setTabs] = useState<TabInfo[]>([
    { id: 'canvas', label: '画布', type: 'canvas', closable: false },
    { id: 'web', label: 'Web', type: 'web', closable: false },
    { id: 'ide', label: 'IDE', type: 'ide', closable: false },
  ]);
  const [activeTabId, setActiveTabId] = useState('canvas');
  const [showNewTabDialog, setShowNewTabDialog] = useState(false);

  // 处理画布添加节点
  const handleAddNode = useCallback((newNode: Node) => {
    // 设置只读标志：mcp/skill 为只读，file/setting 可编辑
    const item = newNode.data?.item as ToolItem | undefined;
    const isReadOnly = item ? (item.type === 'mcp' || item.type === 'skill') : false;

    // 提供保存回调
    const onSave = (units: ContentUnit[], connections: ContentConnection[]) => {
      setNodes(prev => prev.map(n => {
        if (n.id !== newNode.id) return n;
        const nodeItem = n.data?.item as ToolItem | undefined;
        if (!nodeItem) return n;
        return {
          ...n,
          data: {
            ...n.data,
            item: {
              ...nodeItem,
              blueprint: {
                ...(nodeItem.blueprint || {}),
                units,
                connections,
              },
            },
          },
        };
      }));
    };

    const enrichedNode: Node = {
      ...newNode,
      data: {
        ...newNode.data,
        isReadOnly,
        onSave,
      },
    };
    setNodes(prev => [...prev, enrichedNode]);
  }, [setNodes]);

  const handleCreateTab = useCallback((name: string, type: TabType) => {
    const newTab: TabInfo = {
      id: `tab-${Date.now()}`,
      label: name,
      type,
      closable: true,
    };
    setTabs(prev => [...prev, newTab]);
    setActiveTabId(newTab.id);
  }, []);

  const handleCloseTab = useCallback((tabId: string) => {
    setTabs(prev => {
      const newTabs = prev.filter(t => t.id !== tabId);
      if (newTabs.length > 0) {
        setActiveTabId(newTabs[newTabs.length - 1].id);
      }
      return newTabs;
    });
  }, []);

  const activeTab = tabs.find(t => t.id === activeTabId) || tabs[0];

  const renderTabIcon = (type: TabType) => {
    switch (type) {
      case 'canvas': return <Layers className="w-3 h-3" />;
      case 'web': return <Globe className="w-3 h-3" />;
      case 'ide': return <Code2 className="w-3 h-3" />;
      case 'default': return <LayoutDashboard className="w-3 h-3" />;
      default: return <LayoutDashboard className="w-3 h-3" />;
    }
  };

  const renderTabContent = () => {
    if (!activeTab) return null;
    switch (activeTab.type) {
      case 'canvas':
        return <CanvasPage nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onAddNode={handleAddNode} onEdit={(item) => onEdit?.(item)} />;
      case 'web': return <WebBrowser />;
      case 'ide': return <IDE />;
      case 'default': return <AdapterDefault />;
      default: return <AdapterDefault />;
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-slate-900">
      {/* 顶部标签栏 */}
      <div className={cn(
        "flex items-center gap-0.5 px-1 py-1 border-b border-slate-700/50 overflow-x-auto transition-colors",
        isFrozen ? "bg-red-900/60" : "bg-slate-800/90"
      )}>
        {isFrozen && (
          <div className="flex items-center gap-1 px-2 py-1 mr-1 bg-cyan-500/20 rounded text-cyan-300 text-[10px] flex-shrink-0">
            <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse" />
            已冻结
          </div>
        )}
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { if (!isFrozen) setActiveTabId(tab.id); }}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-all flex-shrink-0 group",
              isFrozen && "opacity-50 cursor-not-allowed",
              !isFrozen && activeTabId === tab.id ? "bg-slate-700 text-white" : "text-slate-400 hover:bg-slate-700/50 hover:text-slate-200"
            )}
          >
            {renderTabIcon(tab.type)}
            <span className="truncate max-w-[80px]">{tab.label}</span>
            {tab.closable && (
              <X
                className={cn(
                  "w-3 h-3 rounded-full transition-colors flex-shrink-0",
                  activeTabId === tab.id ? "hover:bg-red-500/20 hover:text-red-400 text-slate-400" : "opacity-0 group-hover:opacity-100 hover:bg-red-500/20 hover:text-red-400"
                )}
                onClick={(e) => { e.stopPropagation(); handleCloseTab(tab.id); }}
              />
            )}
          </button>
        ))}
        <button
          onClick={() => setShowNewTabDialog(true)}
          className="w-6 h-6 rounded-md hover:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-white transition-colors flex-shrink-0 ml-1"
          title="新建标签页"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 主内容区域 */}
      <div className="flex-1 overflow-hidden">
        {renderTabContent()}
      </div>

      {/* 新建标签页对话框 */}
      <NewTabDialog
        isOpen={showNewTabDialog}
        onClose={() => setShowNewTabDialog(false)}
        onCreate={handleCreateTab}
      />
    </div>
  );
}
