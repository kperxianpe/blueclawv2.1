/**
 * WebSocket Message Type Definitions
 * Aligned with backend Python models (blueclaw/core/state_sync.py)
 */

// ============================================================================
// Common
// ============================================================================

export interface WSMessage {
  type: string;
  payload?: Record<string, any>;
  timestamp?: number;
  message_id?: string;
  error?: string;
}

// ============================================================================
// Backend -> Frontend: Thinking Phase
// ============================================================================

export interface ThinkingOption {
  id: string;
  label: string;
  description: string;
  confidence: number;
  is_default: boolean;
}

export interface ThinkingNodeData {
  id: string;
  question: string;
  options: ThinkingOption[];
  allow_custom: boolean;
  parent_id: string | null;
  selected_option_id: string | null;
  custom_input: string | null;
  created_at: string;
  position: { x: number; y: number };
  status: 'active' | 'resolved' | 'skipped';
}

export interface PathItem {
  node_id: string;
  question: string;
  selected_option: ThinkingOption | null;
  custom_input: string | null;
}

export interface ThinkingNodeCreatedPayload {
  node: ThinkingNodeData;
  options: ThinkingOption[];
  allow_custom: boolean;
  previous_node_id: string | null;
}

export interface ThinkingOptionSelectedPayload {
  option_id: string;
  current_node_id: string;
  has_more: boolean;
  final_path?: PathItem[];
}

export interface ThinkingCustomInputPayload {
  current_node_id: string;
  custom_input: string;
  has_more: boolean;
}

export interface ThinkingCompletedPayload {
  final_path: PathItem[];
}

export interface ThinkingConvergedPayload {
  final_path: PathItem[];
  auto_transition: boolean;
  message: string;
}

// ============================================================================
// Backend -> Frontend: Execution Phase
// ============================================================================

export interface ExecutionStepData {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused' | 'skipped';
  dependencies: string[];
  position: { x: number; y: number };
  tool?: string;
  is_main_path: boolean;
  is_convergence: boolean;
  convergence_type?: 'parallel' | 'sequential';
  result?: any;
  error?: string;
  needs_intervention?: boolean;
  is_archived?: boolean;
}

export interface ExecutionBlueprintPayload {
  blueprint: {
    id: string;
    steps: ExecutionStepData[];
  };
}

export interface ExecutionStepStartedPayload {
  step_id: string;
  id: string;
  name: string;
  status: 'running';
  start_time?: string;
  tool?: string;
}

export interface ExecutionStepCompletedPayload {
  step_id: string;
  id: string;
  name: string;
  status: 'completed';
  result?: any;
  duration_ms: number;
}

export interface ExecutionStepFailedPayload {
  step_id: string;
  status: 'failed';
  error: string;
  can_retry: boolean;
  error_type?: string;
  stack_trace?: string;
}

export interface SuggestedAction {
  id: 'replan' | 'skip' | 'retry' | 'custom';
  label: string;
  description: string;
}

export interface ExecutionInterventionNeededPayload {
  step_id: string;
  step_name: string;
  reason: string;
  suggested_actions: SuggestedAction[];
}

export interface ExecutionReturnedToThinkingPayload {
  archived_step_ids: string[];
}

export interface ExecutionReplannedPayload {
  from_step_id: string;
  abandoned_steps: string[];
  new_steps: ExecutionStepData[];
}

export interface ExecutionPausedPayload {
  blueprint_id: string;
}

export interface ExecutionResumedPayload {
  blueprint_id: string;
}

export interface ExecutionCompletedPayload {
  success: boolean;
  summary: string;
  completed_steps: number;
  total_steps: number;
  execution_time: number;
  can_save: boolean;
}

// ============================================================================
// Backend -> Frontend: Task Lifecycle
// ============================================================================

export interface TaskStartedPayload {
  task_id: string;
  user_input: string;
}

export interface TaskInterruptedPayload {
  task_id: string;
}

