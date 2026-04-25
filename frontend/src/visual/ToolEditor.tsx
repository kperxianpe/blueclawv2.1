import { useState } from 'react';
import { X, Save, FileText, Sparkles, Cpu } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolItem } from './ToolDock';

interface ToolEditorProps {
  item?: ToolItem | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (item: Omit<ToolItem, 'id'> & { id?: string }) => void;
}

const COLORS = [
  '#F59E0B', '#FBBF24', '#FCD34D', '#FDE68A', '#FEF3C7',
  '#3B82F6', '#10B981', '#EF4444', '#8B5CF6', '#EC4899'
];

export function ToolEditor({ item, isOpen, onClose, onSave }: ToolEditorProps) {
  const [name, setName] = useState(item?.name || '');
  const [description, setDescription] = useState(item?.description || '');
  const [type, setType] = useState<'mcp' | 'skill' | 'file'>(
    item?.type === 'setting' ? 'file' : (item?.type || 'skill')
  );
  const [color, setColor] = useState(item?.color || COLORS[0]);
  const [content, setContent] = useState(item?.content || '');

  if (!isOpen) return null;

  const handleSave = () => {
    const icon = type === 'mcp' ? Cpu : type === 'skill' ? Sparkles : FileText;
    onSave({
      name,
      description,
      type,
      color,
      content,
      icon
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-[500px] max-h-[90vh] bg-slate-900 rounded-xl border border-slate-700 shadow-2xl overflow-hidden">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-4 py-3 bg-slate-800 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <div 
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: color }}
            >
              {type === 'mcp' && <Cpu className="w-4 h-4 text-slate-900" />}
              {type === 'skill' && <Sparkles className="w-4 h-4 text-slate-900" />}
              {type === 'file' && <FileText className="w-4 h-4 text-slate-900" />}
            </div>
            <span className="font-medium text-white">
              {item ? '编辑工具' : '新建工具'}
            </span>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-slate-700 flex items-center justify-center transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* 表单内容 */}
        <div className="p-4 space-y-4 overflow-y-auto max-h-[calc(90vh-120px)]">
          {/* 类型选择 */}
          <div>
            <label className="block text-xs text-slate-400 mb-2">类型</label>
            <div className="flex gap-2">
              {(['mcp', 'skill', 'file'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setType(t)}
                  className={cn(
                    "flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    type === t
                      ? "bg-blue-600 text-white"
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                  )}
                >
                  {t === 'mcp' && 'MCP'}
                  {t === 'skill' && 'Skill'}
                  {t === 'file' && 'File'}
                </button>
              ))}
            </div>
          </div>

          {/* 名称 */}
          <div>
            <label className="block text-xs text-slate-400 mb-2">名称</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="输入工具名称..."
              className="w-full px-3 py-2 bg-slate-800 text-white text-sm rounded-lg border border-slate-700 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* 描述 */}
          <div>
            <label className="block text-xs text-slate-400 mb-2">描述</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="输入工具描述..."
              className="w-full px-3 py-2 bg-slate-800 text-white text-sm rounded-lg border border-slate-700 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* 颜色 */}
          <div>
            <label className="block text-xs text-slate-400 mb-2">颜色</label>
            <div className="flex flex-wrap gap-2">
              {COLORS.map((c) => (
                <button
                  key={c}
                  onClick={() => setColor(c)}
                  className={cn(
                    "w-8 h-8 rounded-lg transition-all",
                    color === c ? "ring-2 ring-white scale-110" : "hover:scale-105"
                  )}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>

          {/* 内容/配置 */}
          <div>
            <label className="block text-xs text-slate-400 mb-2">
              {type === 'mcp' ? 'MCP 配置' : type === 'skill' ? 'Skill 代码' : '文件内容'}
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={
                type === 'mcp' 
                  ? "输入 MCP 配置 JSON..." 
                  : type === 'skill' 
                    ? "输入 Skill 实现代码..." 
                    : "输入文件内容..."
              }
              rows={8}
              className="w-full px-3 py-2 bg-slate-800 text-white text-sm rounded-lg border border-slate-700 focus:outline-none focus:border-blue-500 font-mono"
            />
          </div>
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-end gap-2 px-4 py-3 bg-slate-800 border-t border-slate-700">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm rounded-lg transition-colors"
          >
            <Save className="w-4 h-4" />
            保存
          </button>
        </div>
      </div>
    </div>
  );
}
