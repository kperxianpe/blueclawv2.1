import { useState, useCallback, useEffect, useRef } from 'react';
import {
  Snowflake, Sparkles, ImagePlus, MessageSquare,
  Unlock, Brain, X
} from 'lucide-react';
import { cn } from '@/lib/utils';

/** 截图框类型 */
export type ScreenshotBoxType = 'explain' | 'modify';

/** 截图框数据 */
export interface ScreenshotBox {
  id: string;
  type: ScreenshotBoxType;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

/** 小思考蓝图节点 */
export interface MiniThinkingNode {
  id: string;
  boxId: string;
  question: string;
  x: number;
  y: number;
  status: 'pending' | 'selected';
  selectedOption?: string;
  options: { id: string; label: string; description: string }[];
}

interface FreezeOverlayProps {
  isFrozen: boolean;
  onUnfreeze: () => void;
  adapterLabel?: string;
  onChangeDescription?: (desc: string) => void;
}

export function FreezeOverlay({
  isFrozen,
  onUnfreeze,
  adapterLabel = '当前页面',
  onChangeDescription,
}: FreezeOverlayProps) {
  const [boxes, setBoxes] = useState<ScreenshotBox[]>([]);
  const [miniNodes, setMiniNodes] = useState<MiniThinkingNode[]>([]);
  const [draggingNode, setDraggingNode] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [hoveredBtn, setHoveredBtn] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 添加截图框
  const addBox = useCallback((type: ScreenshotBoxType) => {
    const newBox: ScreenshotBox = {
      id: `box-${Date.now()}`,
      type,
      label: type === 'explain' ? '解释截图' : '更改截图',
      x: 100 + boxes.length * 40,
      y: 80 + boxes.length * 40,
      width: 150,
      height: 90,
    };
    setBoxes(prev => [...prev, newBox]);

    const options = type === 'explain'
      ? [
          { id: 'A', label: '解释整体', description: '对截图内容进行整体说明' },
          { id: 'B', label: '解释元素', description: '逐一解释截图中的关键元素' },
          { id: 'C', label: '解释问题', description: '指出截图中可能存在的问题' },
          { id: 'D', label: '自定义', description: '输入自定义解释需求' },
        ]
      : [
          { id: 'A', label: '修改样式', description: '调整颜色、大小、间距等样式' },
          { id: 'B', label: '修改布局', description: '调整组件位置和排列方式' },
          { id: 'C', label: '修改内容', description: '更改文本、图标等内容' },
          { id: 'D', label: '自定义', description: '输入自定义修改需求' },
        ];

    const newNode: MiniThinkingNode = {
      id: `mini-${Date.now()}`,
      boxId: newBox.id,
      question: type === 'explain' ? '如何解释这张截图？' : '如何更改这张截图？',
      x: newBox.x + newBox.width + 50,
      y: newBox.y,
      status: 'pending',
      options,
    };
    setMiniNodes(prev => [...prev, newNode]);
  }, [boxes.length]);

  const deleteBox = useCallback((boxId: string) => {
    setBoxes(prev => prev.filter(b => b.id !== boxId));
    setMiniNodes(prev => prev.filter(n => n.boxId !== boxId));
  }, []);

  const deleteMiniNode = useCallback((nodeId: string) => {
    setMiniNodes(prev => prev.filter(n => n.id !== nodeId));
  }, []);

  const selectMiniOption = useCallback((nodeId: string, optionId: string) => {
    setMiniNodes(prev => prev.map(n =>
      n.id === nodeId ? { ...n, status: 'selected' as const, selectedOption: optionId } : n
    ));
  }, []);

  const handleUnfreeze = useCallback(() => {
    onUnfreeze();
    setBoxes([]);
    setMiniNodes([]);
  }, [onUnfreeze]);

  // 小思考蓝图拖动
  const handleNodeMouseDown = useCallback((e: React.MouseEvent, nodeId: string) => {
    e.preventDefault();
    e.stopPropagation();
    const node = miniNodes.find(n => n.id === nodeId);
    if (!node) return;
    setDraggingNode(nodeId);
    setDragOffset({ x: e.clientX - node.x, y: e.clientY - node.y });
  }, [miniNodes]);

  useEffect(() => {
    if (!draggingNode) return;
    const handleMove = (e: MouseEvent) => {
      setMiniNodes(prev => prev.map(n =>
        n.id === draggingNode
          ? { ...n, x: Math.max(0, e.clientX - dragOffset.x), y: Math.max(0, e.clientY - dragOffset.y) }
          : n
      ));
    };
    const handleUp = () => setDraggingNode(null);
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    return () => { window.removeEventListener('mousemove', handleMove); window.removeEventListener('mouseup', handleUp); };
  }, [draggingNode, dragOffset]);

  // 更改蓝图形容
  const handleChangeDescription = useCallback(() => {
    const desc = prompt('输入新的蓝图形容描述:', adapterLabel);
    if (desc && onChangeDescription) onChangeDescription(desc);
  }, [adapterLabel, onChangeDescription]);

  if (!isFrozen) return null;

  // 底部按钮配置
  const bottomButtons = [
    { id: 'changeDesc', icon: MessageSquare, label: '更改蓝图形容', color: 'bg-indigo-500 hover:bg-indigo-400', onClick: handleChangeDescription },
    { id: 'explain', icon: Sparkles, label: '向我解释截图', color: 'bg-pink-500 hover:bg-pink-400', onClick: () => addBox('explain') },
    { id: 'modify', icon: ImagePlus, label: '更改截图', color: 'bg-amber-500 hover:bg-amber-400', onClick: () => addBox('modify') },
    { id: 'unfreeze', icon: Unlock, label: '解除冻结', color: 'bg-emerald-500 hover:bg-emerald-400', onClick: handleUnfreeze },
  ];

  return (
    <div ref={containerRef} className="absolute inset-0 z-[80] pointer-events-none">
      {/* 冻结半透明遮罩 - 极低模糊 */}
      <div className="absolute inset-0 bg-slate-900/10" />

      {/* ===== 截图框 ===== */}
      {boxes.map((box) => {
        const isExplain = box.type === 'explain';
        return (
          <div
            key={box.id}
            className={cn(
              "absolute pointer-events-auto rounded-xl border-2 backdrop-blur-sm shadow-lg transition-all",
              isExplain
                ? 'border-pink-400 bg-pink-500/10 shadow-pink-500/10'
                : 'border-amber-400 bg-amber-500/10 shadow-amber-500/10'
            )}
            style={{ left: box.x, top: box.y, width: box.width, height: box.height }}
          >
            <div className={cn(
              "flex items-center justify-between px-2 py-1 rounded-t-xl",
              isExplain ? 'bg-pink-500/25' : 'bg-amber-500/25'
            )}>
              <div className="flex items-center gap-1">
                {isExplain ? <Sparkles className="w-3 h-3 text-pink-400" /> : <ImagePlus className="w-3 h-3 text-amber-400" />}
                <span className={cn("text-[10px] font-medium", isExplain ? 'text-pink-300' : 'text-amber-300')}>
                  {box.label}
                </span>
              </div>
              <button onClick={() => deleteBox(box.id)} className="w-4 h-4 rounded hover:bg-white/20 flex items-center justify-center">
                <X className="w-2.5 h-2.5 text-white/60" />
              </button>
            </div>
            <div className="p-2 text-center">
              <p className={cn("text-[10px]", isExplain ? 'text-pink-300' : 'text-amber-300')}>
                {isExplain ? '选择解释方式' : '选择更改方式'}
              </p>
            </div>
          </div>
        );
      })}

      {/* ===== 小思考蓝图节点 ===== */}
      {miniNodes.map((node) => {
        const box = boxes.find(b => b.id === node.boxId);
        const isExplain = box?.type === 'explain';
        const accentBg = isExplain ? 'bg-pink-600' : 'bg-amber-600';
        const accentBorder = isExplain ? 'border-pink-500' : 'border-amber-500';
        const accentText = isExplain ? 'text-pink-300' : 'text-amber-300';
        const accentLight = isExplain ? 'text-pink-200' : 'text-amber-200';
        const optionBorder = isExplain ? 'hover:border-pink-400' : 'hover:border-amber-400';
        const optionBg = isExplain ? 'hover:bg-pink-500/20' : 'hover:bg-amber-500/20';
        const optionNum = isExplain ? 'text-pink-400' : 'text-amber-400';

        return (
          <div
            key={node.id}
            className={cn(
              "absolute pointer-events-auto w-[190px] rounded-xl border-2 bg-slate-900/95 shadow-xl backdrop-blur-sm",
              accentBorder,
              draggingNode === node.id ? 'cursor-grabbing opacity-90 scale-105' : 'cursor-grab'
            )}
            style={{ left: node.x, top: node.y }}
            onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
          >
            <div className={cn("px-3 py-2 rounded-t-xl flex items-center justify-between", accentBg)}>
              <div className="flex items-center gap-1.5">
                <Brain className="w-3.5 h-3.5 text-white" />
                <span className="text-[10px] font-medium text-white">思考蓝图</span>
              </div>
              <button onClick={(e) => { e.stopPropagation(); deleteMiniNode(node.id); }}
                className="w-4 h-4 rounded hover:bg-white/20 flex items-center justify-center">
                <X className="w-2.5 h-2.5 text-white/60" />
              </button>
            </div>
            <div className="px-3 py-2 border-b border-slate-700">
              <p className={cn("text-xs font-medium", accentLight)}>{node.question}</p>
            </div>
            <div className="p-2 space-y-1">
              {node.status === 'pending' ? (
                node.options.map((opt) => (
                  <button key={opt.id} onClick={(e) => { e.stopPropagation(); selectMiniOption(node.id, opt.id); }}
                    className={cn("w-full text-left px-2 py-1.5 rounded-lg border border-slate-700 transition-all", optionBorder, optionBg)}>
                    <div className="flex items-center gap-1">
                      <span className={cn("text-[10px] font-bold", optionNum)}>{opt.id}.</span>
                      <span className="text-[11px] text-white">{opt.label}</span>
                    </div>
                    <p className={cn("text-[9px] ml-3", accentText)}>{opt.description}</p>
                  </button>
                ))
              ) : (
                <div className="py-2 text-center">
                  <p className={cn("text-xs", accentText)}>
                    已选择: {node.options.find(o => o.id === node.selectedOption)?.label || '自定义'}
                  </p>
                  <button onClick={(e) => { e.stopPropagation();
                      setMiniNodes(prev => prev.map(n => n.id === node.id ? { ...n, status: 'pending' as const, selectedOption: undefined } : n));
                    }} className={cn("mt-1 text-[10px] underline", accentText, "hover:text-white")}>
                    重新选择
                  </button>
                </div>
              )}
            </div>
          </div>
        );
      })}

      {/* ===== SVG连线 ===== */}
      {miniNodes.length > 0 && (
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-[85]">
          {miniNodes.map((node) => {
            const box = boxes.find(b => b.id === node.boxId);
            if (!box) return null;
            const isExplain = box.type === 'explain';
            const strokeColor = isExplain ? '#ec4899' : '#f59e0b';
            const startX = box.x + box.width;
            const startY = box.y + box.height / 2;
            const endX = node.x;
            const endY = node.y + 55;
            const c1x = startX + (endX - startX) * 0.5;
            const c1y = startY;
            const c2x = startX + (endX - startX) * 0.5;
            const c2y = endY;
            return (
              <g key={`line-${node.id}`}>
                <path d={`M ${startX} ${startY} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${endX} ${endY}`}
                  fill="none" stroke={strokeColor} strokeWidth="1.5" strokeDasharray="6 3" opacity="0.7" />
                <polygon points={`${endX},${endY} ${endX - 6},${endY - 3} ${endX - 6},${endY + 3}`}
                  fill={strokeColor} opacity="0.7" />
              </g>
            );
          })}
        </svg>
      )}

      {/* ===== 底部状态栏 - 四个按钮直接显示 ===== */}
      <div className="absolute bottom-0 left-0 right-0 z-[90] pointer-events-auto">
        <div className="flex items-center justify-center gap-2 py-1.5 bg-slate-900/80 border-t border-cyan-500/30 backdrop-blur-sm">
          {/* 冻结指示器 */}
          <div className="flex items-center gap-1 px-2 py-0.5 bg-cyan-500/20 rounded text-cyan-300 text-[10px] mr-1">
            <Snowflake className="w-3 h-3 animate-pulse" />
            <span>已冻结</span>
          </div>

          <div className="w-px h-3 bg-slate-600 mx-1" />

          {/* 四个功能按钮 */}
          {bottomButtons.map((btn) => (
            <div key={btn.id} className="relative">
              {/* Tooltip */}
              {hoveredBtn === btn.id && (
                <div className={cn(
                  "absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium whitespace-nowrap z-[80]",
                  "bg-slate-700 text-white border border-slate-600 shadow-lg"
                )}>
                  {btn.label}
                  <div className="absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-700 border-b border-r border-slate-600 rotate-45 -mt-1" />
                </div>
              )}
              <button
                onMouseEnter={() => setHoveredBtn(btn.id)}
                onMouseLeave={() => setHoveredBtn(null)}
                onClick={btn.onClick}
                className={cn(
                  "flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-medium text-white transition-all",
                  "border border-white/20 shadow-md hover:scale-105 active:scale-95",
                  btn.color
                )}
              >
                <btn.icon className="w-3 h-3" />
                <span>{btn.label}</span>
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
