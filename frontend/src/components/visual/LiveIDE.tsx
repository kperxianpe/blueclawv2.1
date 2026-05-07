// LiveIDE.tsx — IDE 模式组件骨架
import { useState } from 'react';
import { FileCode, Play, Save } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface IDEFile {
  id: string;
  name: string;
  language: string;
  content: string;
}

export function LiveIDE({ files }: { files: IDEFile[] }) {
  const [activeFile, setActiveFile] = useState<string>(files[0]?.id || '');
  const [fileContents, setFileContents] = useState<Record<string, string>>(
    Object.fromEntries(files.map(f => [f.id, f.content]))
  );

  const currentFile = files.find(f => f.id === activeFile);

  return (
    <div className="absolute inset-2 z-50 flex flex-col">
      <div className="flex-1 bg-slate-900 rounded-lg overflow-hidden border border-white/20 shadow-2xl flex flex-col">
        {/* IDE 标题栏 */}
        <div className="flex items-center gap-2 px-3 py-2 bg-slate-800 border-b border-white/10 flex-shrink-0">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-400" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-400" />
          </div>
          <FileCode className="w-4 h-4 text-blue-400 ml-2" />
          <span className="text-[11px] text-white/70 truncate flex-1 text-center">
            Adapter IDE — 代码编辑器
          </span>
          <button className="flex items-center gap-1 px-2 py-1 bg-blue-600/80 rounded text-[10px] text-white hover:bg-blue-500 transition-colors">
            <Play className="w-3 h-3" />
            运行
          </button>
          <button className="flex items-center gap-1 px-2 py-1 bg-slate-700 rounded text-[10px] text-white/70 hover:bg-slate-600 transition-colors">
            <Save className="w-3 h-3" />
            保存
          </button>
        </div>

        {/* 文件标签栏 */}
        <div className="flex items-center gap-1 px-2 py-1 bg-slate-800/80 border-b border-white/10 overflow-x-auto">
          {files.map(file => (
            <button
              key={file.id}
              onClick={() => setActiveFile(file.id)}
              className={cn(
                "flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-all flex-shrink-0",
                activeFile === file.id
                  ? "bg-white/15 text-white"
                  : "bg-white/5 text-white/50 hover:bg-white/10"
              )}
            >
              <FileCode className="w-3 h-3" />
              <span>{file.name}</span>
              <span className="text-white/30">.{file.language}</span>
            </button>
          ))}
          {files.length === 0 && (
            <span className="text-[10px] text-white/30 italic">无文件</span>
          )}
        </div>

        {/* 代码编辑区域 */}
        <div className="flex-1 overflow-auto p-4 font-mono text-sm">
          {currentFile ? (
            <textarea
              value={fileContents[currentFile.id] || ''}
              onChange={(e) => setFileContents(prev => ({ ...prev, [currentFile.id]: e.target.value }))}
              className="w-full h-full bg-transparent text-white/80 resize-none focus:outline-none leading-relaxed"
              spellCheck={false}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-white/30">
              <p className="text-sm">选择文件以开始编辑</p>
            </div>
          )}
        </div>

        {/* 底部状态栏 */}
        <div className="px-2 py-1 bg-slate-800/90 border-t border-white/10 flex items-center gap-4 flex-shrink-0">
          <span className="text-[10px] text-white/40">
            {currentFile ? `${currentFile.language.toUpperCase()} | ${fileContents[currentFile.id]?.length || 0} 字符` : '无活动文件'}
          </span>
          <span className="text-[10px] text-white/40 ml-auto">
            UTF-8 | 4 空格缩进
          </span>
        </div>
      </div>
    </div>
  );
}
