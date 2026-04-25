# Blueclaw AI Canvas - API Specification

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Blueclaw AI Canvas                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────┐  ┌─────────────────────────────────┐  │
│  │  Thinking       │  │  Settings   │  │  Execution                      │  │
│  │  Blueprint      │  │  Divider    │  │  Area                           │  │
│  │  (Left Panel)   │  │  (60px)     │  │  (Right Panel)                  │  │
│  │                 │  │             │  │  ┌──────────┐  ┌────────────┐  │  │
│  │  - Nodes[]      │  │  - Icon     │  │  │Execution │  │  Visual    │  │  │
│  │  - Edges[]      │  │  - Modal    │  │  │Blueprint │  │  Area      │  │  │
│  │  - Canvas       │  │             │  │  │          │  │            │  │  │
│  │                 │  │             │  │  │ - Nodes  │  │            │  │  │
│  │  Ratio: ~30.9%  │  │             │  │  │ - Edges  │  │            │  │  │
│  │                 │  │             │  │  │          │  │            │  │  │
│  │                 │  │             │  │  │ Ratio:   │  │ Ratio:     │  │  │
│  │                 │  │             │  │  │ ~33.3%   │  │ ~66.7%     │  │  │
│  └─────────────────┘  └─────────────┘  └─────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                              State Management (Zustand)                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  BlueprintStore                                                        │ │
│  │  ├── phase: 'input' | 'thinking' | 'execution' | 'completed'          │ │
│  │  ├── userInput: string                                                │ │
│  │  ├── thinkingNodes: ThinkingNodeType[]                                │ │
│  │  ├── executionSteps: ExecutionStep[]                                  │ │
│  │  ├── canvasConfig: CanvasConfig                                       │ │
│  │  └── UI State (selected IDs, panels, etc.)                            │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Core Types

### 2.1 AppPhase
```typescript
type AppPhase = 'input' | 'thinking' | 'execution' | 'completed';
```
- `input`: Initial state, waiting for user input
- `thinking`: Generating thinking blueprint through user choices
- `execution`: Executing the generated execution blueprint
- `completed`: All execution steps completed

### 2.2 ThinkingNodeType
```typescript
interface ThinkingNodeType {
  id: string;                    // Format: "thinking_XXX"
  question: string;              // The question to ask user
  options: ThinkingOption[];     // Available options (A/B/C/D)
  allowCustom: boolean;          // Allow custom input
  status: 'pending' | 'selected';
  selectedOption?: string;       // Selected option ID
  customInput?: string;          // Custom input text
}

interface ThinkingOption {
  id: string;                    // 'A' | 'B' | 'C' | 'D'
  label: string;                 // Option label
  description: string;           // Option description
  confidence: number;            // 0-1 confidence score
  isDefault?: boolean;           // Mark as recommended option
}
```

### 2.3 ExecutionStep
```typescript
interface ExecutionStep {
  id: string;                    // Format: "step_XXX" or "branch_XX"
  name: string;                  // Step name
  description: string;           // Step description
  status: 'pending' | 'running' | 'completed' | 'failed';
  dependencies: string[];        // IDs of prerequisite steps
  result?: string;               // Execution result
  error?: string;                // Error message if failed
  position: { x: number; y: number };  // Canvas position
  
  // Visual properties
  isMainPath: boolean;           // true = main path, false = branch
  isConvergence?: boolean;       // true = convergence node
  convergenceType?: 'parallel' | 'sequential';
  needsIntervention?: boolean;   // Requires user intervention
  isArchived?: boolean;          // Archived after intervention
}
```

### 2.4 CanvasConfig
```typescript
interface CanvasConfig {
  // Layout ratios
  leftRightRatio: number;        // Default: √5 ≈ 2.236
  execTopBottomRatio: number;    // Default: 2
  
  // Zoom levels
  thinkingCanvasZoom: number;    // Default: 1
  executionCanvasZoom: number;   // Default: 1
  
  // Node spacing
  thinkingNodeSpacing: number;   // Default: 180 (px)
  executionNodeSpacing: number;  // Default: 140 (px)
  
  // Background
  canvasBackground: 'gradient' | 'solid' | 'grid' | 'dots';
  backgroundColor: string;       // Default: '#0f172a'
}
```

