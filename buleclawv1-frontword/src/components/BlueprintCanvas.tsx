import { useCallback, useEffect, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  ConnectionMode,
  type NodeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useBlueprintStore } from '@/store/useBlueprintStore';
import { ThinkingNodeComponent } from './nodes/ThinkingNode';
import { ExecutionNodeComponent } from './nodes/ExecutionNode';
import { SummaryNodeComponent } from './nodes/SummaryNode';
import { InterventionPanel } from './panels/InterventionPanel';
import { SettingsPanel } from './panels/SettingsPanel';
import { InputScreen } from './InputScreen';
import { ToolDock, DEFAULT_TOOLS } from './visual/ToolDock';
import { ToolEditor } from './visual/ToolEditor';
import { VisualAdapter } from './visual/VisualAdapter';
import { FreezeOverlay } from './panels/FreezeOverlay';
import type { ThinkingNodeType, ExecutionStep } from '@/types';
import type { ToolItem } from './visual/ToolDock';
import { Brain, Cpu, X } from 'lucide-react';
import { cn } from '@/lib/utils';

// Register custom node types
const nodeTypes: NodeTypes = {
  thinking: ThinkingNodeComponent as unknown as NodeTypes['thinking'],
  execution: ExecutionNodeComponent as unknown as NodeTypes['execution'],
  summary: SummaryNodeComponent as unknown as NodeTypes['summary'],
};

export function BlueprintCanvas() {
  const {
    phase,
    thinkingNodes,
    executionSteps,
    showInterventionPanel,
    interventionStepId,
    canvasConfig,
    setUserInput,
    startThinking,
    selectThinkingNode,
    selectExecutionStep,
    hideIntervention,
    handleIntervention,
  } = useBlueprintStore();

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

  // 冻结状态
  const [isFrozen, setIsFrozen] = useState(false);
  const [frozenStepName, setFrozenStepName] = useState('');
  const [adapterLabel, setAdapterLabel] = useState('当前页面');

  // Generate thinking canvas nodes (左侧) - 直线连接
  useEffect(() => {
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    thinkingNodes.forEach((node: ThinkingNodeType, index: number) => {
      // 垂直排列，使用配置的节点间距
      newNodes.push({
        id: node.id,
        type: 'thinking',
        position: { x: 150, y: index * canvasConfig.thinkingNodeSpacing },
        data: { nodeId: node.id },
        style: { width: 220 },
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
        data: step.id === 'summary'
          ? {}
          : { stepId: step.id, onFreeze: handleFreeze },
        style: { width: 180 },
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

  const handleInputSubmit = useCallback((input: string) => {
    setUserInput(input);
    startThinking();
  }, [setUserInput, startThinking]);

  const handleExecAction = useCallback((action: 'continue' | 'newBranch' | 'stop') => {
    handleIntervention(action);
  }, [handleIntervention]);

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
        blueprint: toolData.blueprint || { title: '', condition: '', media: { images: [], text: '' } }
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
        blueprint: toolData.blueprint || { title: '', condition: '', media: { images: [], text: '' } }
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

  // 处理冻结
  const handleFreeze = useCallback((stepName: string) => {
    setFrozenStepName(stepName);
    setIsFrozen(true);
  }, []);

  // 解冻
  const handleUnfreeze = useCallback(() => {
    setIsFrozen(false);
    setFrozenStepName('');
  }, []);

  // 处理工具使用
  const handleToolUse = useCallback((item: ToolItem, target: 'thinking' | 'execution') => {
    // 工具使用逻辑
    console.log('Tool used:', item.name, 'for', target);
  }, []);

  if (phase === 'input') {
    return (
      <div className="h-screen w-screen bg-gradient-to-br from-gray-50 to-blue-50/30 flex items-center justify-center">
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

          {/* Thinking Canvas */}
          <div className="flex-1 min-h-0">
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
            <div className="flex-1 min-h-0">
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
            <div className="flex-1 min-h-0 relative">
              <VisualAdapter
                droppedItems={visualDroppedItems}
                onItemUse={handleToolUse}
                onEdit={handleEditTool}
                isFrozen={isFrozen}
              />
              {/* 冻结覆盖层 */}
              <FreezeOverlay
                isFrozen={isFrozen}
                onUnfreeze={handleUnfreeze}
                adapterLabel={frozenStepName || adapterLabel}
                onChangeDescription={setAdapterLabel}
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
        onAction={handleExecAction}
      />
    </div>
  );
}