// ============================================================================
// Backend -> Frontend: Visual Adapter
// ============================================================================

export interface VisualElement {
  id?: string;
  type?: string;
  bbox?: { x: number; y: number; w: number; h: number };
  text?: string;
  [key: string]: any;
}

export interface VisPreviewPayload {
  screenshot_id: string;
  image_base64: string;
  width: number;
  height: number;
  annotations: any[];
  analysis: {
    scene_type?: string;
    elements: VisualElement[];
    suggested_next_action?: string;
  };
}

export interface VisActionExecutedPayload {
  action: string;
  result: any;
}

// ============================================================================
// Backend -> Frontend: Error
// ============================================================================

export interface ErrorPayload {
  message: string;
  error?: string;
}

// ============================================================================
// Backend -> Frontend: Freeze / Screenshot / Annotation
// ============================================================================

export interface ScreenshotPayload {
  adapterId: string;
  stepId: string;
  image: string; // base64 PNG
  timestamp: number;
}

export interface FreezeConfirmedPayload {
  adapterId: string;
  stepId: string;
  screenshot: string; // base64 PNG
  freezeToken: string;
}

export interface AnnotationBox {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  label?: string;
}

// ============================================================================
// Frontend -> Backend: Freeze / Annotation
// ============================================================================

export interface FreezeRequestPayload {
  task_id: string;
  step_id: string;
  reason?: string;
}

export interface SubmitAnnotationPayload {
  task_id: string;
  step_id: string;
  annotation?: string; // 文本备注
  boxes?: AnnotationBox[]; // 框选标注
}

// ============================================================================
// Frontend -> Backend: Thinking Control
// ============================================================================

export interface SelectOptionPayload {
  task_id: string;
  current_node_id: string;
  option_id: string;
}

export interface CustomInputPayload {
  task_id: string;
  current_node_id: string;
  custom_input: string;
}

export interface ConfirmExecutionPayload {
  task_id: string;
}

// ============================================================================
// Frontend -> Backend: Execution Control
// ============================================================================

export interface ExecutionStartPayload {
  task_id: string;
  blueprint_id?: string;
}

export interface ExecutionPausePayload {
  task_id: string;
  blueprint_id: string;
}

export interface ExecutionResumePayload {
  task_id: string;
  blueprint_id: string;
}

export interface ExecutionIntervenePayload {
  task_id: string;
  blueprint_id: string;
  step_id: string;
  action: 'replan' | 'skip' | 'retry' | 'modify';
  custom_input?: string;
}

export interface ExecutionCancelPayload {
  task_id: string;
  blueprint_id: string;
}

// ============================================================================
// Frontend -> Backend: Task Control
// ============================================================================

export interface TaskStartPayload {
  user_input: string;
}

export interface TaskInterruptPayload {
  task_id: string;
}

// ============================================================================
// Type guards (runtime validation helpers)
// ============================================================================

export function isThinkingNodeCreated(msg: WSMessage): msg is { type: 'thinking.node_created'; payload: ThinkingNodeCreatedPayload } {
  return msg.type === 'thinking.node_created' && msg.payload?.node !== undefined;
}

export function isExecutionBlueprintLoaded(msg: WSMessage): msg is { type: 'execution.blueprint_loaded'; payload: ExecutionBlueprintPayload } {
  return msg.type === 'execution.blueprint_loaded' && msg.payload?.blueprint !== undefined;
}

export function isExecutionStepStarted(msg: WSMessage): msg is { type: 'execution.step_started'; payload: ExecutionStepStartedPayload } {
  return msg.type === 'execution.step_started' && msg.payload?.step_id !== undefined;
}

export function isExecutionStepCompleted(msg: WSMessage): msg is { type: 'execution.step_completed'; payload: ExecutionStepCompletedPayload } {
  return msg.type === 'execution.step_completed' && msg.payload?.step_id !== undefined;
}
