import { BlueprintCanvas } from '@/components/BlueprintCanvas';
import { Header } from '@/components/Header';
import { useBlueprintStore } from '@/store/useBlueprintStore';
import './App.css';

function App() {
  const { phase, reset } = useBlueprintStore();

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header phase={phase} onReset={reset} />
      <div className="flex-1">
        <BlueprintCanvas />
      </div>
    </div>
  );
}

export default App;
