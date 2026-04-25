import { useState, useCallback, useEffect, memo, useRef } from 'react';
import { Handle, Position } from '@xyflow/react';
import { cn } from '@/lib/utils';
import {
  GripVertical, Link2, ChevronDown, ChevronRight,
  Image, FileText, Box, Plus, Save, Lock, X,
} from 'lucide-react';
import type { ToolItem } from './ToolDock';

// ============ 类型 ============

export interface ContentUnit {
  id: string;
  type: 'tool' | 'content' | 'nested';
  x: number;
  y: number;
  title?: string;
  text?: string;
  images?: string[];
  toolId?: string;
  toolColor?: string;
  toolName?: string;
  nestedBlueprintId?: string;
  nestedName?: string;
  nestedItem?: ToolItem; // 嵌套时保留完整工具数据
}

export interface ContentConnection {
  id: string;
  fromUnitId: string;
  toUnitId: string;
  label?: string;
}

export interface ContentBlueprint {
  title?: string;
  condition?: string;
  media?: { images: string[]; text: string };
  units?: ContentUnit[];
  connections?: ContentConnection[];
}

// ============ 常量 ============

const INNER_W = 500;
const INNER_H = 350;
const UNIT_W = 52;
const UNIT_H = 36;

// ============ 工具函数 ============

function genId() {
  return `u-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
}

function genConnId() {
  return `c-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
}

function ringLayout(units: ContentUnit[]): ContentUnit[] {
  if (units.length === 0) return [];
  const cx = INNER_W / 2;
  const cy = INNER_H / 2;
  const r = Math.min(INNER_W, INNER_H) * 0.32;
  return units.map((unit, i) => {
    const angle = (i / Math.max(units.length, 1)) * Math.PI * 2 - Math.PI / 2;
    return { ...unit, x: cx + r * Math.cos(angle) - UNIT_W / 2, y: cy + r * Math.sin(angle) - UNIT_H / 2 };
  });
}

function connPath(units: ContentUnit[], fromId: string, toId: string): string {
  const from = units.find((u) => u.id === fromId);
  const to = units.find((u) => u.id === toId);
  if (!from || !to) return '';
  const x1 = from.x + UNIT_W / 2;
  const y1 = from.y + UNIT_H / 2;
  const x2 = to.x + UNIT_W / 2;
  const y2 = to.y + UNIT_H / 2;
  const dx = x2 - x1;
  const off = Math.abs(dx) * 0.3 + Math.abs(y2 - y1) * 0.2;
  return `M ${x1} ${y1} C ${x1 + off} ${y1}, ${x2 - off} ${y2}, ${x2} ${y2}`;
}

function connMid(units: ContentUnit[], fromId: string, toId: string): { x: number; y: number } | null {
  const from = units.find((u) => u.id === fromId);
  const to = units.find((u) => u.id === toId);
  if (!from || !to) return null;
  return { x: (from.x + to.x) / 2 + UNIT_W / 2, y: (from.y + to.y) / 2 + UNIT_H / 2 };
}

// ============ 内部画布组件 ============

