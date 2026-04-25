import { useState } from 'react';
import {
  Brain, Workflow, Clock, CheckCircle2, Circle,
  AlertCircle, Zap, Target, FileText, BarChart3,
  ChevronRight, Layers, Cpu, Globe, Code2
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface TaskInfo {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress: number;
  type: 'thinking' | 'execution' | 'web' | 'ide';
  timestamp: string;
}

const DEFAULT_TASKS: TaskInfo[] = [
  {
    id: '1',
    title: '任务理解与目标分析',
    description: '解析用户需求，确定任务目标和范围',
    status: 'completed',
    progress: 100,
    type: 'thinking',
    timestamp: '2025-06-13 21:00:15',
  },
  {
    id: '2',
    title: '思考蓝图构建',
    description: '通过多轮选择构建完整的思考路径',
    status: 'completed',
    progress: 100,
    type: 'thinking',
    timestamp: '2025-06-13 21:05:32',
  },
  {
    id: '3',
    title: '执行蓝图生成',
    description: '将思考路径转换为可执行的任务序列',
    status: 'running',
    progress: 65,
    type: 'execution',
    timestamp: '2025-06-13 21:08:10',
  },
  {
    id: '4',
    title: 'Web搜索 - 技术方案调研',
    description: '搜索最佳实践和参考实现',
    status: 'running',
    progress: 40,
    type: 'web',
    timestamp: '2025-06-13 21:10:05',
  },
  {
    id: '5',
    title: '代码生成 - 前端组件开发',
    description: '编写React组件和样式代码',
    status: 'pending',
    progress: 0,
    type: 'ide',
    timestamp: '--',
  },
];

export function AdapterDefault() {
  const [tasks] = useState<TaskInfo[]>(DEFAULT_TASKS);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);

  const completedCount = tasks.filter(t => t.status === 'completed').length;
  const runningCount = tasks.filter(t => t.status === 'running').length;
  const pendingCount = tasks.filter(t => t.status === 'pending').length;
  const totalProgress = Math.round(tasks.reduce((sum, t) => sum + t.progress, 0) / tasks.length);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-400" />;
      case 'running':
        return <Zap className="w-4 h-4 text-yellow-400 animate-pulse" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      default:
        return <Circle className="w-4 h-4 text-slate-500" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return '已完成';
      case 'running':
        return '执行中';
      case 'error':
        return '出错';
      default:
        return '待执行';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-400 bg-green-400/10';
      case 'running':
        return 'text-yellow-400 bg-yellow-400/10';
      case 'error':
        return 'text-red-400 bg-red-400/10';
      default:
        return 'text-slate-400 bg-slate-400/10';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'thinking':
        return <Brain className="w-3.5 h-3.5" />;
      case 'execution':
        return <Workflow className="w-3.5 h-3.5" />;
      case 'web':
        return <Globe className="w-3.5 h-3.5" />;
      case 'ide':
        return <Code2 className="w-3.5 h-3.5" />;
      default:
        return <Layers className="w-3.5 h-3.5" />;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'thinking':
        return '思考';
      case 'execution':
        return '执行';
      case 'web':
        return 'Web';
      case 'ide':
        return 'IDE';
      default:
        return '其他';
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-slate-900 overflow-auto">
      {/* 顶部概览卡片 */}
      <div className="grid grid-cols-4 gap-3 p-4">
        <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700/50">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-slate-400">总进度</span>
          </div>
          <div className="text-2xl font-bold text-white">{totalProgress}%</div>
          <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full transition-all duration-500"
              style={{ width: `${totalProgress}%` }}
            />
          </div>
        </div>

        <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700/50">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4 text-green-400" />
            <span className="text-xs text-slate-400">已完成</span>
          </div>
          <div className="text-2xl font-bold text-green-400">{completedCount}</div>
          <span className="text-xs text-slate-500">个任务</span>
        </div>

        <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700/50">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-yellow-400" />
            <span className="text-xs text-slate-400">执行中</span>
          </div>
          <div className="text-2xl font-bold text-yellow-400">{runningCount}</div>
          <span className="text-xs text-slate-500">个任务</span>
        </div>

        <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700/50">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-slate-400" />
            <span className="text-xs text-slate-400">待执行</span>
          </div>
          <div className="text-2xl font-bold text-slate-400">{pendingCount}</div>
          <span className="text-xs text-slate-500">个任务</span>
        </div>
      </div>

      {/* 任务列表 */}
      <div className="flex-1 px-4 pb-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-white">执行蓝图进度</span>
          </div>
          <span className="text-xs text-slate-500">共 {tasks.length} 个任务</span>
        </div>

        <div className="space-y-2">
          {tasks.map((task) => (
            <div
              key={task.id}
              className="bg-slate-800/60 rounded-lg border border-slate-700/50 overflow-hidden"
            >
              <button
                onClick={() => setExpandedTask(expandedTask === task.id ? null : task.id)}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-700/30 transition-colors"
              >
                {getStatusIcon(task.status)}
                <div className="flex-1 text-left">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">{task.title}</span>
                    <span className={cn("text-[10px] px-1.5 py-0.5 rounded", getStatusColor(task.status))}>
                      {getStatusText(task.status)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">{task.description}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1 text-xs text-slate-500">
                    {getTypeIcon(task.type)}
                    <span>{getTypeLabel(task.type)}</span>
                  </div>
                  <div className="w-16">
                    <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all duration-500",
                          task.status === 'completed' && "bg-green-400",
                          task.status === 'running' && "bg-yellow-400",
                          task.status === 'pending' && "bg-slate-600",
                        )}
                        style={{ width: `${task.progress}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-slate-500">{task.progress}%</span>
                  </div>
                  <ChevronRight
                    className={cn(
                      "w-4 h-4 text-slate-500 transition-transform",
                      expandedTask === task.id && "rotate-90"
                    )}
                  />
                </div>
              </button>

              {/* 展开详情 */}
              {expandedTask === task.id && (
                <div className="px-4 pb-3 border-t border-slate-700/50 pt-2">
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="flex items-center gap-2">
                      <Cpu className="w-3 h-3 text-slate-500" />
                      <span className="text-slate-400">任务ID:</span>
                      <span className="text-slate-300 font-mono">{task.id}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-3 h-3 text-slate-500" />
                      <span className="text-slate-400">时间戳:</span>
                      <span className="text-slate-300">{task.timestamp}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Layers className="w-3 h-3 text-slate-500" />
                      <span className="text-slate-400">类型:</span>
                      <span className="text-slate-300">{getTypeLabel(task.type)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <FileText className="w-3 h-3 text-slate-500" />
                      <span className="text-slate-400">状态:</span>
                      <span className={cn(
                        task.status === 'completed' && "text-green-400",
                        task.status === 'running' && "text-yellow-400",
                        task.status === 'pending' && "text-slate-400",
                      )}>
                        {getStatusText(task.status)}
                      </span>
                    </div>
                  </div>
                  {/* 模拟输出 */}
                  {task.status === 'running' && (
                    <div className="mt-2 p-2 bg-slate-900/80 rounded border border-slate-700/50 font-mono text-[11px] text-slate-400">
                      <span className="text-green-400">$</span> 正在执行任务 {task.id}...<br />
                      <span className="text-slate-500">&gt;</span> 处理中，请稍候...
                    </div>
                  )}
                  {task.status === 'completed' && (
                    <div className="mt-2 p-2 bg-green-900/20 rounded border border-green-700/30 font-mono text-[11px] text-green-400">
                      ✓ 任务完成 - 输出已保存
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 底部记忆摘要 */}
      <div className="px-4 pb-4">
        <div className="bg-slate-800/60 rounded-lg border border-slate-700/50 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-medium text-white">任务记忆摘要</span>
          </div>
          <div className="space-y-2 text-xs text-slate-400">
            <p>• 用户请求构建 Blueclaw AI 自执行画布演示网站</p>
            <p>• 已完成思考蓝图构建，确定双区域布局（思考+执行）</p>
            <p>• 当前正在构建执行蓝图的多标签页系统</p>
            <p>• 包含画布、Web浏览器、IDE三个核心功能模块</p>
          </div>
        </div>
      </div>
    </div>
  );
}
