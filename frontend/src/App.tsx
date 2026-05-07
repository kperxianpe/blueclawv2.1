import { BlueprintCanvas } from '@/components/BlueprintCanvas';
import { Header } from '@/components/Header';
import { useBlueprintStore } from '@/store/useBlueprintStore';
import { useState } from 'react';
import './App.css';

function App() {
  const { phase, reset } = useBlueprintStore();
  const [apiKey, setApiKey] = useState(localStorage.getItem('blueclaw_api_key') || '');

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header phase={phase} onReset={reset} />
      <div className="flex-1">
        <BlueprintCanvas apiKey={apiKey} onApiKeyChange={setApiKey} />
      </div>
    </div>
  );
}

export default App;
