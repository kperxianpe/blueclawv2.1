import { useState } from 'react';
import { Globe, RefreshCw, Home, Lock, Star, ArrowLeft, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export function WebBrowser() {
  const [url, setUrl] = useState('https://www.bing.com');
  const [displayUrl, setDisplayUrl] = useState('https://www.bing.com');
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState<string[]>(['https://www.bing.com']);
  const [historyIndex, setHistoryIndex] = useState(0);

  const handleNavigate = () => {
    let targetUrl = displayUrl.trim();
    if (!targetUrl) return;
    if (!targetUrl.startsWith('http')) {
      targetUrl = 'https://' + targetUrl;
    }
    setIsLoading(true);
    setTimeout(() => {
      setUrl(targetUrl);
      setDisplayUrl(targetUrl);
      setIsLoading(false);
      const newHistory = history.slice(0, historyIndex + 1);
      newHistory.push(targetUrl);
      setHistory(newHistory);
      setHistoryIndex(newHistory.length - 1);
    }, 500);
  };

  const handleBack = () => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      setHistoryIndex(newIndex);
      setUrl(history[newIndex]);
      setDisplayUrl(history[newIndex]);
    }
  };

  const handleForward = () => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      setHistoryIndex(newIndex);
      setUrl(history[newIndex]);
      setDisplayUrl(history[newIndex]);
    }
  };

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 500);
  };

  const handleHome = () => {
    setDisplayUrl('https://www.bing.com');
    handleNavigate();
  };

  return (
    <div className="w-full h-full flex flex-col bg-slate-900">
      {/* 地址栏区域 */}
      <div className="flex items-center gap-2 px-3 py-2 bg-slate-800 border-b border-slate-700">
        {/* 导航按钮 */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleBack}
            disabled={historyIndex <= 0}
            className={cn(
              "w-7 h-7 rounded flex items-center justify-center transition-colors",
              historyIndex > 0 ? "hover:bg-slate-700 text-slate-300" : "text-slate-600 cursor-not-allowed"
            )}
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <button
            onClick={handleForward}
            disabled={historyIndex >= history.length - 1}
            className={cn(
              "w-7 h-7 rounded flex items-center justify-center transition-colors",
              historyIndex < history.length - 1 ? "hover:bg-slate-700 text-slate-300" : "text-slate-600 cursor-not-allowed"
            )}
          >
            <ArrowRight className="w-4 h-4" />
          </button>
          <button
            onClick={handleRefresh}
            className="w-7 h-7 rounded hover:bg-slate-700 flex items-center justify-center text-slate-300 transition-colors"
          >
            <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
          </button>
          <button
            onClick={handleHome}
            className="w-7 h-7 rounded hover:bg-slate-700 flex items-center justify-center text-slate-300 transition-colors"
          >
            <Home className="w-4 h-4" />
          </button>
        </div>

        {/* 地址输入框 */}
        <div className="flex-1 flex items-center gap-2 px-3 py-1.5 bg-slate-700/50 rounded-lg">
          <Lock className="w-3 h-3 text-green-400 flex-shrink-0" />
          <input
            type="text"
            value={displayUrl}
            onChange={(e) => setDisplayUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleNavigate()}
            className="flex-1 bg-transparent text-slate-200 text-sm outline-none"
          />
          <Star className="w-3 h-3 text-slate-500 hover:text-yellow-400 cursor-pointer transition-colors" />
        </div>
      </div>

      {/* 浏览器内容区域 */}
      <div className="flex-1 relative bg-white overflow-hidden">
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-100">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-slate-500">正在加载...</span>
            </div>
          </div>
        ) : (
          <div className="w-full h-full flex flex-col">
            {/* 模拟网页内容 */}
            <div className="flex-1 bg-gradient-to-b from-slate-50 to-white p-6 overflow-auto">
              {url.includes('bing') ? (
                /* Bing首页模拟 */
                <div className="flex flex-col items-center mt-16">
                  <div className="text-4xl font-bold text-slate-700 mb-8 tracking-tight">
                    Bing
                  </div>
                  <div className="w-full max-w-xl relative">
                    <input
                      type="text"
                      className="w-full px-4 py-3 bg-white border border-slate-300 rounded-full shadow-sm text-base outline-none focus:border-blue-500 focus:shadow-md transition-all"
                      placeholder="搜索网页、图片、视频..."
                    />
                    <button className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center hover:bg-blue-600 transition-colors">
                      <ArrowRight className="w-4 h-4 text-white" />
                    </button>
                  </div>
                  <div className="flex gap-6 mt-8">
                    {['网页', '图片', '视频', '地图', '新闻'].map((item) => (
                      <button
                        key={item}
                        className="px-4 py-2 text-sm text-slate-600 hover:text-blue-600 hover:bg-slate-100 rounded-lg transition-colors"
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                /* 通用网页模拟 */
                <div className="max-w-4xl mx-auto">
                  <div className="h-16 bg-slate-800 rounded-t-lg flex items-center px-6">
                    <Globe className="w-5 h-5 text-blue-400 mr-3" />
                    <span className="text-white font-medium">{url}</span>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-b-lg p-8 min-h-[400px]">
                    <h1 className="text-2xl font-bold text-slate-800 mb-4">网页内容</h1>
                    <p className="text-slate-600 mb-4">当前访问的URL: {url}</p>
                    <div className="space-y-3">
                      <div className="h-3 bg-slate-200 rounded w-3/4" />
                      <div className="h-3 bg-slate-200 rounded w-1/2" />
                      <div className="h-3 bg-slate-200 rounded w-2/3" />
                      <div className="h-3 bg-slate-200 rounded w-4/5" />
                      <div className="h-3 bg-slate-200 rounded w-3/5" />
                    </div>
                    <div className="mt-6 grid grid-cols-3 gap-4">
                      <div className="h-24 bg-slate-200 rounded-lg" />
                      <div className="h-24 bg-slate-200 rounded-lg" />
                      <div className="h-24 bg-slate-200 rounded-lg" />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 底部状态栏 */}
      <div className="flex items-center justify-between px-3 py-1 bg-slate-800 border-t border-slate-700 text-xs text-slate-500">
        <span>{isLoading ? '正在加载...' : '完成'}</span>
        <span>Edge 模拟器</span>
      </div>
    </div>
  );
}