## 3. Store Interface (BlueprintStore)

### 3.1 State Properties
```typescript
interface BlueprintState {
  // Core state
  phase: AppPhase;
  userInput: string;
  
  // Thinking blueprint
  thinkingNodes: ThinkingNodeType[];
  currentThinkingIndex: number;
  selectedThinkingNodeId: string | null;
  
  // Execution blueprint
  executionSteps: ExecutionStep[];
  selectedExecutionStepId: string | null;
  
  // Intervention
  showInterventionPanel: boolean;
  interventionStepId: string | null;
  
  // Configuration
  canvasConfig: CanvasConfig;
}
```

### 3.2 Actions

#### Input Phase
```typescript
// Set user input text
setUserInput: (input: string) => void

// Start thinking phase
startThinking: () => void
```

#### Thinking Phase
```typescript
// Select an option for a thinking node
selectThinkingOption: (nodeId: string, optionId: string) => void

// Set custom input for a thinking node
setCustomInput: (nodeId: string, input: string) => void

// Select a thinking node (for UI highlighting)
selectThinkingNode: (nodeId: string) => void

// Complete thinking phase, generate execution blueprint
completeThinking: () => void
```

#### Execution Phase
```typescript
// Start execution
startExecution: () => void

// Execute next available step
executeNextStep: () => void

// Select an execution step (for UI highlighting)
selectExecutionStep: (stepId: string) => void

// Trigger intervention for a step
interveneExecution: (stepId: string) => void

// Handle intervention action
handleIntervention: (action: 'continue' | 'newBranch' | 'stop') => void

// Hide intervention panel
hideIntervention: () => void
```

#### Configuration
```typescript
// Update canvas configuration
updateCanvasConfig: (config: Partial<CanvasConfig>) => void

// Reset to default configuration
resetCanvasConfig: () => void

// Reset entire application state
reset: () => void
```

## 4. Execution Flow

### 4.1 Phase Transition Diagram
```
┌─────────┐    setUserInput    ┌───────────┐
│  input  │ ──────────────────>│ thinking  │
└─────────┘                    └─────┬─────┘
                                     │
                                     │ completeThinking
                                     │ (generates executionSteps)
                                     v
                              ┌───────────┐
                              │ execution │<──────┐
                              └─────┬─────┘       │
                                    │             │
                    ┌───────────────┼─────────────┘
                    │               │
                    │ intervene     │ all completed
                    │ (back to      │
                    │  thinking)    v
                    │          ┌───────────┐
                    └─────────>│ completed │
                               └───────────┘
```

### 4.2 Execution Algorithm
```typescript
function executeNextStep() {
  // 1. Find all pending steps whose dependencies are completed
  const executableSteps = executionSteps.filter(step => 
    step.status === 'pending' &&
    step.dependencies.every(depId => 
      getStep(depId).status === 'completed'
    )
  );
  
  // 2. Prioritize main path steps
  const mainPathSteps = executableSteps.filter(s => s.isMainPath);
  const branchSteps = executableSteps.filter(s => !s.isMainPath);
  
  // 3. Execute main path first, then branches
  const stepsToExecute = mainPathSteps.length > 0 
    ? mainPathSteps 
    : branchSteps;
  
  // 4. Execute steps (with delay for visualization)
  stepsToExecute.forEach(step => {
    step.status = 'running';
    setTimeout(() => {
      step.status = 'completed';
      step.result = generateMockResult(step);
      executeNextStep(); // Recursive call
    }, 1500);
  });
}
```

## 5. Intervention Flow

### 5.1 Intervention Trigger
```typescript
function interveneExecution(stepId: string) {
  const stepIndex = executionSteps.findIndex(s => s.id === stepId);
  const completedSteps = executionSteps
    .slice(0, stepIndex + 1)
    .filter(s => s.status === 'completed');
  
  // Generate intervention question with context
  const context = completedSteps
    .map(s => `${s.name}: ${s.result || 'completed'}`)
    .join('; ');
  
  const interventionNode = generateThinkingNode(0, 
    `At "${currentStep.name}" - re-plan. Completed: ${context}. How to adjust?`
  );
  
  // Switch back to thinking phase
  setState({
    phase: 'thinking',
    thinkingNodes: [interventionNode],
    executionSteps: executionSteps.map((s, i) => 
      i <= stepIndex ? { ...s, isArchived: true } : s
    )
  });
}
```

