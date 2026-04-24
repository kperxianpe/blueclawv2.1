/**
 * WebSocket Context
 * 共享 WebSocket 连接状态
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
  /** Incremented on every received message. Use as useEffect dep to process messages. */
  messageVersion: number;
  /** Consume all unprocessed messages and return them. */
  consumeMessages: () => WebSocketMessage[];
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8006';

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
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      console.log('[WebSocketContext] Connecting to:', WS_URL);
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WebSocketContext] Connected');
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        // 暴露到 window 以便测试访问
        if (typeof window !== 'undefined') {
          (window as any).__WEBSOCKET_INSTANCE__ = ws;
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketMessage;
          console.log('[WebSocketContext] Received:', data.type);
          messagesRef.current.push(data);
          setLastMessage(data);
          setMessageVersion(v => v + 1);
        } catch (e) {
          console.error('[WebSocketContext] Parse error:', e);
        }
      };

      ws.onerror = (e) => {
        console.error('[WebSocketContext] Error:', e);
        setError('WebSocket connection error');
        setIsConnected(false);
      };

      ws.onclose = () => {
        console.log('[WebSocketContext] Disconnected');
        setIsConnected(false);
        wsRef.current = null;

        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          console.log(`[WebSocketContext] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        }
      };
    } catch (e) {
      console.error('[WebSocketContext] Failed to connect:', e);
      setError('Failed to create WebSocket connection');
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const consumeMessages = useCallback(() => {
    const newMessages = messagesRef.current.slice(consumedIndexRef.current);
    consumedIndexRef.current = messagesRef.current.length;
    return newMessages;
  }, []);

  const send = useCallback((type: string, payload: any = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message = {
        type,
        payload,
        timestamp: Date.now(),
        message_id: crypto.randomUUID()
      };
      console.log('[WebSocketContext] Send:', type, payload);
      wsRef.current.send(JSON.stringify(message));
      return true;
    } else {
      console.warn('[WebSocketContext] Not connected, message dropped:', type);
      return false;
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return (
    <WebSocketContext.Provider value={{ isConnected, lastMessage, error, send, connect, disconnect, messageVersion, consumeMessages }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider');
  }
  return context;
}
