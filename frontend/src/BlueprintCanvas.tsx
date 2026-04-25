import { useCallback, useEffect, useState, useRef } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge,
  ConnectionMode,
  type NodeTypes,
  type ReactFlowInstance,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useBlueprintStore } from '@/store/useBlueprintStore';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { ThinkingNodeComponent } from './nodes/ThinkingNode';
import { ExecutionNodeComponent } from './nodes/ExecutionNode';
import { SummaryNodeComponent } from './nodes/SummaryNode';
import { InterventionPanel } from './panels/InterventionPanel';
import { SettingsPanel } from './panels/SettingsPanel';
import { FreezeOverlay } from './panels/FreezeOverlay';
import { InputScreen } from './InputScreen';
import { ToolDock, DEFAULT_TOOLS } from './visual/ToolDock';
import { ToolEditor } from './visual/ToolEditor';
import { VisualAdapter } from './visual/VisualAdapter';
import type { ThinkingNodeType, ExecutionStep } from '@/types';
import type { ToolItem } from './visual/ToolDock';
import { Brain, Cpu, X, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

// Register custom node types
const nodeTypes: NodeTypes = {
  thinking: ThinkingNodeComponent as unknown as NodeTypes['thinking'],
  execution: ExecutionNodeComponent as unknown as NodeTypes['execution'],
  summary: SummaryNodeComponent as unknown as NodeTypes['summary'],
};

export function BlueprintCanvas() {
  const store = useBlueprintStore();
  const thinkingFlowRef = useRef<ReactFlowInstance | null>(null);
  const execFlowRef = useRef<ReactFlowInstance | null>(null);
  const {
    phase,
    thinkingNodes,
    executionSteps,
    showInterventionPanel,
    interventionStepId,
    canvasConfig,
    currentTaskId,
    isRealtimeMode,
    isGeneratingBlueprint,
    showConfirmExecution,
    setUserInput,
    startThinking,
    selectThinkingNode,
    selectExecutionStep,
    hideIntervention,
    handleIntervention,
    completeThinking,
    setIsGeneratingBlueprint,
    setShowConfirmExecution,
    freeze,
    clearFreeze,
  } = store;

  const [thinkingNodesState, setThinkingNodes, onThinkingNodesChange] = useNodesState<Node>([]);
  const [thinkingEdges, setThinkingEdges, onThinkingEdgesChange] = useEdgesState<Edge>([]);
  
  const [execNodes, setExecNodes, onExecNodesChange] = useNodesState<Node>([]);
  const [execEdges, setExecEdges, onExecEdgesChange] = useEdgesState<Edge>([]);
  
  // 设置窗口显示状态
  const [showSettings, setShowSettings] = useState(false);
  
  // 工具状态
  const [tools, setTools] = useState<ToolItem[]>(DEFAULT_TOOLS);
  const [filteredTools, setFilteredTools] = useState<ToolItem[]>(DEFAULT_TOOLS);
  const [editingTool, setEditingTool] = useState<ToolItem | null>(null);
  const [showToolEditor, setShowToolEditor] = useState(false);
  
  // 视觉层拖放状态
  const [visualDroppedItems, setVisualDroppedItems] = useState<ToolItem[]>([]);

  // Generate thinking canvas nodes (左侧) - 直线连接
  useEffect(() => {
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    thinkingNodes.forEach((node: ThinkingNodeType, index: number) => {
      // 垂直排列，使用配置的节点间距
      newNodes.push({
        id: node.id,
        type: 'thinking',
        position: { x: 220, y: 60 + index * canvasConfig.thinkingNodeSpacing },
        data: { nodeId: node.id },
        style: { width: 220, height: 120 },
      });

      // 直线连接前一个节点
      if (index > 0) {
        const prevNode = thinkingNodes[index - 1];
        const isPrevSelected = prevNode.status === 'selected';
        newEdges.push({
          id: `e-${prevNode.id}-${node.id}`,
          source: prevNode.id,
          target: node.id,
          sourceHandle: 'bottom',
          targetHandle: 'top',
          animated: true,
          type: 'straight',
          style: { 
            stroke: isPrevSelected ? '#2563EB' : '#6B7280', 
            strokeWidth: isPrevSelected ? 6 : 5,
            zIndex: 10,
          },
          markerEnd: {
            type: 'arrowclosed',
            width: 20,
            height: 20,
            color: isPrevSelected ? '#2563EB' : '#6B7280',
          },
        });
      }
    });

    setThinkingNodes(newNodes);
    setThinkingEdges(newEdges);
  }, [thinkingNodes, setThinkingNodes, setThinkingEdges, canvasConfig.thinkingNodeSpacing]);

  // Generate execution canvas nodes (右侧) - 支持支路连线
  useEffect(() => {
    if (executionSteps.length === 0) return;
    
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    executionSteps.forEach((step: ExecutionStep) => {
      const nodeType = step.id === 'summary' ? 'summary' : 'execution';
      
      newNodes.push({
        id: step.id,
        type: nodeType,
        position: step.position,
        data: step.id === 'summary' ? {} : { stepId: step.id },
        style: { width: 180, height: 80 },
      });

      // 根据dependencies创建连线
      step.dependencies.forEach((depId) => {
        const depStep = executionSteps.find(s => s.id === depId);
        if (!depStep) return;
        
        const isCompleted = depStep.status === 'completed';
        const isRunning = step.status === 'running';
        const isFailed = depStep.status === 'failed';
        
        // 判断连线类型
        const isMainPathEdge = step.isMainPath && depStep.isMainPath;
        const isBranchToConvergence = step.isConvergence && !depStep.isMainPath;
        const isBranchFromMain = !step.isMainPath && depStep.isMainPath;
        
        // 判断连线方向
        const isVerticalLine = Math.abs(depStep.position.x - step.position.x) < 10;
        const isHorizontalLine = Math.abs(depStep.position.y - step.position.y) < 10;
        
        // 设置样式
        let strokeColor = '#6B7280';
        let strokeWidth = 4;
        let strokeDasharray = 'none';
        let animated = isRunning;
        let edgeType = 'step';
        let sourceHandle = 'bottom';
        let targetHandle = 'top';
        
        // 主路径水平连线：右→左
        if (isMainPathEdge && isHorizontalLine) {
          edgeType = 'straight';
          sourceHandle = 'right';
          targetHandle = 'left';
        }
        // 分支从主路径向下
        else if (isBranchFromMain) {
          edgeType = 'step';
          sourceHandle = 'bottom';
          targetHandle = 'top';
        }
        // 分支汇合到主路径：右→左
        else if (isBranchToConvergence) {
          edgeType = 'step';
          sourceHandle = 'right';
          targetHandle = 'left';
        }
        // 垂直连线
        else if (isVerticalLine) {
          edgeType = 'straight';
          sourceHandle = 'bottom';
          targetHandle = 'top';
        }
        
        if (isFailed) {
          strokeColor = '#DC2626';
        } else if (isCompleted || isRunning) {
          if (isMainPathEdge) {
            strokeColor = '#16A34A';
            strokeWidth = 5;
          } else {
            strokeColor = '#3B82F6';
            strokeWidth = 4;
            strokeDasharray = '5,3';
          }
        }
        
        newEdges.push({
          id: `e-${depId}-${step.id}`,
          source: depId,
          target: step.id,
          sourceHandle: sourceHandle,
          targetHandle: targetHandle,
          animated: animated,
          type: edgeType,
          style: { 
            stroke: strokeColor, 
            strokeWidth: strokeWidth,
            strokeDasharray: strokeDasharray,
            zIndex: 10,
          },
          markerEnd: {
            type: 'arrowclosed',
            width: 16,
            height: 16,
            color: strokeColor,
          },
        });
      });
    });

    setExecNodes(newNodes);
    setExecEdges(newEdges);
  }, [executionSteps, setExecNodes, setExecEdges]);

  const { isConnected, send } = useWebSocketContext();
  const [wsError, setWsError] = useState<string | null>(null);

  // Auto-fit view when nodes change (critical for E2E screenshots)
  useEffect(() => {
    if (thinkingFlowRef.current && thinkingNodesState.length > 0) {
      setTimeout(() => {
        thinkingFlowRef.current?.fitView({ padding: 0.3, duration: 300 });
      }, 100);
    }
  }, [thinkingNodesState]);

  useEffect(() => {
    if (execFlowRef.current && execNodes.length > 0) {
      setTimeout(() => {
        execFlowRef.current?.fitView({ padding: 0.2, duration: 300 });
      }, 100);
    }
  }, [execNodes]);

  // Expose fitView helpers for E2E tests
  useEffect(() => {
    if (typeof window !== 'undefined') {
      (window as any).__REACTFLOW_FITVIEW__ = () => {
        thinkingFlowRef.current?.fitView({ padding: 0.3, duration: 300 });
        execFlowRef.current?.fitView({ padding: 0.2, duration: 300 });
      };
    }
  }, []);

  // 发送 freeze_request
  const handleFreezeRequest = useCallback((stepId: string) => {
    if (isConnected && currentTaskId) {
      send('freeze_request', {
        task_id: currentTaskId,
        step_id: stepId,
        reason: '用户请求冻结并标注',
      });
    }
  }, [isConnected, send, currentTaskId]);

  // 处理确认执行
  const handleConfirmExecution = useCallback(() => {
    if (isConnected && currentTaskId) {
      send('thinking.confirm_execution', {
        task_id: currentTaskId
      });
      setIsGeneratingBlueprint(true);
    } else {
      setWsError('后端服务未连接，无法确认执行。请检查 WebSocket 服务 (ws://localhost:8006) 是否已启动。');
    }
    setShowConfirmExecution(false);
  }, [isConnected, send, currentTaskId, setIsGeneratingBlueprint, setShowConfirmExecution]);

  const handleInputSubmit = useCallback((input: string) => {
    setUserInput(input);
    setWsError(null);
    
    if (isConnected) {
      // 真实后端模式 - 发送消息
      const sent = send('task.start', { user_input: input });
      if (!sent) {
        setWsError('无法发送任务到后端，连接可能已断开。请检查 WebSocket 服务是否正常运行。');
      }
    } else {
      setWsError('后端服务未连接。请先启动 WebSocket 服务 (python backend/main.py)，然后刷新页面重试。');
    }
  }, [setUserInput, isConnected, send]);

  const handleExecAction = useCallback((action: 'continue' | 'newBranch' | 'stop', customInput?: string) => {
    const state = useBlueprintStore.getState();
    if (state.isRealtimeMode && state.currentTaskId && state.currentBlueprintId && state.interventionStepId) {
      if (action === 'newBranch') {
        send('execution.intervene', {
          task_id: state.currentTaskId,
          blueprint_id: state.currentBlueprintId,
          step_id: state.interventionStepId,
          action: 'replan',
          custom_input: customInput || '',
        });
      }
    }
    handleIntervention(action);
  }, [handleIntervention, send]);

  // 处理工具搜索
  const handleToolSearch = useCallback((query: string) => {
    if (!query.trim()) {
      setFilteredTools(tools);
    } else {
      setFilteredTools(tools.filter(t => 
        t.name.toLowerCase().includes(query.toLowerCase()) ||
        t.description.toLowerCase().includes(query.toLowerCase())
      ));
    }
  }, [tools]);

  // 处理新建工具
  const handleAddTool = useCallback(() => {
    setEditingTool(null);
    setShowToolEditor(true);
  }, []);

  // 处理编辑工具
  const handleEditTool = useCallback((item: ToolItem) => {
    setEditingTool(item);
    setShowToolEditor(true);
  }, []);

  // 处理保存工具
  const handleSaveTool = useCallback((toolData: Omit<ToolItem, 'id'> & { id?: string }) => {
    if (editingTool) {
      // 编辑现有工具
      setTools(prev => prev.map(t => 
        t.id === editingTool.id ? { ...t, ...toolData } as ToolItem : t
      ));
    } else {
      // 新建工具
      const newTool: ToolItem = {
        id: `tool-${Date.now()}`,
        name: toolData.name || 'New Tool',
        description: toolData.description || '',
        type: toolData.type || 'skill',
        color: toolData.color || '#F59E0B',
        icon: toolData.icon || Cpu,
        content: toolData.content || ''
      };
      setTools(prev => [...prev, newTool]);
    }
    // 更新过滤后的工具列表
    setFilteredTools(prev => {
      if (editingTool) {
        return prev.map(t => t.id === editingTool.id ? { ...t, ...toolData } as ToolItem : t);
      }
      return [...prev, {
        id: `tool-${Date.now()}`,
        name: toolData.name || 'New Tool',
        description: toolData.description || '',
        type: toolData.type || 'skill',
        color: toolData.color || '#F59E0B',
        icon: toolData.icon || Cpu,
        content: toolData.content || ''
      }];
    });
  }, [editingTool]);

  // 处理工具拖放到视觉层
  const handleVisualDrop = useCallback((item: ToolItem) => {
    setVisualDroppedItems(prev => {
      if (prev.find(i => i.id === item.id)) return prev;
      return [...prev, item];
    });
  }, []);

  // 处理工具使用
  const handleToolUse = useCallback((item: ToolItem, target: 'thinking' | 'execution') => {
    // 工具使用逻辑
    console.log('Tool used:', item.name, 'for', target);
  }, []);

  if (phase === 'input') {
    return (
      <div className="h-screen w-screen bg-gradient-to-br from-gray-50 to-blue-50/30 flex flex-col items-center justify-center">
        {wsError && (
          <div className="mb-4 max-w-2xl mx-4 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
            <div className="font-semibold mb-1">连接异常</div>
            <div>{wsError}</div>
          </div>
        )}
        <InputScreen onSubmit={handleInputSubmit} />
      </div>
    );
  }

  // 从配置计算比例
  // 左右比例: 1 : leftRightRatio
  const totalRatio = 1 + canvasConfig.leftRightRatio;
  const leftRatio = (1 / totalRatio * 100);
  // 执行区域上下比例: 1 : execTopBottomRatio
  const execTopRatio = (1 / (1 + canvasConfig.execTopBottomRatio) * 100);
  const execBottomRatio = (canvasConfig.execTopBottomRatio / (1 + canvasConfig.execTopBottomRatio) * 100);

  // 根据背景样式设置背景class
  const getBackgroundClass = () => {
    switch (canvasConfig.canvasBackground) {
      case 'solid':
        return { backgroundColor: canvasConfig.backgroundColor };
      case 'grid':
        return {};
      case 'dots':
        return {};
      case 'gradient':
      default:
        return {};
    }
  };

  const backgroundClass = cn(
    'h-screen w-screen flex flex-col',
    canvasConfig.canvasBackground === 'gradient' && 'bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950',
    canvasConfig.canvasBackground === 'solid' && '',
    canvasConfig.canvasBackground === 'grid' && 'bg-slate-900',
    canvasConfig.canvasBackground === 'dots' && 'bg-slate-900'
  );

  return (
    <div className={backgroundClass} style={getBackgroundClass()}>
      {/* 主画布区域 - 填充整个屏幕 */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* 左侧 - 思考蓝图 */}
        <div className="flex flex-col bg-blue-900/20 relative" style={{ flex: `0 0 ${leftRatio}%` }}>
          {/* Header */}
          <div className="px-4 py-2 flex items-center gap-2 bg-blue-900/60 border-b border-blue-800/50">
            <div className="w-7 h-7 rounded-lg bg-blue-500 flex items-center justify-center">
              <Brain className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-semibold text-blue-100">思考蓝图</span>
            <span className="text-xs text-blue-400">|</span>
            <span className="text-xs text-blue-300">
              {phase === 'thinking' ? '引导思考方向' : '构筑完成'}
            </span>
          </div>

          {/* 确认执行按钮 */}
          {showConfirmExecution && (
            <div className="px-4 py-3 bg-green-500/20 border-b border-green-500/30">
              <button
                onClick={handleConfirmExecution}
                className="w-full py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
              >
                <Sparkles className="w-4 h-4" />
                思考完成，开始执行
              </button>
            </div>
          )}

          {/* 正在生成执行蓝图提示 */}
          {isGeneratingBlueprint && (
            <div className="px-4 py-3 bg-blue-500/20 border-b border-blue-500/30">
              <div className="flex items-center justify-center gap-2 text-blue-100">
                <div className="w-4 h-4 border-2 border-blue-300 border-t-white rounded-full animate-spin" />
                <span className="font-medium">正在生成执行蓝图...</span>
              </div>
              <div className="text-center text-xs text-blue-300 mt-1">
                AI 正在根据您的选择规划执行步骤
              </div>
            </div>
          )}

          {/* Thinking Canvas */}
          <div className="flex-1 min-h-0 relative">
            {thinkingNodesState.length === 0 && phase === 'thinking' && (
              <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-blue-950/40">
                <div className="w-10 h-10 border-4 border-blue-400 border-t-white rounded-full animate-spin mb-3" />
                <p className="text-blue-200 font-medium">等待 AI 思考...</p>
                <p className="text-blue-400 text-xs mt-1">正在分析您的需求</p>
              </div>
            )}
            <ReactFlow
              nodes={thinkingNodesState}
              edges={thinkingEdges}
              onNodesChange={onThinkingNodesChange}
              onEdgesChange={onThinkingEdgesChange}
              nodeTypes={nodeTypes}
              connectionMode={ConnectionMode.Loose}
              fitView
              fitViewOptions={{ padding: 0.3 }}
              minZoom={0.3}
              maxZoom={2}
              className="w-full h-full"
              onNodeClick={(_, node) => selectThinkingNode(node.id)}
              onInit={(instance) => { thinkingFlowRef.current = instance; }}
              defaultEdgeOptions={{
                type: 'straight',
                markerEnd: { type: 'arrowclosed', width: 20, height: 20 },
                style: { strokeWidth: 5, zIndex: 10 },
              }}
              edgesFocusable={true}
            >
              {canvasConfig.canvasBackground === 'grid' && (
                <Background color="#1e3a5f" gap={40} size={2} />
              )}
              {canvasConfig.canvasBackground === 'dots' && (
                <Background color="#1e3a5f" gap={30} size={2} />
              )}
              {(canvasConfig.canvasBackground === 'gradient' || canvasConfig.canvasBackground === 'solid') && (
                <Background color="#3B82F6" gap={20} size={1} />
              )}
              <Controls className="bg-blue-900/60 border border-blue-800/50 shadow-sm" />
            </ReactFlow>
          </div>
        </div>

        {/* 中间分隔栏 - 工具Dock */}
        <ToolDock
          tools={filteredTools}
          onDragStart={(item) => handleVisualDrop(item)}
          onToolClick={handleEditTool}
          onAddTool={handleAddTool}
          onSearch={handleToolSearch}
          onSettings={() => setShowSettings(true)}
        />

        {/* 设置弹窗 */}
        {showSettings && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="w-[400px] max-h-[80vh] bg-slate-900 rounded-xl border border-slate-700 shadow-2xl overflow-hidden">
              {/* 弹窗标题栏 */}
              <div className="flex items-center justify-between px-4 py-3 bg-slate-800 border-b border-slate-700">
                <span className="font-medium text-slate-200">设置</span>
                <button
                  onClick={() => setShowSettings(false)}
                  className="w-8 h-8 rounded-lg hover:bg-slate-700 flex items-center justify-center transition-colors"
                >
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>
              
              {/* 设置内容 */}
              <div className="p-4 overflow-y-auto max-h-[calc(80vh-60px)]">
                <SettingsPanel />
              </div>
            </div>
          </div>
        )}

        {/* 工具编辑器弹窗 */}
        <ToolEditor
          item={editingTool}
          isOpen={showToolEditor}
          onClose={() => setShowToolEditor(false)}
          onSave={handleSaveTool}
        />

        {/* 右侧 - 执行区域 */}
        <div className="flex-1 flex flex-col bg-blue-900/20">
          {/* 执行区域上半部分 - 执行蓝图 */}
          <div className="flex flex-col" style={{ height: `${execTopRatio}%` }}>
            {/* Header */}
            <div className="px-4 py-2 flex items-center gap-2 bg-blue-900/60 border-b border-blue-800/50">
              <div className="w-7 h-7 rounded-lg bg-green-500 flex items-center justify-center">
                <Cpu className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="font-semibold text-blue-100">执行蓝图</span>
              <span className="text-xs text-blue-400">|</span>
              <span className="text-xs text-blue-300">
                {phase === 'completed' ? '执行完成' : '执行中...'}
              </span>
            </div>

            {/* Execution Canvas */}
            <div className="flex-1 min-h-0 relative">
              {execNodes.length === 0 && (phase === 'execution' || phase === 'completed') && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-blue-950/40">
                  {isGeneratingBlueprint ? (
                    <>
                      <div className="w-10 h-10 border-4 border-green-400 border-t-white rounded-full animate-spin mb-3" />
                      <p className="text-green-200 font-medium">生成执行计划中...</p>
                      <p className="text-green-400 text-xs mt-1">AI 正在根据思考结果规划执行步骤</p>
                    </>
                  ) : (
                    <>
                      <Cpu className="w-10 h-10 text-blue-400 mb-3" />
                      <p className="text-blue-200 font-medium">等待执行数据...</p>
                      <p className="text-blue-400 text-xs mt-1">执行蓝图加载中</p>
                    </>
                  )}
                </div>
              )}
              <ReactFlow
                nodes={execNodes}
                edges={execEdges}
                onNodesChange={onExecNodesChange}
                onEdgesChange={onExecEdgesChange}
                nodeTypes={nodeTypes}
                connectionMode={ConnectionMode.Loose}
                fitView
                fitViewOptions={{ padding: 0.2, includeHiddenNodes: false }}
                minZoom={0.15}
                maxZoom={2}
                className="w-full h-full"
                onNodeClick={(_, node) => selectExecutionStep(node.id)}
                onInit={(instance) => { execFlowRef.current = instance; }}
                defaultEdgeOptions={{
                  type: 'step',
                  markerEnd: { type: 'arrowclosed', width: 16, height: 16 },
                  style: { strokeWidth: 4, zIndex: 10 },
                }}
                edgesFocusable={true}
              >
                {canvasConfig.canvasBackground === 'grid' && (
                  <Background color="#1e3a5f" gap={40} size={2} />
                )}
                {canvasConfig.canvasBackground === 'dots' && (
                  <Background color="#1e3a5f" gap={30} size={2} />
                )}
                {(canvasConfig.canvasBackground === 'gradient' || canvasConfig.canvasBackground === 'solid') && (
                  <Background color="#3B82F6" gap={20} size={1} />
                )}
                <Controls className="bg-blue-900/60 border border-blue-800/50 shadow-sm" />
              </ReactFlow>
            </div>
          </div>
          
          {/* 执行区域下半部分 - 视觉区域 (Visual Adapter) */}
          <div 
            className="w-full flex flex-col"
            style={{ height: `${execBottomRatio}%` }}
          >
            {/* Visual Adapter */}
            <div className="flex-1 min-h-0">
              <VisualAdapter
                droppedItems={visualDroppedItems}
                onItemUse={handleToolUse}
                onEdit={handleEditTool}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Intervention Panel */}
      <InterventionPanel
        isOpen={showInterventionPanel}
        onClose={hideIntervention}
        stepName={executionSteps.find(s => s.id === interventionStepId)?.name || ''}
        stepStatus={executionSteps.find(s => s.id === interventionStepId)?.status as 'failed' | 'paused' | 'running' || 'failed'}
        onAction={handleExecAction}
      />

      {/* Freeze Overlay */}
      <FreezeOverlay
        isOpen={freeze.isFrozen}
        onClose={clearFreeze}
      />
    </div>
  );
}