function InnerCanvas({
  units,
  connections,
  onUnitsChange,
  onConnectionsChange,
  parentColor,
  isReadOnly,
  selectedUnitId,
  onSelectUnit,
  onEditConnection,
  onEditUnit,
  onDropNested,
}: {
  units: ContentUnit[];
  connections: ContentConnection[];
  onUnitsChange: (u: ContentUnit[]) => void;
  onConnectionsChange: (c: ContentConnection[]) => void;
  parentColor: string;
  isReadOnly: boolean;
  selectedUnitId: string | null;
  onSelectUnit: (id: string | null) => void;
  onEditConnection: (conn: ContentConnection) => void;
  onEditUnit: (unit: ContentUnit) => void;
  onDropNested: (item: ToolItem, x: number, y: number) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  // ---- 单元点击交互（用 onClick，不用 onMouseDown） ----
  const handleUnitClick = useCallback(
    (unit: ContentUnit) => {
      if (isReadOnly) {
        onSelectUnit(unit.id === selectedUnitId ? null : unit.id);
        return;
      }
      if (selectedUnitId && selectedUnitId !== unit.id) {
        // A已选中，点击B → 创建连线
        const exists = connections.some(
          (c) =>
            (c.fromUnitId === selectedUnitId && c.toUnitId === unit.id) ||
            (c.fromUnitId === unit.id && c.toUnitId === selectedUnitId)
        );
        if (!exists) {
          onConnectionsChange([
            ...connections,
            { id: genConnId(), fromUnitId: selectedUnitId, toUnitId: unit.id },
          ]);
        }
        onSelectUnit(null);
      } else {
        onSelectUnit(unit.id === selectedUnitId ? null : unit.id);
      }
    },
    [isReadOnly, selectedUnitId, connections, onConnectionsChange, onSelectUnit]
  );

  // ---- 单元双击编辑 ----
  const handleUnitDblClick = useCallback(
    (unit: ContentUnit) => {
      if (isReadOnly) return;
      if (unit.type === 'content') onEditUnit(unit);
    },
    [isReadOnly, onEditUnit]
  );

  // ---- 连线双击标注 ----
  const handleConnDblClick = useCallback(
    (conn: ContentConnection) => {
      if (isReadOnly) return;
      onEditConnection(conn);
    },
    [isReadOnly, onEditConnection]
  );

  // ---- 空白处点击取消选中 ----
  const handleBgClick = useCallback(
    (e: React.MouseEvent) => {
      // 只有点击容器本身或svg背景时才取消
      const target = e.target as HTMLElement;
      if (target === e.currentTarget || target.tagName === 'svg' || target.tagName === 'path') {
        onSelectUnit(null);
      }
    },
    [onSelectUnit]
  );

  // ---- 内部拖放：接收嵌套蓝图 ----
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      let data: string | null = null;
      try { data = e.dataTransfer.getData('application/json'); } catch {}
      if (!data) try { data = e.dataTransfer.getData('text/plain'); } catch {}
      if (!data) return;
      try {
        const item: ToolItem = JSON.parse(data);
        if (!containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        const localX = e.clientX - rect.left;
        const localY = e.clientY - rect.top;
        onDropNested(item, localX - UNIT_W / 2, localY - UNIT_H / 2);
      } catch {}
    },
    [onDropNested]
  );

  // ---- Shift+拖拽移动单元 ----
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const dragOffsetRef = useRef({ x: 0, y: 0 });

  const handleUnitPointerDown = useCallback(
    (unit: ContentUnit, e: React.PointerEvent) => {
      if (isReadOnly) return;
      if (e.shiftKey) {
        e.preventDefault();
        setDraggingId(unit.id);
        dragOffsetRef.current = { x: e.clientX - unit.x, y: e.clientY - unit.y };
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
      }
    },
    [isReadOnly]
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!draggingId) return;
      const newX = Math.max(0, Math.min(INNER_W - UNIT_W, e.clientX - dragOffsetRef.current.x));
      const newY = Math.max(0, Math.min(INNER_H - UNIT_H, e.clientY - dragOffsetRef.current.y));
      onUnitsChange(units.map((u) => (u.id === draggingId ? { ...u, x: newX, y: newY } : u)));
    },
    [draggingId, units, onUnitsChange]
  );

  const handlePointerUp = useCallback(() => {
    setDraggingId(null);
  }, []);

  return (
    <div
      ref={containerRef}
      className="relative nodrag nopan nowheel"
      style={{ width: INNER_W, height: INNER_H, cursor: draggingId ? 'grabbing' : 'default' }}
      onClick={handleBgClick}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* 背景网格 */}
      <div
        className="absolute inset-0 rounded-lg opacity-15"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(251,191,36,0.35) 1px, transparent 1px)',
          backgroundSize: '14px 14px',
        }}
      />

      {/* SVG 连线层 — pointer-events:none 默认，只有透明点击路径接收事件 */}
      <svg className="absolute inset-0" width={INNER_W} height={INNER_H} style={{ zIndex: 5, pointerEvents: 'none' }}>
        {connections.map((conn) => {
          const path = connPath(units, conn.fromUnitId, conn.toUnitId);
          if (!path) return null;
          const mid = connMid(units, conn.fromUnitId, conn.toUnitId);
          const from = units.find((u) => u.id === conn.fromUnitId);
          const to = units.find((u) => u.id === conn.toUnitId);
          return (
            <g key={conn.id} style={{ pointerEvents: 'none' }}>
              {/* 可见连线 */}
              <path
                d={path}
                fill="none"
                stroke="#FBBF24"
                strokeWidth={3}
                strokeDasharray={conn.label ? undefined : '5 3'}
                opacity={0.9}
                style={{ filter: 'drop-shadow(0 0 2px rgba(251,191,36,0.6))' }}
              />
              {/* 连线端点圆点 */}
              {from && to && (
                <>
                  <circle cx={from.x + UNIT_W / 2} cy={from.y + UNIT_H / 2} r={4} fill="#FBBF24" opacity={0.9} />
                  <circle cx={to.x + UNIT_W / 2} cy={to.y + UNIT_H / 2} r={4} fill="#FBBF24" opacity={0.9} />
                </>
              )}
              {/* 标注文字 */}
              {conn.label && mid && (
                <>
                  <rect x={mid.x - 24} y={mid.y - 8} width={48} height={16} rx={5}
                    fill="rgba(15,23,42,0.95)" stroke="#FBBF24" strokeWidth={1} />
                  <text x={mid.x} y={mid.y + 4} textAnchor="middle" fill="#FBBF24" fontSize={8} fontWeight={500}
                    fontFamily="ui-sans-serif, system-ui, sans-serif">{conn.label}</text>
                </>
              )}
              {/* 透明宽路径 — 放在最上层用于点击/双击捕获 */}
              <path
                d={path}
                fill="none"
                stroke="transparent"
                strokeWidth={14}
                style={{ pointerEvents: 'stroke', cursor: 'pointer' }}
                onDoubleClick={(e) => {
                  e.stopPropagation();
                  handleConnDblClick(conn);
                }}
              />
            </g>
          );
        })}
      </svg>

      {/* 内容单元层 */}
      <div className="absolute inset-0" style={{ zIndex: 10 }}>
        {units.map((unit) => {
          const isSel = selectedUnitId === unit.id;
          const base = 'absolute rounded-lg flex flex-col items-center justify-center gap-0.5 transition-all select-none';
          const sel = isSel ? 'ring-2 ring-yellow-400 shadow-lg scale-110 z-20' : 'hover:scale-105 z-10';

          if (unit.type === 'tool') {
            return (
              <div
                key={unit.id}
                className={cn(base, sel, 'border cursor-pointer')}
                style={{
                  left: unit.x, top: unit.y, width: UNIT_W, height: UNIT_H,
                  backgroundColor: `${unit.toolColor || parentColor}28`,
                  borderColor: isSel ? '#FBBF24' : `${unit.toolColor || parentColor}55`,
                }}
                onClick={() => handleUnitClick(unit)}
                title={unit.toolName || '工具'}
              >
                <div className="w-4 h-4 rounded flex items-center justify-center" style={{ backgroundColor: unit.toolColor || parentColor }}>
                  <Box className="w-2.5 h-2.5 text-slate-900" />
                </div>
                <span className="text-[7px] text-slate-300 truncate w-full text-center px-0.5 leading-tight">{unit.toolName || 'Tool'}</span>
              </div>
            );
          }

          if (unit.type === 'nested') {
            return (
              <div
                key={unit.id}
                className={cn(base, sel, 'border border-dashed cursor-pointer')}
                style={{
                  left: unit.x, top: unit.y, width: UNIT_W + 10, height: UNIT_H,
                  backgroundColor: 'rgba(251,191,36,0.15)',
                  borderColor: isSel ? '#FBBF24' : 'rgba(251,191,36,0.4)',
                }}
                onClick={() => handleUnitClick(unit)}
                title={unit.nestedName || '嵌套蓝图'}
              >
                <Link2 className="w-3 h-3 text-yellow-400" />
                <span className="text-[7px] text-yellow-300 truncate w-full text-center px-0.5 leading-tight">{unit.nestedName || 'Blueprint'}</span>
              </div>
            );
          }

          // content
          return (
            <div
              key={unit.id}
              className={cn(base, sel, 'border cursor-pointer p-1')}
              style={{
                left: unit.x, top: unit.y,
                width: UNIT_W + 22,
                height: UNIT_H + (unit.images && unit.images.length > 0 ? 18 : 0),
                backgroundColor: isSel ? 'rgba(30,41,59,0.95)' : 'rgba(30,41,59,0.75)',
                borderColor: isSel ? '#FBBF24' : 'rgba(100,116,139,0.4)',
              }}
              onClick={() => handleUnitClick(unit)}
              onDoubleClick={() => handleUnitDblClick(unit)}
              onPointerDown={(e) => handleUnitPointerDown(unit, e)}
            >
              <div className="flex items-center gap-1 w-full">
                <FileText className="w-2.5 h-2.5 text-slate-400 flex-shrink-0" />
                <span className="text-[7px] text-slate-200 truncate font-medium leading-tight">{unit.title || '内容'}</span>
              </div>
              {unit.text && <p className="text-[6px] text-slate-400 leading-tight line-clamp-2 w-full mt-0.5">{unit.text}</p>}
              {unit.images && unit.images.length > 0 && (
                <div className="flex gap-0.5 mt-0.5">
                  {unit.images.slice(0, 2).map((img, i) => (
                    <div key={i} className="w-4 h-4 rounded bg-slate-700 flex items-center justify-center overflow-hidden">
                      {img ? <img src={img} alt="" className="w-full h-full object-cover" /> : <Image className="w-2 h-2 text-slate-500" />}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 空状态 */}
      {units.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center text-slate-600">
            <Box className="w-6 h-6 mx-auto mb-1 opacity-40" />
            <p className="text-[9px]">空内容蓝图</p>
            <p className="text-[7px] mt-0.5">点击 + 添加内容单元</p>
            <p className="text-[7px] mt-0.5 text-slate-500">或拖拽其他蓝图到此处嵌套</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ============ 主节点组件 ============

interface ContentBlueprintNodeProps {
  data: {
    item: ToolItem;
    onClick?: () => void;
    onSave?: (units: ContentUnit[], connections: ContentConnection[]) => void;
    isReadOnly?: boolean;
  };
  selected?: boolean;
}

const ContentBlueprintNodeComponent = memo(({ data, selected }: ContentBlueprintNodeProps) => {
  const { item, onClick, onSave, isReadOnly = false } = data;
  const blueprint = item.blueprint as ContentBlueprint | undefined;

  const [isExpanded, setIsExpanded] = useState(false);

  // 本地状态 — 从 blueprint 初始化
  const [units, setUnits] = useState<ContentUnit[]>(() => {
    const initial = blueprint?.units || [];
    return ringLayout(initial);
  });
  const [connections, setConnections] = useState<ContentConnection[]>(() => blueprint?.connections || []);
  const [selectedUnitId, setSelectedUnitId] = useState<string | null>(null);
  const [savedFlash, setSavedFlash] = useState(false);

  // 当外部 blueprint 变化时同步（Save 后或其他更新）
  useEffect(() => {
    const newUnits = blueprint?.units || [];
    const newConns = blueprint?.connections || [];
    // 只有当外部数据与本地不同时才同步，避免覆盖正在编辑的内容
    const unitsChanged = JSON.stringify(newUnits) !== JSON.stringify(units);
    const connsChanged = JSON.stringify(newConns) !== JSON.stringify(connections);
    if (unitsChanged) setUnits(ringLayout(newUnits));
    if (connsChanged) setConnections(newConns);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [blueprint?.units, blueprint?.connections]);

  // 连线标注编辑
  const [editingConnId, setEditingConnId] = useState<string | null>(null);
  const [connLabel, setConnLabel] = useState('');

  // 单元内容编辑
  const [editingUnit, setEditingUnit] = useState<ContentUnit | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editText, setEditText] = useState('');
  const [editImages, setEditImages] = useState<string[]>([]);
  const [imageInput, setImageInput] = useState('');

  const hasContent = units.length > 0 || !!(blueprint?.title || blueprint?.condition);

  const readOnlyLabel = item.type === 'mcp' ? 'mcp不可编辑' : item.type === 'skill' ? 'skill不可编辑' : '只读';

  // ---- 添加内容单元 ----
  const handleAddContent = useCallback(() => {
    if (isReadOnly) return;
    const cx = INNER_W / 2 - UNIT_W / 2;
    const cy = INNER_H / 2 - UNIT_H / 2;
    const off = units.length * 12;
    const newUnit: ContentUnit = {
      id: genId(), type: 'content', x: cx + off, y: cy + off,
      title: '新内容', text: '双击编辑', images: [],
    };
    setUnits(ringLayout([...units, newUnit]));
    setSelectedUnitId(newUnit.id);
  }, [isReadOnly, units]);

  // ---- 保存 ----
  const handleSave = useCallback(() => {
    onSave?.(units, connections);
    setSavedFlash(true);
    setTimeout(() => setSavedFlash(false), 1200);
  }, [onSave, units, connections]);

  // ---- 嵌套拖入 ----
  const handleDropNested = useCallback((droppedItem: ToolItem, x: number, y: number) => {
    if (isReadOnly) return;
    const boundedX = Math.max(0, Math.min(INNER_W - UNIT_W - 10, x));
    const boundedY = Math.max(0, Math.min(INNER_H - UNIT_H, y));
    const newUnit: ContentUnit = {
      id: genId(), type: 'nested',
      x: boundedX, y: boundedY,
      nestedBlueprintId: droppedItem.id,
      nestedName: droppedItem.name,
      nestedItem: droppedItem,
    };
    setUnits(ringLayout([...units, newUnit]));
  }, [isReadOnly, units]);

  // ---- 连线标注 ----
  const handleEditConnection = useCallback((conn: ContentConnection) => {
    setEditingConnId(conn.id);
    setConnLabel(conn.label || '');
  }, []);

  const saveConnLabel = () => {
    if (!editingConnId) return;
    setConnections(connections.map((c) =>
      c.id === editingConnId ? { ...c, label: connLabel.trim() || undefined } : c
    ));
    setEditingConnId(null);
  };

  // ---- 单元编辑 ----
  const handleEditUnit = useCallback((unit: ContentUnit) => {
    setEditingUnit(unit);
    setEditTitle(unit.title || '');
    setEditText(unit.text || '');
    setEditImages(unit.images || []);
    setImageInput('');
  }, []);

  const saveUnitEdit = () => {
    if (!editingUnit) return;
    setUnits(units.map((u) =>
      u.id === editingUnit.id
        ? { ...u, title: editTitle.trim() || u.title, text: editText.trim() || u.text, images: editImages.filter(Boolean) }
        : u
    ));
    setEditingUnit(null);
  };

  const addImage = () => {
    if (imageInput.trim()) { setEditImages([...editImages, imageInput.trim()]); setImageInput(''); }
  };

  const removeImage = (i: number) => setEditImages(editImages.filter((_, idx) => idx !== i));

  return (
    <div
      className={cn(
        'rounded-xl border-2 overflow-hidden transition-shadow',
        selected ? 'ring-2 ring-yellow-400 border-yellow-400 shadow-xl bg-yellow-950/90' : 'border-yellow-600/60 bg-yellow-950/80',
        'hover:border-yellow-500',
        isExpanded ? 'w-[540px]' : 'w-[190px]'
      )}
      style={{ transitionDuration: '200ms' }}
    >
      {/* Handle */}
      <Handle type="target" position={Position.Top} id="top" style={{ background: item.color, width: 8, height: 8, top: -4 }} />
      <Handle type="target" position={Position.Left} id="left" style={{ background: item.color, width: 8, height: 8, left: -4, top: '50%' }} />

      {/* 头部 — 拖拽手柄 */}
      <div className="px-2.5 py-1.5 flex items-center gap-2" style={{ backgroundColor: `${item.color}25` }}>
        <div
          className="w-5 h-5 rounded flex items-center justify-center flex-shrink-0 cursor-grab active:cursor-grabbing"
          style={{ backgroundColor: item.color }}
          onClick={(e) => { e.stopPropagation(); onClick?.(); }}
        >
          <GripVertical className="w-2.5 h-2.5 text-slate-900" />
        </div>
        <div className="flex-1 min-w-0 cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
          <span className="text-[11px] font-medium text-white truncate block">{item.name}</span>
          <div className="flex items-center gap-1">
            <span className="text-[8px] text-slate-400">内容蓝图</span>
            {isReadOnly && <span className="text-[7px] text-slate-500 flex items-center gap-0.5"><Lock className="w-2 h-2" />{readOnlyLabel}</span>}
          </div>
        </div>
        <div className="flex items-center gap-0.5">
          {isExpanded ? (
            <>
              <span className="text-[7px] text-slate-500">{units.length}·{connections.length}</span>
              <button className="p-0.5 rounded hover:bg-white/10" onClick={(e) => { e.stopPropagation(); setIsExpanded(false); setSelectedUnitId(null); }}>
                <ChevronDown className="w-3 h-3 text-slate-400" />
              </button>
            </>
          ) : (
            <button className="p-0.5 rounded hover:bg-white/10" onClick={(e) => { e.stopPropagation(); setIsExpanded(true); }}>
              <ChevronRight className="w-3 h-3 text-slate-400" />
            </button>
          )}
        </div>
      </div>

      {/* 折叠概要 */}
      {!isExpanded && hasContent && (
        <div className="px-2.5 py-1.5 space-y-1">
          {blueprint?.title && (
            <div className="flex items-start gap-1.5">
              <span className="text-[7px] text-yellow-500 uppercase w-7 flex-shrink-0">目标</span>
              <p className="text-[9px] text-yellow-100/70 leading-snug line-clamp-2">{blueprint.title}</p>
            </div>
          )}
          {blueprint?.condition && (
            <div className="flex items-start gap-1.5">
              <span className="text-[7px] text-yellow-600 uppercase w-7 flex-shrink-0">条件</span>
              <p className="text-[9px] text-yellow-200/40 leading-snug line-clamp-2">{blueprint.condition}</p>
            </div>
          )}
          {units.length > 0 && (
            <div className="flex flex-wrap gap-0.5 mt-0.5">
              {units.slice(0, 5).map((u) => (
                <div key={u.id} className="w-4 h-4 rounded flex items-center justify-center"
                  style={{
                    backgroundColor: u.type === 'tool' ? `${u.toolColor || item.color}35` : u.type === 'nested' ? 'rgba(251,191,36,0.15)' : 'rgba(148,163,184,0.15)',
                    border: `1px solid ${u.type === 'tool' ? (u.toolColor || item.color) : u.type === 'nested' ? 'rgba(251,191,36,0.3)' : 'rgba(148,163,184,0.2)'}`,
                  }}
                  title={u.toolName || u.title || u.nestedName || ''}>
                  {u.type === 'tool' && <Box className="w-2 h-2 text-slate-400" />}
                  {u.type === 'content' && <FileText className="w-2 h-2 text-slate-500" />}
                  {u.type === 'nested' && <Link2 className="w-2 h-2 text-yellow-500" />}
                </div>
              ))}
              {units.length > 5 && <div className="w-4 h-4 rounded bg-slate-700/40 flex items-center justify-center"><span className="text-[6px] text-slate-500">+</span></div>}
            </div>
          )}
        </div>
      )}

      {/* 展开：内部画布 */}
      {isExpanded && (
        <div className="px-2 py-2 border-t border-yellow-600/15">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[8px] text-yellow-500 uppercase tracking-wider">内容画布</span>
            <div className="flex items-center gap-1">
              {!isReadOnly && (
                <>
                  <button className="flex items-center gap-0.5 text-[8px] text-yellow-400 hover:text-yellow-300 px-1.5 py-0.5 rounded bg-yellow-500/10 hover:bg-yellow-500/20 transition-colors"
                    onClick={(e) => { e.stopPropagation(); handleAddContent(); }}>
                    <Plus className="w-2.5 h-2.5" />添加
                  </button>
                  <button className={cn('flex items-center gap-0.5 text-[8px] px-1.5 py-0.5 rounded transition-colors',
                    savedFlash ? 'text-green-400 bg-green-500/15' : 'text-slate-300 hover:text-white bg-slate-700/40 hover:bg-slate-600/40')}
                    onClick={(e) => { e.stopPropagation(); handleSave(); }}>
                    <Save className="w-2.5 h-2.5" />{savedFlash ? '已保存' : 'Save'}
                  </button>
                </>
              )}
              {isReadOnly && <span className="text-[8px] text-slate-500 flex items-center gap-0.5"><Lock className="w-2.5 h-2.5" />{readOnlyLabel}</span>}
            </div>
          </div>
          <div className="rounded-lg border border-yellow-600/15 bg-slate-900/40 overflow-hidden">
            <InnerCanvas
              units={units} connections={connections}
              onUnitsChange={setUnits} onConnectionsChange={setConnections}
              parentColor={item.color} isReadOnly={isReadOnly}
              selectedUnitId={selectedUnitId} onSelectUnit={setSelectedUnitId}
              onEditConnection={handleEditConnection} onEditUnit={handleEditUnit}
              onDropNested={handleDropNested}
            />
          </div>
          <div className="mt-1 flex items-center justify-between text-[7px] text-slate-600">
            {!isReadOnly ? (
              <span>单击单元选中再单击另一单元连线 · 双击连线标注 · 双击内容单元编辑 · Shift+拖拽移动 · 可拖拽其他蓝图进来嵌套</span>
            ) : (
              <span>{readOnlyLabel} · 可查看但不可编辑</span>
            )}
          </div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} id="bottom" style={{ background: item.color, width: 8, height: 8, bottom: -4 }} />
      <Handle type="source" position={Position.Right} id="right" style={{ background: item.color, width: 8, height: 8, right: -4, top: '50%' }} />

      {/* 连线标注编辑模态框 */}
      {editingConnId && !isReadOnly && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setEditingConnId(null)}>
          <div className="bg-slate-800 border border-yellow-500/40 rounded-lg shadow-2xl p-3 w-[240px]" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] text-white font-medium">编辑连线标注</span>
              <button onClick={() => setEditingConnId(null)} className="text-slate-400 hover:text-white"><X className="w-3 h-3" /></button>
            </div>
            <input type="text" value={connLabel} onChange={(e) => setConnLabel(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') saveConnLabel(); if (e.key === 'Escape') setEditingConnId(null); }}
              placeholder="输入逻辑关系..." autoFocus
              className="w-full mb-3 px-2 py-1.5 bg-slate-700/50 border border-slate-600 rounded text-[11px] text-yellow-200 placeholder:text-slate-500 outline-none focus:border-yellow-500" />
            <div className="flex justify-end gap-1.5">
              <button onClick={() => setEditingConnId(null)} className="text-[10px] text-slate-400 px-2 py-1 rounded hover:bg-slate-700">取消</button>
              <button onClick={saveConnLabel} className="text-[10px] text-yellow-400 px-2 py-1 rounded bg-yellow-500/10 hover:bg-yellow-500/20">确定</button>
            </div>
          </div>
        </div>
      )}

      {/* 单元编辑模态框（支持图文） */}
      {editingUnit && !isReadOnly && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setEditingUnit(null)}>
          <div className="bg-slate-800 border border-yellow-500/40 rounded-lg shadow-2xl p-3 w-[320px] max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] text-white font-medium">编辑内容单元</span>
              <button onClick={() => setEditingUnit(null)} className="text-slate-400 hover:text-white"><X className="w-3 h-3" /></button>
            </div>
            <label className="text-[9px] text-slate-400 mb-1 block">标题</label>
            <input type="text" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} placeholder="输入标题..."
              className="w-full mb-2 px-2 py-1 bg-slate-700/50 border border-slate-600 rounded text-[10px] text-white placeholder:text-slate-500 outline-none focus:border-yellow-500" />
            <label className="text-[9px] text-slate-400 mb-1 block">描述</label>
            <textarea value={editText} onChange={(e) => setEditText(e.target.value)} placeholder="输入描述文字..." rows={3}
              className="w-full mb-2 px-2 py-1 bg-slate-700/50 border border-slate-600 rounded text-[10px] text-white placeholder:text-slate-500 outline-none focus:border-yellow-500 resize-none" />
            <label className="text-[9px] text-slate-400 mb-1 block">图片</label>
            <div className="flex gap-1 mb-2">
              <input type="text" value={imageInput} onChange={(e) => setImageInput(e.target.value)} placeholder="粘贴图片URL..."
                className="flex-1 px-2 py-1 bg-slate-700/50 border border-slate-600 rounded text-[10px] text-white placeholder:text-slate-500 outline-none focus:border-yellow-500"
                onKeyDown={(e) => { if (e.key === 'Enter') addImage(); }} />
              <button onClick={addImage} className="text-[10px] text-yellow-400 px-2 py-1 rounded bg-yellow-500/10 hover:bg-yellow-500/20">添加</button>
            </div>
            {editImages.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {editImages.map((img, i) => (
                  <div key={i} className="relative group">
                    <div className="w-12 h-12 rounded bg-slate-700 flex items-center justify-center overflow-hidden border border-slate-600">
                      {img ? <img src={img} alt="" className="w-full h-full object-cover" /> : <Image className="w-4 h-4 text-slate-500" />}
                    </div>
                    <button onClick={() => removeImage(i)} className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-red-500/80 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-colors">
                      <X className="w-2 h-2" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="flex justify-end gap-1.5">
              <button onClick={() => setEditingUnit(null)} className="text-[10px] text-slate-400 px-2 py-1 rounded hover:bg-slate-700">取消</button>
              <button onClick={saveUnitEdit} className="text-[10px] text-yellow-400 px-2 py-1 rounded bg-yellow-500/10 hover:bg-yellow-500/20">确定</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

ContentBlueprintNodeComponent.displayName = 'ContentBlueprintNodeComponent';

export { ContentBlueprintNodeComponent };
