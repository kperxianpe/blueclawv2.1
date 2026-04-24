# Blueclaw AI Canvas - AI Integration Guide

## Quick Reference for AI Agents

### Core Store Actions

```typescript
import { useBlueprintStore } from '@/store/useBlueprintStore';

const store = useBlueprintStore.getState();
```

#### Start a Task
```typescript
// 1. Set user input
store.setUserInput("规划杭州2日游");

// 2. Start thinking phase
store.startThinking();
// Automatically generates first thinking node
```

#### Make a Choice in Thinking Phase
```typescript
// Select an option (A/B/C/D)
store.selectThinkingOption('thinking_001', 'A');

// Or provide custom input
store.setCustomInput('thinking_001', '自定义需求');

// After last node, automatically transitions to execution
```

#### Monitor Execution
```typescript
// Get current execution state
const { executionSteps, phase } = useBlueprintStore();

// Check step status
const pendingSteps = executionSteps.filter(s => s.status === 'pending');
const runningSteps = executionSteps.filter(s => s.status === 'running');
const completedSteps = executionSteps.filter(s => s.status === 'completed');
```

#### Trigger Intervention
```typescript
// From any execution step, trigger re-planning
store.interveneExecution('step_003');

// This will:
// 1. Archive completed steps
// 2. Generate intervention thinking node
// 3. Switch back to thinking phase
```

### State Shape

```typescript
interface BlueprintState {
  phase: 'input' | 'thinking' | 'execution' | 'completed';
  userInput: string;
  thinkingNodes: Array<{
    id: string;
    question: string;
    options: Array<{
      id: string;
      label: string;
      description: string;
      confidence: number;
    }>;
    status: 'pending' | 'selected';
    selectedOption?: string;
    customInput?: string;
  }>;
  executionSteps: Array<{
    id: string;
    name: string;
    description: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    dependencies: string[];
    result?: string;
    error?: string;
    isMainPath: boolean;
    isConvergence?: boolean;
  }>;
  canvasConfig: {
    leftRightRatio: number;
    execTopBottomRatio: number;
    thinkingNodeSpacing: number;
    executionNodeSpacing: number;
    thinkingCanvasZoom: number;
    executionCanvasZoom: number;
    canvasBackground: 'gradient' | 'solid' | 'grid' | 'dots';
    backgroundColor: string;
  };
}
```

### Execution Flow Algorithm

```
1. User Input → startThinking()
   ↓
2. Generate thinking nodes sequentially
   ↓
3. User makes choices → selectThinkingOption()
   ↓
4. After last node → completeThinking()
   ↓
5. Generate execution blueprint
   ↓
6. executeNextStep() - recursive execution
   ↓
7. All completed → phase = 'completed'
```

### Intervention Flow

```
1. User clicks "Re-plan" on execution step
   ↓
2. interveneExecution(stepId)
   ↓
3. Archive steps up to stepId
   ↓
4. Generate intervention thinking node
   ↓
5. phase = 'thinking'
   ↓
6. User makes new choices
   ↓
7. Generate new execution blueprint
   ↓
8. Continue execution
```

### Node Positioning Rules

**Thinking Blueprint:**
- Vertical layout
- Fixed X: 150
- Y: index * spacing

**Execution Blueprint:**
- Main path: Horizontal at Y=80
- Branches: Vertical from step_003 position
- Convergence: Back to main path Y=80

### Edge Styling

| Edge Type | Color | Width | Style |
|-----------|-------|-------|-------|
| Main path | Green (#16A34A) | 5px | Solid |
| Branch | Blue (#3B82F6) | 4px | Dashed |
| Active | Animated | - | Flowing |

### Mock Data API

```typescript
import { generateThinkingNode, generateExecutionBlueprint } from '@/mock/mockEngine';

// Generate a thinking node
const node = generateThinkingNode(0, optionalCustomQuestion);

// Generate execution blueprint
const steps = generateExecutionBlueprint(nodeSpacing);
// Returns 9 steps with proper dependencies and positions
```

### Configuration Update

```typescript
// Update any config value
store.updateCanvasConfig({
  executionNodeSpacing: 160,  // Changes all node positions
  leftRightRatio: 2.5,        // Changes panel widths
  canvasBackground: 'grid'    // Changes background style
});

// Reset to defaults
store.resetCanvasConfig();
```

### Reset Application

```typescript
// Reset entire state
store.reset();
// Returns to input phase with empty state
```

---

## Common Integration Patterns

### Pattern 1: Auto-execute After Thinking
```typescript
// After user completes all thinking nodes
useEffect(() => {
  if (phase === 'thinking' && allNodesSelected()) {
    store.completeThinking();
  }
}, [thinkingNodes]);
```

### Pattern 2: Monitor Execution Progress
```typescript
// Track execution progress
const progress = useMemo(() => {
  const total = executionSteps.length;
  const completed = executionSteps.filter(s => s.status === 'completed').length;
  return Math.round((completed / total) * 100);
}, [executionSteps]);
```

### Pattern 3: Dynamic Node Spacing
```typescript
// Adjust spacing based on node count
useEffect(() => {
  const nodeCount = executionSteps.length;
  const optimalSpacing = Math.min(200, Math.max(100, 800 / nodeCount));
  store.updateCanvasConfig({ executionNodeSpacing: optimalSpacing });
}, [executionSteps.length]);
```