### 5.2 Intervention Options
- `A. Adjust current step` - Modify current execution strategy
- `B. Add branch steps` - Execute additional tasks in parallel
- `C. Skip current step` - Proceed to subsequent execution
- `D. Complete re-plan` - Redesign based on completed results

## 6. Node Positioning Algorithm

### 6.1 Thinking Blueprint Layout
```typescript
function calculateThinkingNodePosition(index: number, spacing: number) {
  return {
    x: 150,  // Fixed X position
    y: index * spacing  // Vertical stacking
  };
}
```

### 6.2 Execution Blueprint Layout
```typescript
function calculateExecutionNodePosition(
  step: ExecutionStep, 
  spacing: number
) {
  const START_X = 20;
  const MAIN_Y = 80;
  const BRANCH_Y_START = MAIN_Y + spacing;
  
  const stepIndex = extractNumber(step.id);
  
  if (step.id.startsWith('step_')) {
    // Main path: horizontal layout
    return {
      x: START_X + spacing * (stepIndex - 1),
      y: MAIN_Y
    };
  } else if (step.id.startsWith('branch_')) {
    // Branch: vertical layout from step_003
    const branchIndex = stepIndex - 1;
    return {
      x: START_X + spacing * 2,
      y: BRANCH_Y_START + spacing * branchIndex
    };
  }
}
```

## 7. Edge Generation

### 7.1 Thinking Blueprint Edges
```typescript
function generateThinkingEdges(nodes: ThinkingNodeType[]): Edge[] {
  return nodes.slice(1).map((node, index) => ({
    id: `e-${nodes[index].id}-${node.id}`,
    source: nodes[index].id,
    target: node.id,
    type: 'straight',
    animated: nodes[index].status === 'selected'
  }));
}
```

### 7.2 Execution Blueprint Edges
```typescript
function generateExecutionEdges(steps: ExecutionStep[]): Edge[] {
  const edges: Edge[] = [];
  
  steps.forEach(step => {
    step.dependencies.forEach(depId => {
      const depStep = steps.find(s => s.id === depId);
      if (!depStep) return;
      
      const isMainPath = step.isMainPath && depStep.isMainPath;
      const isBranchEdge = !step.isMainPath || !depStep.isMainPath;
      
      edges.push({
        id: `e-${depId}-${step.id}`,
        source: depId,
        target: step.id,
        type: isMainPath ? 'straight' : 'step',
        animated: step.status === 'running',
        style: {
          stroke: isMainPath ? '#16A34A' : '#3B82F6',
          strokeWidth: isMainPath ? 5 : 4,
          strokeDasharray: isBranchEdge ? '5,3' : 'none'
        }
      });
    });
  });
  
  return edges;
}
```

## 8. Component Interface

### 8.1 ThinkingNodeComponent
```typescript
interface ThinkingNodeProps {
  data: {
    nodeId: string;
  };
}

// Features:
// - Collapsed view: Shows question + current selection
// - Expanded view: Shows options + custom input + "Re-think" button
// - Click to expand/collapse
// - Option click triggers selectThinkingOption()
```

### 8.2 ExecutionNodeComponent
```typescript
interface ExecutionNodeProps {
  data: {
    stepId: string;
  };
}

// Features:
// - Collapsed view: Shows step name + status badge
// - Expanded view: Shows details + progress + result + "Re-plan" button
// - Status colors: pending(gray) | running(blue) | completed(green) | failed(red)
// - Main/Branch badge
// - Convergence indicator
```

### 8.3 SettingsPanel
```typescript
interface SettingsPanelProps {
  // No props - uses store directly
}

// Features:
// - Sliders for all CanvasConfig properties
// - Real-time preview (updates store on change)
// - Background style selector
// - Reset to defaults button
```

## 9. Mock Data Generation

