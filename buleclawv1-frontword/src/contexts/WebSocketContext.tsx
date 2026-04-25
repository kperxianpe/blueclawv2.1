/**
 * WebSocket Context for API V2
 * Connects to backend /ws with message queue (survives React 18 batching)
 */
import { createContext, useContext, useState, useEffect, useRef, useCallback, type ReactNode } from 'react';

export interface WebSocketMessage {
  type: string;
  payload?: any;
  timestamp?: number;
  message_id?: string;
  error?: string;
}

interface WebSocketContextType {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  error: string | null;
  send: (type: string, payload?: any) => boolean;
  connect: () => void;
  disconnect: () => void;
  messageVersion: number;
  consumeMessages: () => WebSocketMessage[];
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8006/ws';

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [messageVersion, setMessageVersion] = useState(0);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;
  const messagesRef = useRef<WebSocketMessage[]>([]);
  const consumedIndexRef = useRef(0);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    try {
      console.log('[WS] Connecting to:', WS_URL);
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onopen = () => {
        console.log('[WS] Connected');
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        if (typeof window !== 'undefined') {
          (window as any).__WEBSOCKET_INSTANCE__ = ws;
        }
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketMessage;
          console.log('[WS] Received:', data.type);
          messagesRef.current.push(data);
          setLastMessage(data);
          setMessageVersion(v => v + 1);
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };
      ws.onerror = () => {
        setError('WebSocket connection error');
        setIsConnected(false);
      };
      ws.onclose = () => {
        console.log('[WS] Disconnected');
        setIsConnected(false);
        wsRef.current = null;
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        }
      };
    } catch (e) {
      setError('Failed to create WebSocket connection');
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
  }, []);

  const consumeMessages = useCallback(() => {
    const newMessages = messagesRef.current.slice(consumedIndexRef.current);
    consumedIndexRef.current = messagesRef.current.length;
    return newMessages;
  }, []);

  const send = useCallback((type: string, payload: any = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message = { type, payload, timestamp: Date.now(), message_id: crypto.randomUUID() };
      console.log('[WS] Send:', type, payload);
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    console.warn('[WS] Not connected, message dropped:', type);
    return false;
  }, []);

  useEffect(() => { connect(); return () => disconnect(); }, [connect, disconnect]);

  return (
    <WebSocketContext.Provider value={{ isConnected, lastMessage, error, send, connect, disconnect, messageVersion, consumeMessages }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext);
  if (!context) throw new Error('useWebSocketContext must be used within WebSocketProvider');
  return context;
}
