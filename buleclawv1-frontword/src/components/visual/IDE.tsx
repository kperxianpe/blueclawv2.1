import { useState } from 'react';
import {
  FileText, Folder, FolderOpen, Play, Square, Settings,
  Search, GitBranch, Puzzle, PanelLeft, PanelRight,
  ChevronRight, ChevronDown, X, Terminal,
  Code2, Bug, MoreHorizontal
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileItem {
  id: string;
  name: string;
  type: 'file' | 'folder';
  language?: string;
  content?: string;
  isOpen?: boolean;
  children?: FileItem[];
}

const DEFAULT_FILES: FileItem[] = [
  {
    id: 'src',
    name: 'src',
    type: 'folder',
    isOpen: true,
    children: [
      {
        id: 'components',
        name: 'components',
        type: 'folder',
        isOpen: true,
        children: [
          { id: 'app.tsx', name: 'App.tsx', type: 'file', language: 'tsx', content: 'import { useState } from "react";\n\nexport function App() {\n  const [count, setCount] = useState(0);\n\n  return (\n    <div className="p-4">\n      <h1>Hello World</h1>\n      <button onClick={() => setCount(c => c + 1)}>\n        Count: {count}\n      </button>\n    </div>\n  );\n}' },
          { id: 'header.tsx', name: 'Header.tsx', type: 'file', language: 'tsx', content: 'export function Header() {\n  return <header>Header</header>;\n}' },
        ]
      },
      { id: 'main.tsx', name: 'main.tsx', type: 'file', language: 'tsx', content: 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport { App } from "./components/App";\n\nReactDOM.createRoot(document.getElementById("root")!).render(\n  <React.StrictMode>\n    <App />\n  </React.StrictMode>\n);' },
      { id: 'styles.css', name: 'styles.css', type: 'file', language: 'css', content: '* {\n  margin: 0;\n  padding: 0;\n  box-sizing: border-box;\n}\n\nbody {\n  font-family: -apple-system, sans-serif;\n  background: #1e1e1e;\n  color: #d4d4d4;\n}' },
    ]
  },
  { id: 'package.json', name: 'package.json', type: 'file', language: 'json', content: '{\n  "name": "my-project",\n  "version": "1.0.0",\n  "dependencies": {\n    "react": "^18.2.0",\n    "react-dom": "^18.2.0"\n  }\n}' },
  { id: 'tsconfig.json', name: 'tsconfig.json', type: 'file', language: 'json', content: '{\n  "compilerOptions": {\n    "target": "ES2020",\n    "module": "ESNext",\n    "jsx": "react-jsx",\n    "strict": true\n  }\n}' },
];

const LANGUAGE_COLORS: Record<string, string> = {
  tsx: '#3178c6',
  ts: '#3178c6',
  js: '#f7df1e',
  jsx: '#61dafb',
  css: '#264de4',
  json: '#8bc34a',
  py: '#3776ab',
  html: '#e34c26',
};

export function IDE() {
  const [files, setFiles] = useState<FileItem[]>(DEFAULT_FILES);
  const [openTabs, setOpenTabs] = useState<string[]>(['app.tsx']);
  const [activeTab, setActiveTab] = useState('app.tsx');
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [terminalVisible, setTerminalVisible] = useState(true);
  const [terminalOutput, setTerminalOutput] = useState<string[]>([
    '$ npm run dev',
    '> my-project@1.0.0 dev',
    '> vite',
    '',
    '  VITE v5.0.0  ready in 320ms',
    '',
    '  ➜  Local:   http://localhost:5173/',
    '  ➜  Network: http://192.168.1.100:5173/',
    '  ➜  press h + enter to show help',
  ]);
  const [isRunning, setIsRunning] = useState(true);

  const findFile = (items: FileItem[], id: string): FileItem | null => {
    for (const item of items) {
      if (item.id === id) return item;
      if (item.children) {
        const found = findFile(item.children, id);
        if (found) return found;
      }
    }
    return null;
  };

  const toggleFolder = (items: FileItem[], id: string): FileItem[] => {
    return items.map(item => {
      if (item.id === id && item.type === 'folder') {
        return { ...item, isOpen: !item.isOpen };
      }
      if (item.children) {
        return { ...item, children: toggleFolder(item.children, id) };
      }
      return item;
    });
  };

  const openFile = (fileId: string) => {
    if (!openTabs.includes(fileId)) {
      setOpenTabs(prev => [...prev, fileId]);
    }
    setActiveTab(fileId);
  };

  const closeTab = (fileId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const newTabs = openTabs.filter(t => t !== fileId);
    setOpenTabs(newTabs);
    if (activeTab === fileId && newTabs.length > 0) {
      setActiveTab(newTabs[newTabs.length - 1]);
    }
  };

  const runCode = () => {
    setTerminalOutput(prev => [
      ...prev,
      '',
      '$ npm run build',
      '> my-project@1.0.0 build',
      '> tsc && vite build',
      '',
      'building for production...',
      '✓ 42 modules transformed.',
      '✓ built in 2.45s',
    ]);
    setIsRunning(true);
  };

  const stopCode = () => {
    setTerminalOutput(prev => [...prev, '', '^C', '进程已终止']);
    setIsRunning(false);
  };

  const activeFile = findFile(files, activeTab);

  const renderFileTree = (items: FileItem[], depth = 0) => {
    return items.map(item => (
      <div key={item.id}>
        <button
          onClick={() => {
            if (item.type === 'folder') {
              setFiles(prev => toggleFolder(prev, item.id));
            } else {
              openFile(item.id);
            }
          }}
          className={cn(
            "w-full flex items-center gap-1 px-2 py-1 text-xs hover:bg-slate-700/50 transition-colors",
            activeTab === item.id && "bg-slate-700/80 text-white",
            activeTab !== item.id && "text-slate-400"
          )}
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          {item.type === 'folder' ? (
            item.isOpen ? (
              <ChevronDown className="w-3 h-3 flex-shrink-0" />
            ) : (
              <ChevronRight className="w-3 h-3 flex-shrink-0" />
            )
          ) : (
            <span className="w-3 flex-shrink-0" />
          )}
          {item.type === 'folder' ? (
            item.isOpen ? (
              <FolderOpen className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
            ) : (
              <Folder className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
            )
          ) : (
            <FileText
              className="w-3.5 h-3.5 flex-shrink-0"
              style={{ color: LANGUAGE_COLORS[item.language || ''] || '#9ca3af' }}
            />
          )}
          <span className="truncate">{item.name}</span>
        </button>
        {item.type === 'folder' && item.isOpen && item.children && (
          <div>{renderFileTree(item.children, depth + 1)}</div>
        )}
      </div>
    ));
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#1e1e1e]">
      {/* 顶部工具栏 */}
      <div className="flex items-center gap-1 px-2 py-1 bg-[#252526] border-b border-[#333]">
        <button
          onClick={() => setSidebarVisible(!sidebarVisible)}
          className={cn(
            "w-7 h-7 rounded flex items-center justify-center transition-colors",
            sidebarVisible ? "bg-[#37373d] text-white" : "hover:bg-[#37373d] text-slate-400"
          )}
        >
          <PanelLeft className="w-4 h-4" />
        </button>
        <div className="w-px h-4 bg-[#333] mx-1" />
        <button
          onClick={runCode}
          className="w-7 h-7 rounded hover:bg-[#37373d] flex items-center justify-center text-green-400 transition-colors"
          title="运行"
        >
          <Play className="w-4 h-4" />
        </button>
        <button
          onClick={stopCode}
          className={cn(
            "w-7 h-7 rounded flex items-center justify-center transition-colors",
            isRunning ? "hover:bg-[#37373d] text-red-400" : "text-slate-600 cursor-not-allowed"
          )}
          title="停止"
        >
          <Square className="w-3.5 h-3.5" />
        </button>
        <button className="w-7 h-7 rounded hover:bg-[#37373d] flex items-center justify-center text-slate-400 transition-colors" title="调试">
          <Bug className="w-4 h-4" />
        </button>
        <div className="w-px h-4 bg-[#333] mx-1" />
        <button className="w-7 h-7 rounded hover:bg-[#37373d] flex items-center justify-center text-slate-400 transition-colors" title="搜索">
          <Search className="w-4 h-4" />
        </button>
        <button className="w-7 h-7 rounded hover:bg-[#37373d] flex items-center justify-center text-slate-400 transition-colors" title="Git">
          <GitBranch className="w-4 h-4" />
        </button>
        <button className="w-7 h-7 rounded hover:bg-[#37373d] flex items-center justify-center text-slate-400 transition-colors" title="插件">
          <Puzzle className="w-4 h-4" />
        </button>
        <div className="flex-1" />
        <button
          onClick={() => setTerminalVisible(!terminalVisible)}
          className={cn(
            "w-7 h-7 rounded flex items-center justify-center transition-colors",
            terminalVisible ? "bg-[#37373d] text-white" : "hover:bg-[#37373d] text-slate-400"
          )}
        >
          <PanelRight className="w-4 h-4" />
        </button>
        <button className="w-7 h-7 rounded hover:bg-[#37373d] flex items-center justify-center text-slate-400 transition-colors">
          <Settings className="w-4 h-4" />
        </button>
      </div>

      {/* 主体区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧文件树 */}
        {sidebarVisible && (
          <div className="w-[200px] flex flex-col bg-[#252526] border-r border-[#333]">
            {/* 文件树标题 */}
            <div className="flex items-center justify-between px-3 py-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Explorer</span>
              <button className="w-5 h-5 rounded hover:bg-[#37373d] flex items-center justify-center text-slate-400">
                <MoreHorizontal className="w-3 h-3" />
              </button>
            </div>
            {/* 文件列表 */}
            <div className="flex-1 overflow-auto">
              {renderFileTree(files)}
            </div>
          </div>
        )}

        {/* 编辑器区域 */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* 标签栏 */}
          <div className="flex bg-[#252526] border-b border-[#333] overflow-x-auto">
            {openTabs.map(tabId => {
              const file = findFile(files, tabId);
              if (!file) return null;
              return (
                <button
                  key={tabId}
                  onClick={() => setActiveTab(tabId)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-2 text-xs min-w-[100px] max-w-[150px] transition-colors",
                    activeTab === tabId
                      ? "bg-[#1e1e1e] text-white border-t-2 border-t-blue-500"
                      : "bg-[#2d2d2d] text-slate-400 hover:bg-[#37373d]"
                  )}
                >
                  <FileText
                    className="w-3.5 h-3.5 flex-shrink-0"
                    style={{ color: LANGUAGE_COLORS[file.language || ''] || '#9ca3af' }}
                  />
                  <span className="truncate flex-1">{file.name}</span>
                  <X
                    className="w-3 h-3 hover:text-white flex-shrink-0 opacity-60 hover:opacity-100"
                    onClick={(e) => closeTab(tabId, e)}
                  />
                </button>
              );
            })}
          </div>

          {/* 代码编辑区 */}
          <div className="flex-1 flex overflow-hidden">
            {/* 行号 */}
            <div className="w-[40px] bg-[#1e1e1e] border-r border-[#333] text-right pr-2 pt-2 select-none overflow-hidden">
              {activeFile?.content?.split('\n').map((_, i) => (
                <div key={i} className="text-[11px] text-[#858585] leading-5">
                  {i + 1}
                </div>
              ))}
            </div>
            {/* 代码内容 */}
            <div className="flex-1 overflow-auto pt-2 pl-2">
              <pre className="text-[13px] text-[#d4d4d4] leading-5 font-mono">
                <code>{activeFile?.content || '选择文件以查看内容'}</code>
              </pre>
            </div>
          </div>

          {/* 底部终端 */}
          {terminalVisible && (
            <div className="h-[150px] flex flex-col bg-[#1e1e1e] border-t border-[#333]">
              {/* 终端标签 */}
              <div className="flex items-center gap-2 px-3 py-1 bg-[#252526]">
                <Terminal className="w-3 h-3 text-slate-400" />
                <span className="text-xs text-slate-300">Terminal</span>
                <span className="text-xs text-slate-500">bash</span>
                <div className="flex-1" />
                <button
                  onClick={() => setTerminalVisible(false)}
                  className="w-5 h-5 rounded hover:bg-[#37373d] flex items-center justify-center text-slate-400"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
              {/* 终端输出 */}
              <div className="flex-1 overflow-auto p-2">
                {terminalOutput.map((line, i) => (
                  <div key={i} className="text-xs font-mono leading-4">
                    {line.startsWith('$') || line.startsWith('>') ? (
                      <span className="text-green-400">{line}</span>
                    ) : line.startsWith('✓') ? (
                      <span className="text-green-400">{line}</span>
                    ) : line.startsWith('➜') ? (
                      <span className="text-cyan-400">{line}</span>
                    ) : (
                      <span className="text-slate-300">{line}</span>
                    )}
                  </div>
                ))}
                <div className="text-xs font-mono text-green-400 mt-1">$ <span className="animate-pulse">_</span></div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 底部状态栏 */}
      <div className="flex items-center justify-between px-3 py-0.5 bg-[#007acc] text-white text-[11px]">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Code2 className="w-3 h-3" />
            {activeFile?.language?.toUpperCase() || 'TEXT'}
          </span>
          <span>UTF-8</span>
        </div>
        <div className="flex items-center gap-3">
          <span>Prettier</span>
          <span>Ln 1, Col 1</span>
          <span>Spaces: 2</span>
        </div>
      </div>
    </div>
  );
}
