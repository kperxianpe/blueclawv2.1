import { CheckCircle2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface CompletionScreenProps {
  onReset: () => void;
}

export function CompletionScreen({ onReset }: CompletionScreenProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] px-4">
      {/* Success Icon */}
      <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mb-6 animate-in zoom-in-50 duration-500">
        <CheckCircle2 className="w-10 h-10 text-green-500" />
      </div>

      {/* Title */}
      <h2 className="text-3xl font-bold text-gray-900 mb-3">
        任务完成！
      </h2>
      <p className="text-lg text-gray-500 mb-8 text-center max-w-md">
        所有步骤执行成功，AI 已为你完成规划
      </p>

      {/* Summary Card */}
      <div className="w-full max-w-md bg-white rounded-2xl border border-gray-200 shadow-sm p-6 mb-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-blue-500" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">执行摘要</h3>
            <p className="text-sm text-gray-500">5 个步骤全部完成</p>
          </div>
        </div>
        
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">查询天气</span>
            <span className="text-green-600 font-medium">已完成</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">搜索景点</span>
            <span className="text-green-600 font-medium">已完成</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">规划交通</span>
            <span className="text-green-600 font-medium">已重新规划</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">推荐酒店</span>
            <span className="text-green-600 font-medium">已完成</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">生成行程</span>
            <span className="text-green-600 font-medium">已完成</span>
          </div>
        </div>
      </div>

      {/* Reset Button */}
      <Button
        onClick={onReset}
        className="px-8 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium"
      >
        开始新任务
      </Button>
    </div>
  );
}
