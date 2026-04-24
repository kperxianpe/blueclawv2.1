import { useState } from 'react';
import { Brain, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import { Handle, Position } from '@xyflow/react';
import { useBlueprintStore } from '@/store/useBlueprintStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { cn } from '@/lib/utils';

interface ThinkingNodeProps {
  data: { nodeId: string };
}

export function ThinkingNodeComponent({ data }: ThinkingNodeProps) {
  const { nodeId } = data;
  const node = useBlueprintStore(state => state.thinkingNodes.find(n => n.id === nodeId));
  const phase = useBlueprintStore(state => state.phase);
  const selectedNodeId = useBlueprintStore(state => state.selectedThinkingNodeId);
  const isRealtimeMode = useBlueprintStore(state => state.isRealtimeMode);
  const currentTaskId = useBlueprintStore(state => state.currentTaskId);
  const selectThinkingOption = useBlueprintStore(state => state.selectThinkingOption);
  const setCustomInput = useBlueprintStore(state => state.setCustomInput);
  const selectThinkingNode = useBlueprintStore(state => state.selectThinkingNode);
  
  const { isConnected, send } = useWebSocket();
  
  const [isExpanded, setIsExpanded] = useState(false);
  const [customInput, setCustomInputState] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  if (!node) return null;

  const isSelected = selectedNodeId === nodeId;
  const isPending = node.status === 'pending';
  const isDone = node.status === 'selected';

  const handleExpand = () => {
    setIsExpanded(!isExpanded);
    selectThinkingNode(nodeId);
  };

  const handleOptionClick = (optionId: string) => {
    if (phase !== 'thinking') return;
    
    if (isRealtimeMode && isConnected && currentTaskId) {
      // 真实后端模式
      send('thinking.select_option', {
        task_id: currentTaskId,
        current_node_id: nodeId,
        option_id: optionId
      });
      // 本地先更新状态
      selectThinkingOption(nodeId, optionId);
    } else {
      // Mock 模式
      selectThinkingOption(nodeId, optionId);
    }
  };

  const handleCustomSubmit = () => {
    if (phase !== 'thinking') return;
    if (customInput.trim()) {
      if (isRealtimeMode && isConnected && currentTaskId) {
        // 真实后端模式
        send('thinking.custom_input', {
          task_id: currentTaskId,
          current_node_id: nodeId,
          custom_input: customInput.trim()
        });
      }
      // 本地更新状态
      setCustomInput(nodeId, customInput.trim());
    }
  };

  // 获取概览文本
  const getOverviewText = () => {
    if (isDone) {
      return node.selectedOption 
        ? node.options.find(o => o.id === node.selectedOption)?.label
        : node.customInput;
    }
    return isPending ? '待选择' : '已完成';
  };

  return (
    <div className="relative">
      {/* 输入连接点 */}
      <Handle 
        type="target" 
        position={Position.Top} 
        id="top"
        style={{ 
          background: '#2563EB', 
          width: 10, 
          height: 10,
          top: -5,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 100,
          border: '2px solid white',
          boxShadow: '0 1px 3px rgba(0,0,0,0.3)'
        }}
      />
      
      {/* 主节点容器 */}
      <div 
        className={cn(
          "w-[260px] rounded-xl border-2 transition-all duration-300 bg-white relative overflow-hidden",
          isSelected ? "border-blue-500 ring-2 ring-blue-200 shadow-lg" : "border-gray-200",
          isDone && "bg-blue-50"
        )}
      >
        {/* 顶部概览区域 - 始终显示 */}
        <div 
          onClick={handleExpand}
          className={cn(
            "flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-50 transition-colors",
            isExpanded ? "border-b border-gray-200" : ""
          )}
        >
          <div className={cn(
            "w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0",
            isDone ? "bg-blue-500" : isPending ? "bg-blue-400" : "bg-gray-300"
          )}>
            <Brain className="w-3 h-3 text-white" />
          </div>
          
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-gray-700 truncate">
              {node.question}
            </p>
            <p className="text-[10px] text-gray-500 truncate">
              {getOverviewText()}
            </p>
          </div>
          
          <div className="flex items-center gap-1">
            {isDone && <Sparkles className="w-3 h-3 text-yellow-500" />}
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </div>
        </div>

        {/* 展开后的详细内容 */}
        {isExpanded && (
          <div className="bg-gray-900">
            {/* 概览 + 干涉按钮行 */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700">
              <span className="text-[10px] text-gray-400">思考节点 #{nodeId.split('_')[1]}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  // 干涉：重新思考从当前节点
                  if (phase === 'thinking' && isPending) {
                    // 可以重新选择
                  }
                }}
                disabled={!isPending || phase !== 'thinking'}
                className={cn(
                  "px-2 py-1 rounded text-[10px] font-medium transition-colors",
                  isPending && phase === 'thinking'
                    ? "bg-red-500 hover:bg-red-600 text-white"
                    : "bg-gray-700 text-gray-500 cursor-not-allowed"
                )}
              >
                重新思考
              </button>
            </div>

            {/* 详细内容 */}
            <div className="p-3">
              {isPending && phase === 'thinking' ? (
                <>
                  <p className="text-xs text-gray-400 mb-2">选择方案:</p>
                  <div className="space-y-1.5">
                    {node.options.map((option) => (
                      <button
                        key={option.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOptionClick(option.id);
                        }}
                        className="w-full text-left p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
                      >
                        <div className="flex items-center gap-1.5">
                          <span className="text-blue-400 font-semibold text-[10px]">{option.id}.</span>
                          <span className="text-white text-xs">{option.label}</span>
                          {option.isDefault && <Sparkles className="w-2.5 h-2.5 text-yellow-400" />}
                        </div>
                        <p className="text-gray-400 text-[9px] ml-3">{option.description}</p>
                      </button>
                    ))}

                    {/* Custom Input */}
                    {!showCustomInput ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setShowCustomInput(true);
                        }}
                        className="w-full p-2 rounded-lg border border-dashed border-gray-600 hover:border-blue-500 hover:bg-gray-800 transition-colors text-left"
                      >
                        <span className="text-gray-400 text-xs">其他...</span>
                      </button>
                    ) : (
                      <div 
                        onClick={(e) => e.stopPropagation()}
                        className="p-2 rounded-lg border border-blue-500 bg-gray-800"
                      >
                        <input
                          type="text"
                          value={customInput}
                          onChange={(e) => setCustomInputState(e.target.value)}
                          placeholder="输入你的需求..."
                          className="w-full px-2 py-1 rounded border border-gray-600 bg-gray-900 text-white focus:border-blue-500 focus:outline-none text-xs mb-1"
                          autoFocus
                          onKeyDown={(e) => e.key === 'Enter' && handleCustomSubmit()}
                        />
                        <div className="flex gap-1">
                          <button
                            onClick={handleCustomSubmit}
                            disabled={!customInput.trim()}
                            className="flex-1 py-1 bg-blue-500 text-white rounded text-[10px] font-medium hover:bg-blue-600 disabled:opacity-50"
                          >
                            确认
                          </button>
                          <button
                            onClick={() => {
                              setShowCustomInput(false);
                              setCustomInputState('');
                            }}
                            className="flex-1 py-1 bg-gray-700 text-gray-300 rounded text-[10px] font-medium hover:bg-gray-600"
                          >
                            取消
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="text-center py-4">
                  <p className="text-xs text-gray-400">已选择:</p>
                  <p className="text-sm text-white mt-1">{getOverviewText()}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 输出连接点 */}
      <Handle 
        type="source" 
        position={Position.Bottom} 
        id="bottom"
        style={{ 
          background: '#2563EB', 
          width: 10, 
          height: 10,
          bottom: -5,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 100,
          border: '2px solid white',
          boxShadow: '0 1px 3px rgba(0,0,0,0.3)'
        }}
      />
    </div>
  );
}
