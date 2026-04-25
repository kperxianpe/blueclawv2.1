import { useState, memo, useEffect } from 'react';
import { Handle, Position } from '@xyflow/react';
import { useBlueprintStore } from '@/store/useBlueprintStore';
import { cn } from '@/lib/utils';
import { Brain, ChevronDown, ChevronUp, Sparkles, ArrowRight, RotateCcw, Save } from 'lucide-react';
import type { ToolItem } from '../visual/ToolDock';
import { ToolBadgeMini, findToolById } from '../visual/ToolDock';

interface ThinkingNodeProps {
  data: { nodeId: string };
  selected?: boolean;
}

const ThinkingNodeComponent = memo(({ data, selected }: ThinkingNodeProps) => {
  const { nodeId } = data;
  const node = useBlueprintStore((state) => state.thinkingNodes.find((n) => n.id === nodeId));
  const phase = useBlueprintStore((state) => state.phase);
  const selectThinkingNode = useBlueprintStore((state) => state.selectThinkingNode);
  const addToolToThinkingNode = useBlueprintStore((state) => state.addToolToThinkingNode);
  const removeToolFromThinkingNode = useBlueprintStore((state) => state.removeToolFromThinkingNode);
  const selectThinkingOption = useBlueprintStore((state) => state.selectThinkingOption);
  const setCustomInputAction = useBlueprintStore((state) => state.setCustomInput);

  const [isExpanded, setIsExpanded] = useState(false);
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customInput, setCustomInput] = useState('');
  const [isSaved, setIsSaved] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  // 当节点选择完成后自动折叠
  useEffect(() => {
    if (node?.status === 'selected' && isExpanded) {
      setIsExpanded(false);
    }
  }, [node?.status]);

  if (!node) return null;

  const isSelected = selected;
  const hasAssociatedTools = (node.associatedTools || []).length > 0;

  const handleExpand = () => {
    setIsExpanded(!isExpanded);
    if (!isExpanded) selectThinkingNode(nodeId);
  };

  const handleOptionClick = (optionId: string) => {
    if (node.status === 'pending' && phase === 'thinking') {
      selectThinkingOption(nodeId, optionId);
      setIsExpanded(false);
    }
  };

  const handleCustomSubmit = () => {
    if (customInput.trim()) {
      setCustomInputAction(nodeId, customInput.trim());
      setShowCustomInput(false);
      setCustomInput('');
      setIsExpanded(false);
    }
  };

  // 拖放接收
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = 'copy';
    if (isExpanded) setDragOver(true);
  };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    let data: string | null = null;
    try { data = e.dataTransfer.getData('application/json'); } catch {}
    if (!data) try { data = e.dataTransfer.getData('text/plain'); } catch {}
    if (data) {
      try {
        const item: ToolItem = JSON.parse(data);
        if (!node.associatedTools?.includes(item.id)) {
          addToolToThinkingNode(nodeId, item.id);
          setIsSaved(false);
        }
      } catch {}
    }
  };

  const handleRemoveTool = (toolId: string) => {
    removeToolFromThinkingNode(nodeId, toolId);
    setIsSaved(false);
  };

  return (
    <div className="relative" onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}>
      {/* 输入Handle */}
      <Handle type="target" position={Position.Top} id="top" style={{ background: '#3B82F6', width: 10, height: 10, top: -5 }} />

      <div className={cn(
        "w-[240px] rounded-xl border-2 overflow-hidden transition-all duration-300 bg-white shadow-sm",
        isSelected ? "ring-2 ring-offset-2 ring-blue-400 shadow-lg border-blue-500" : "border-blue-400",
        node.status === 'selected' ? "bg-blue-50/80" : "",
        dragOver && isExpanded && "ring-2 ring-amber-400 border-amber-400"
      )}>

        {/* 概览行 */}
        <div onClick={handleExpand} className={cn(
          "flex items-center gap-2 px-3 py-2 cursor-pointer select-none transition-colors",
          isExpanded ? "border-b border-gray-100" : ""
        )}>
          <div className="w-7 h-7 rounded-lg bg-blue-500 flex items-center justify-center flex-shrink-0">
            <Brain className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-gray-800 truncate leading-tight">{node.question}</p>
            <p className="text-[10px] text-gray-500 truncate">
              {node.status === 'selected'
                ? `已选择: ${node.options.find(o => o.id === node.selectedOption)?.label || '自定义'}`
                : '待选择'}
            </p>
          </div>
          {/* 关联工具小方块预览（折叠时显示） */}
          {!isExpanded && hasAssociatedTools && (
            <div className="flex items-center gap-0.5">
              {(node.associatedTools || []).slice(0, 3).map(tid => {
                const t = findToolById(tid);
                return t ? (
                  <div key={tid} className="w-3.5 h-3.5 rounded-sm flex-shrink-0" style={{ backgroundColor: t.color }} title={t.name} />
                ) : null;
              })}
              {(node.associatedTools || []).length > 3 && (
                <span className="text-[8px] text-amber-500">+</span>
              )}
            </div>
          )}
          {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" /> : <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />}
        </div>

        {/* 展开内容 */}
        {isExpanded && (
          <div className="bg-gray-50">
            {/* 按钮行 + 工具方块 */}
            <div className="px-3 py-2 bg-gray-100/80 border-b border-gray-200 space-y-2">
              {/* 重新思考按钮 */}
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-gray-500">思考节点 #{nodeId.split('_').pop()}</span>
                {phase === 'thinking' && node.status === 'pending' && (
                  <button onClick={(e) => e.stopPropagation()} className="flex items-center gap-1 px-2 py-1 bg-red-500 hover:bg-red-400 text-white rounded text-[10px] font-medium transition-colors">
                    <RotateCcw className="w-3 h-3" />重新思考
                  </button>
                )}
              </div>

              {/* 关联工具方块行 */}
              <div className={cn("flex items-center gap-1.5 min-h-[28px] rounded-lg px-2 py-1 transition-colors", dragOver ? "bg-amber-100/50 border border-dashed border-amber-400" : "border border-dashed border-gray-300")}>
                <span className="text-[9px] text-gray-400 mr-1">工具:</span>
                {(node.associatedTools || []).length > 0 ? (
                  <>
                    {(node.associatedTools || []).map(tid => (
                      <ToolBadgeMini key={tid} toolId={tid} onRemove={() => handleRemoveTool(tid)} />
                    ))}
                    {/* Save按钮 */}
                    <button onClick={() => setIsSaved(true)} className={cn("ml-auto px-1.5 py-0.5 rounded text-[9px] transition-colors", isSaved ? "bg-green-500 text-white" : "bg-amber-500 text-white hover:bg-amber-400")}>
                      {isSaved ? '✓' : <Save className="w-2.5 h-2.5" />}
                    </button>
                  </>
                ) : (
                  <span className="text-[9px] text-gray-400">拖拽添加</span>
                )}
              </div>
            </div>

            {/* 选项列表 */}
            <div className="p-3 space-y-1.5">
              {node.options.map((option) => (
                <button key={option.id} onClick={() => handleOptionClick(option.id)} disabled={node.status !== 'pending' || phase !== 'thinking'}
                  className={cn("w-full text-left px-3 py-2 rounded-lg border transition-all",
                    node.selectedOption === option.id ? "border-blue-500 bg-blue-50 shadow-sm" : "border-gray-200 bg-white hover:border-blue-300",
                    node.status !== 'pending' && "cursor-default")}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={cn("w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0", node.selectedOption === option.id ? "bg-blue-500 text-white" : "bg-gray-100 text-gray-600")}>{option.id}</span>
                      <span className="text-sm text-gray-700">{option.label}</span>
                      {option.isDefault && <Sparkles className="w-3.5 h-3.5 text-amber-500" />}
                    </div>
                    {node.selectedOption === option.id && <ArrowRight className="w-4 h-4 text-blue-500" />}
                  </div>
                  <p className="text-xs text-gray-500 mt-1 ml-7">{option.description}</p>
                </button>
              ))}

              {/* 自定义输入 */}
              {!showCustomInput ? (
                <button onClick={() => setShowCustomInput(true)} disabled={node.status !== 'pending' || phase !== 'thinking'}
                  className="w-full px-3 py-2 border border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-gray-400 disabled:opacity-50">其他... 自定义输入</button>
              ) : (
                <div className="space-y-2">
                  <input type="text" value={customInput} onChange={(e) => setCustomInput(e.target.value)} placeholder="请输入您的自定义选项..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:border-blue-500" autoFocus />
                  <div className="flex gap-2">
                    <button onClick={handleCustomSubmit} className="flex-1 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium">确认</button>
                    <button onClick={() => { setShowCustomInput(false); setCustomInput(''); }} className="flex-1 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg text-sm font-medium">取消</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} id="bottom" style={{ background: '#3B82F6', width: 10, height: 10, bottom: -5 }} />
    </div>
  );
});

ThinkingNodeComponent.displayName = 'ThinkingNodeComponent';
export { ThinkingNodeComponent };
