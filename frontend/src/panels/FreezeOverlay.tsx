/**
 * FreezeOverlay
 * 冻结覆盖层：展示截图 + 框选标注 + 提交标注
 */
import { useState, useRef, useCallback } from 'react';
import { X, Send, MousePointer, Square } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { useBlueprintStore } from '@/store/useBlueprintStore';
import type { AnnotationBox } from '@/types';

interface FreezeOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export function FreezeOverlay({ isOpen, onClose }: FreezeOverlayProps) {
  const { send } = useWebSocketContext();
  const freeze = useBlueprintStore(s => s.freeze);
  const currentTaskId = useBlueprintStore(s => s.currentTaskId);
  const clearFreeze = useBlueprintStore(s => s.clearFreeze);

  const [boxes, setBoxes] = useState<AnnotationBox[]>([]);
  const [annotationText, setAnnotationText] = useState('');
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [currentBox, setCurrentBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const [tool, setTool] = useState<'select' | 'rect'>('rect');
  const imageRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  if (!isOpen || !freeze.screenshot) return null;

  const getImageCoordinates = (e: React.MouseEvent | React.PointerEvent) => {
    const img = imageRef.current;
    if (!img) return null;
    const rect = img.getBoundingClientRect();
    const scaleX = img.naturalWidth / rect.width;
    const scaleY = img.naturalHeight / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    if (tool !== 'rect') return;
    e.preventDefault();
    const coords = getImageCoordinates(e);
    if (!coords) return;
    setIsDrawing(true);
    setDrawStart(coords);
    setCurrentBox({ x: coords.x, y: coords.y, w: 0, h: 0 });
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDrawing || !drawStart) return;
    e.preventDefault();
    const coords = getImageCoordinates(e);
    if (!coords) return;
    setCurrentBox({
      x: Math.min(drawStart.x, coords.x),
      y: Math.min(drawStart.y, coords.y),
      w: Math.abs(coords.x - drawStart.x),
      h: Math.abs(coords.y - drawStart.y),
    });
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (!isDrawing || !currentBox) return;
    e.preventDefault();
    setIsDrawing(false);
    setDrawStart(null);

    // 忽略太小的框
    if (currentBox.w > 10 && currentBox.h > 10) {
      const newBox: AnnotationBox = {
        id: `box_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
        x: Math.round(currentBox.x),
        y: Math.round(currentBox.y),
        w: Math.round(currentBox.w),
        h: Math.round(currentBox.h),
        label: '',
      };
      setBoxes(prev => [...prev, newBox]);
    }
    setCurrentBox(null);
  };

  const handleRemoveBox = (id: string) => {
    setBoxes(prev => prev.filter(b => b.id !== id));
  };

  const handleSubmit = useCallback(() => {
    if (!currentTaskId || !freeze.stepId) return;

    send('submit_annotation', {
      task_id: currentTaskId,
      step_id: freeze.stepId,
      annotation: annotationText,
      boxes: boxes.map(b => ({ x: b.x, y: b.y, w: b.w, h: b.h, label: b.label || '' })),
      freeze_token: freeze.freezeToken,
    });

    // 清理状态
    setBoxes([]);
    setAnnotationText('');
    clearFreeze();
    onClose();
  }, [send, currentTaskId, freeze, annotationText, boxes, clearFreeze, onClose]);

  const handleCancel = () => {
    setBoxes([]);
    setAnnotationText('');
    clearFreeze();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="relative flex flex-col bg-slate-900 rounded-xl shadow-2xl max-w-[90vw] max-h-[90vh] overflow-hidden"
           ref={containerRef}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-slate-800 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-white">步骤已冻结</span>
            <span className="text-xs text-slate-400">{freeze.stepId}</span>
          </div>
          <div className="flex items-center gap-2">
            {/* 工具切换 */}
            <button
              onClick={() => setTool('select')}
              className={cn(
                'p-1.5 rounded transition-colors',
                tool === 'select' ? 'bg-blue-500 text-white' : 'text-slate-400 hover:text-white'
              )}
              title="选择"
            >
              <MousePointer className="w-4 h-4" />
            </button>
            <button
              onClick={() => setTool('rect')}
              className={cn(
                'p-1.5 rounded transition-colors',
                tool === 'rect' ? 'bg-blue-500 text-white' : 'text-slate-400 hover:text-white'
              )}
              title="框选标注"
            >
              <Square className="w-4 h-4" />
            </button>
            <button
              onClick={handleCancel}
              className="p-1.5 rounded text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Screenshot + Annotation Canvas */}
        <div className="flex-1 overflow-auto p-4 flex justify-center">
          <div className="relative inline-block">
            <img
              ref={imageRef}
              src={`data:image/png;base64,${freeze.screenshot}`}
              alt="Screenshot"
              className={cn(
                'max-w-full max-h-[60vh] object-contain rounded border border-slate-700',
                tool === 'rect' && 'cursor-crosshair'
              )}
              draggable={false}
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerLeave={handlePointerUp}
            />
            {/* 已保存的标注框（CSS 叠加层，相对于显示尺寸） */}
            {imageRef.current && boxes.map(box => {
              const img = imageRef.current!;
              const rect = img.getBoundingClientRect();
              const scaleX = rect.width / img.naturalWidth;
              const scaleY = rect.height / img.naturalHeight;
              return (
                <div
                  key={box.id}
                  className="absolute border-2 border-red-500 bg-red-500/10 pointer-events-none"
                  style={{
                    left: box.x * scaleX,
                    top: box.y * scaleY,
                    width: box.w * scaleX,
                    height: box.h * scaleY,
                  }}
                >
                  <span className="absolute -top-5 left-0 text-[10px] text-red-400 bg-black/60 px-1 rounded whitespace-nowrap">
                    {box.label || `框 ${box.id.slice(-4)}`}
                  </span>
                </div>
              );
            })}
            {/* 正在画的框 */}
            {imageRef.current && currentBox && (
              <div
                className="absolute border-2 border-blue-400 bg-blue-400/10 pointer-events-none"
                style={{
                  left: currentBox.x * (imageRef.current.getBoundingClientRect().width / imageRef.current.naturalWidth),
                  top: currentBox.y * (imageRef.current.getBoundingClientRect().height / imageRef.current.naturalHeight),
                  width: currentBox.w * (imageRef.current.getBoundingClientRect().width / imageRef.current.naturalWidth),
                  height: currentBox.h * (imageRef.current.getBoundingClientRect().height / imageRef.current.naturalHeight),
                }}
              />
            )}
          </div>
        </div>

        {/* Annotation List */}
        {boxes.length > 0 && (
          <div className="px-4 py-2 bg-slate-800/50 border-t border-slate-700 max-h-[120px] overflow-auto">
            <div className="text-xs text-slate-400 mb-2">已标注框 ({boxes.length})：</div>
            <div className="flex flex-wrap gap-2">
              {boxes.map(box => (
                <div key={box.id} className="flex items-center gap-1 text-xs bg-slate-700 rounded px-2 py-1">
                  <span className="text-slate-300">框 {box.id.slice(-4)}</span>
                  <span className="text-slate-500">({box.x},{box.y}) {box.w}x{box.h}</span>
                  <button
                    onClick={() => handleRemoveBox(box.id)}
                    className="text-slate-500 hover:text-red-400 ml-1"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="px-4 py-3 bg-slate-800 border-t border-slate-700 flex items-center gap-3">
          <textarea
            value={annotationText}
            onChange={(e) => setAnnotationText(e.target.value)}
            placeholder="添加文本备注（可选）..."
            className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            rows={2}
          />
          <button
            onClick={handleSubmit}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Send className="w-4 h-4" />
            提交并继续
          </button>
        </div>
      </div>
    </div>
  );
}
