import { useState } from 'react';
import { Sparkles, ArrowRight, MapPin, Code, Key, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface InputScreenProps {
  onSubmit: (input: string, apiKey?: string) => void;
}

const quickExamples = [
  { text: '帮我规划北京3日游', icon: MapPin },
  { text: '写Python脚本', icon: Code },
];

export function InputScreen({ onSubmit }: InputScreenProps) {
  const [input, setInput] = useState('');
  const [apiKey, setApiKey] = useState(localStorage.getItem('blueclaw_api_key') || '');
  const [showKey, setShowKey] = useState(false);

  const handleSubmit = () => {
    if (input.trim()) {
      // Save key to localStorage for convenience
      if (apiKey.trim()) {
        localStorage.setItem('blueclaw_api_key', apiKey.trim());
      }
      onSubmit(input.trim(), apiKey.trim() || undefined);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-full w-full px-4">
      {/* Logo & Title */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-lg shadow-blue-200">
          <Sparkles className="w-6 h-6 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900">Blueclaw</h1>
      </div>

      {/* Main Question */}
      <div className="text-center mb-8">
        <h2 className="text-4xl font-semibold text-gray-900 mb-3">
          你想做什么？
        </h2>
        <p className="text-lg text-gray-500">
          告诉我你的需求，AI 会帮你规划并执行
        </p>
      </div>

      {/* API Key Input */}
      <div className="w-full max-w-2xl mb-4">
        <div className="relative">
          <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            type={showKey ? 'text' : 'password'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="填入 Kimi API Key（可选，留空则使用系统默认）"
            className="w-full h-10 pl-10 pr-10 text-sm rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
          />
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Input Box */}
      <div className="w-full max-w-2xl mb-6">
        <div className="relative">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="帮我规划一个周末旅行..."
            className="w-full h-16 pl-6 pr-32 text-lg rounded-2xl border-2 border-gray-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all shadow-sm"
          />
          <Button
            onClick={handleSubmit}
            disabled={!input.trim()}
            data-testid="submit-task"
            className="absolute right-2 top-1/2 -translate-y-1/2 h-12 px-6 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            开始
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>

      {/* Quick Examples */}
      <div className="flex items-center gap-3 text-sm text-gray-500">
        <span>试试：</span>
        {quickExamples.map((example, index) => (
          <button
            key={index}
            onClick={() => setInput(example.text)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-100 hover:bg-blue-50 hover:text-blue-600 transition-colors"
          >
            <example.icon className="w-3.5 h-3.5" />
            {example.text}
          </button>
        ))}
      </div>
    </div>
  );
}