### 9.1 Thinking Node Generator
```typescript
function generateThinkingNode(
  index: number, 
  customQuestion?: string
): ThinkingNodeType {
  const questions = [
    'What type of trip do you want?',
    'Where do you plan to go?',
    'When do you plan to depart?'
  ];
  
  const defaultOptions = [
    [
      { id: 'A', label: 'Nature', description: 'Mountains, forests, outdoor', confidence: 0.85 },
      { id: 'B', label: 'City', description: 'Architecture, food, culture', confidence: 0.78 },
      { id: 'C', label: 'Relaxation', description: 'Hot springs, beaches, slow life', confidence: 0.72 },
    ],
    // ... more options
  ];
  
  const interventionOptions = [
    { id: 'A', label: 'Adjust current step', description: 'Modify execution strategy', confidence: 0.85 },
    { id: 'B', label: 'Add branch steps', description: 'Execute additional tasks', confidence: 0.78 },
    { id: 'C', label: 'Skip current step', description: 'Proceed to next', confidence: 0.72 },
    { id: 'D', label: 'Complete re-plan', description: 'Redesign based on results', confidence: 0.80 },
  ];
  
  return {
    id: `thinking_${String(index).padStart(3, '0')}`,
    question: customQuestion || questions[index % questions.length],
    options: customQuestion ? interventionOptions : defaultOptions[index % defaultOptions.length],
    allowCustom: true,
    status: 'pending'
  };
}
```

### 9.2 Execution Blueprint Generator
```typescript
function generateExecutionBlueprint(spacing: number = 140): ExecutionStep[] {
  // Returns 9 steps:
  // - 3 main path steps (step_001 to step_003)
  // - 3 branch steps (branch_01 to branch_03)
  // - 3 post-convergence steps (step_004 to step_006)
  
  // Layout:
  // step_001 -> step_002 -> step_003 -> step_004 -> step_005 -> step_006
  //                          |           ^
  //                          ├-> branch_01 ┘
  //                          ├-> branch_02 ┘
  //                          └-> branch_03 ┘
}
```

## 10. Event Handling

### 10.1 Node Click
```typescript
// Thinking node click
onNodeClick: (node) => {
  selectThinkingNode(node.id);
  toggleNodeExpanded(node.id);
}

// Execution node click
onNodeClick: (node) => {
  selectExecutionStep(node.id);
  toggleNodeExpanded(node.id);
}
```

### 10.2 Intervention Button Click
```typescript
// "Re-think" button in thinking node
onReThinkClick: () => {
  // Allow re-selection if in thinking phase
}

// "Re-plan" button in execution node
onRePlanClick: () => {
  interveneExecution(stepId);
}
```

## 11. Configuration Update Flow

```typescript
// When user adjusts spacing slider
updateCanvasConfig({ executionNodeSpacing: newValue });

// Store automatically:
// 1. Updates config
// 2. Calls regenerateExecutionPositions()
// 3. Updates all step positions
// 4. ReactFlow re-renders with new positions
```

## 12. State Persistence

Currently, state is NOT persisted. All state is in-memory and resets on page reload.

To add persistence:
```typescript
// In store initialization
const persistedState = localStorage.getItem('blueclaw-state');
if (persistedState) {
  return JSON.parse(persistedState);
}

// In state updates
subscribe((state) => {
  localStorage.setItem('blueclaw-state', JSON.stringify(state));
});
```

---

## Appendix: File Structure

```
/src
├── components/
│   ├── BlueprintCanvas.tsx      # Main canvas container
│   ├── InputScreen.tsx          # Initial input screen
│   ├── nodes/
│   │   ├── ThinkingNode.tsx     # Thinking node component
│   │   ├── ExecutionNode.tsx    # Execution node component
│   │   └── SummaryNode.tsx      # Summary node component
│   └── panels/
│       ├── SettingsPanel.tsx    # Settings panel
│       ├── DetailPanel.tsx      # Detail panel (deprecated)
│       └── InterventionPanel.tsx # Intervention modal
├── store/
│   └── useBlueprintStore.ts     # Zustand store
├── types/
│   └── index.ts                 # Type definitions
├── mock/
│   └── mockEngine.ts            # Mock data generators
└── lib/
    └── utils.ts                 # Utility functions
```
