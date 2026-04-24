import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { WebSocketProvider } from './contexts/WebSocketContext'
import { RealtimeProvider } from './components/RealtimeProvider'
import './store/adapterStore'  // Exposes __ADAPTER_SET__ for E2E testing

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <WebSocketProvider>
      <RealtimeProvider>
        <App />
      </RealtimeProvider>
    </WebSocketProvider>
  </StrictMode>,
)
