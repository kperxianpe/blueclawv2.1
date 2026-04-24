/**
 * Minimal adapter runtime store for testing
 * Exposes __ADAPTER_SET__ on window for Playwright E2E tests
 */

interface AdapterSnapshot {
  studioId?: string;
  blueprintId?: string;
  taskId?: string;
  adapterType?: string;
  state?: string;
  currentUrl?: string;
  annotations?: any[];
  lastUpdated?: number;
}

interface AdapterStoreState {
  runtimeMap: Record<string, AdapterSnapshot>;
}

const initialState: AdapterStoreState = {
  runtimeMap: {},
};

let state = { ...initialState };

function setState(updater: ((s: AdapterStoreState) => AdapterStoreState) | Partial<AdapterStoreState>) {
  if (typeof updater === 'function') {
    state = updater(state);
  } else {
    state = { ...state, ...updater };
  }
}

if (typeof window !== 'undefined') {
  (window as any).__ADAPTER_SET__ = setState;
  (window as any).__ADAPTER_STORE__ = state;
}

export function getAdapterStore() {
  return state;
}

export function updateAdapterRuntime(blueprintId: string, snapshot: Partial<AdapterSnapshot>) {
  setState((s) => ({
    ...s,
    runtimeMap: {
      ...s.runtimeMap,
      [blueprintId]: {
        ...(s.runtimeMap[blueprintId] || {}),
        ...snapshot,
        lastUpdated: Date.now(),
      },
    },
  }));
}
