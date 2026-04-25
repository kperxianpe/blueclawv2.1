import { useState } from 'react';
import { useBlueprintStore } from '@/store/useBlueprintStore';
import { Settings, RotateCcw, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export function SettingsPanel() {
  const { canvasConfig, updateCanvasConfig, resetCanvasConfig } = useBlueprintStore();
  const [isExpanded, setIsExpanded] = useState(false);

  // 计算百分比显示
  const leftPercent = (1 / (1 + canvasConfig.leftRightRatio) * 100).toFixed(1);
  const rightPercent = (canvasConfig.leftRightRatio / (1 + canvasConfig.leftRightRatio) * 100).toFixed(1);
  const execTopPercent = (1 / (1 + canvasConfig.execTopBottomRatio) * 100).toFixed(1);
  const execBottomPercent = (canvasConfig.execTopBottomRatio / (1 + canvasConfig.execTopBottomRatio) * 100).toFixed(1);

  return (
    <div className="bg-blue-900/60 border border-blue-800/50 rounded-lg overflow-hidden">
      {/* 标题栏 - Unity风格文件目录样式 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center gap-2 hover:bg-blue-800/50 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-yellow-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-yellow-400" />
        )}
        <Settings className="w-4 h-4 text-yellow-400" />
        <span className="text-sm font-medium text-yellow-100">config.json</span>
      </button>

      {/* 设置内容 */}
      <div
        className={cn(
          'overflow-hidden transition-all duration-300',
          isExpanded ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        <div className="px-3 py-3 space-y-4 border-t border-blue-800/30">
          {/* 左右比例 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs text-blue-300">左右比例 (1:√5)</label>
              <span className="text-xs text-yellow-400">{leftPercent}% : {rightPercent}%</span>
            </div>
            <input
              type="range"
              min="1"
              max="5"
              step="0.1"
              value={canvasConfig.leftRightRatio}
              onChange={(e) => updateCanvasConfig({ leftRightRatio: parseFloat(e.target.value) })}
              className="w-full h-1.5 bg-blue-800 rounded-lg appearance-none cursor-pointer accent-yellow-400"
            />
            <div className="flex justify-between text-[10px] text-blue-500">
              <span>1:1</span>
              <span>1:√5</span>
              <span>1:5</span>
            </div>
          </div>

          {/* 执行区域上下比例 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs text-blue-300">执行区域比例 (1:2)</label>
              <span className="text-xs text-yellow-400">{execTopPercent}% : {execBottomPercent}%</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="4"
              step="0.1"
              value={canvasConfig.execTopBottomRatio}
              onChange={(e) => updateCanvasConfig({ execTopBottomRatio: parseFloat(e.target.value) })}
              className="w-full h-1.5 bg-blue-800 rounded-lg appearance-none cursor-pointer accent-yellow-400"
            />
            <div className="flex justify-between text-[10px] text-blue-500">
              <span>1:0.5</span>
              <span>1:2</span>
              <span>1:4</span>
            </div>
          </div>

          {/* 思考蓝图缩放 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs text-blue-300">思考蓝图缩放</label>
              <span className="text-xs text-yellow-400">{canvasConfig.thinkingCanvasZoom.toFixed(1)}x</span>
            </div>
            <input
              type="range"
              min="0.3"
              max="2"
              step="0.1"
              value={canvasConfig.thinkingCanvasZoom}
              onChange={(e) => updateCanvasConfig({ thinkingCanvasZoom: parseFloat(e.target.value) })}
              className="w-full h-1.5 bg-blue-800 rounded-lg appearance-none cursor-pointer accent-yellow-400"
            />
          </div>

          {/* 执行蓝图缩放 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs text-blue-300">执行蓝图缩放</label>
              <span className="text-xs text-yellow-400">{canvasConfig.executionCanvasZoom.toFixed(1)}x</span>
            </div>
            <input
              type="range"
              min="0.3"
              max="2"
              step="0.1"
              value={canvasConfig.executionCanvasZoom}
              onChange={(e) => updateCanvasConfig({ executionCanvasZoom: parseFloat(e.target.value) })}
              className="w-full h-1.5 bg-blue-800 rounded-lg appearance-none cursor-pointer accent-yellow-400"
            />
          </div>

          {/* 思考蓝图节点间距 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs text-blue-300">思考节点间距</label>
              <span className="text-xs text-yellow-400">{canvasConfig.thinkingNodeSpacing}px</span>
            </div>
            <input
              type="range"
              min="100"
              max="300"
              step="10"
              value={canvasConfig.thinkingNodeSpacing}
              onChange={(e) => updateCanvasConfig({ thinkingNodeSpacing: parseInt(e.target.value) })}
              className="w-full h-1.5 bg-blue-800 rounded-lg appearance-none cursor-pointer accent-yellow-400"
            />
          </div>

          {/* 执行蓝图节点统一间距 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs text-blue-300">执行节点间距</label>
              <span className="text-xs text-yellow-400">{canvasConfig.executionNodeSpacing}px</span>
            </div>
            <input
              type="range"
              min="80"
              max="250"
              step="10"
              value={canvasConfig.executionNodeSpacing}
              onChange={(e) => updateCanvasConfig({ executionNodeSpacing: parseInt(e.target.value) })}
              className="w-full h-1.5 bg-blue-800 rounded-lg appearance-none cursor-pointer accent-yellow-400"
            />
            <div className="flex justify-between text-[10px] text-blue-500">
              <span>紧凑</span>
              <span>默认</span>
              <span>宽松</span>
            </div>
          </div>

          {/* 背景样式 */}
          <div className="space-y-2">
            <label className="text-xs text-blue-300">背景样式</label>
            <div className="grid grid-cols-4 gap-1">
              {(['gradient', 'solid', 'grid', 'dots'] as const).map((bg) => (
                <button
                  key={bg}
                  onClick={() => updateCanvasConfig({ canvasBackground: bg })}
                  className={cn(
                    'px-2 py-1.5 text-[10px] rounded transition-colors',
                    canvasConfig.canvasBackground === bg
                      ? 'bg-yellow-400 text-blue-900 font-medium'
                      : 'bg-blue-800/50 text-blue-300 hover:bg-blue-800'
                  )}
                >
                  {bg === 'gradient' && '渐变'}
                  {bg === 'solid' && '纯色'}
                  {bg === 'grid' && '网格'}
                  {bg === 'dots' && '点阵'}
                </button>
              ))}
            </div>
          </div>

          {/* 重置按钮 */}
          <button
            onClick={resetCanvasConfig}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-blue-800/50 hover:bg-blue-800 text-blue-300 text-xs rounded transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            重置为默认值
          </button>
        </div>
      </div>
    </div>
  );
}
