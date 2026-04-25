# Blueclaw AI - AdapterViser 接口文档

## 1. 模块定位

**AdapterViser** 是 Blueclaw AI 画布系统右下区域的"浏览器式标签页容器"，类似于 Chrome/Edge 的多标签页切换系统。它承载任务执行过程中的所有可视化工具（画布/Web/IDE），并支持动态创建新的自定义标签页。

```
+-------------------------------------------------------------+
|  左:思考蓝图  |  中:工具栏  |  右:执行区域                    |
|              |            |  +---------------------------+  |
|              |            |  |     执行蓝图(上)           |  |
|              |            |  +---------------------------+  |
|              |            |  | 画布 | Web | IDE | + |      |  |  <- AdapterViser
|              |            |  +---------------------------+  |
|              |            |  |                           |  |  <- 标签页内容区
|              |            |  |  (画布/Web/IDE/Adapter)    |  |
|              |            |  |                           |  |
|              |            |  +---------------------------+  |
+-------------------------------------------------------------+
```

---

## 2. 文件清单与路径

| 文件 | 路径 | 职责 |
|------|------|------|
| **VisualAdapter.tsx** | `src/components/visual/VisualAdapter.tsx` | 主容器组件，管理标签页切换 |
| **WebBrowser.tsx** | `src/components/visual/WebBrowser.tsx` | Web浏览器模拟标签页 |
| **IDE.tsx** | `src/components/visual/IDE.tsx` | VSCode IDE模拟标签页 |
| **AdapterDefault.tsx** | `src/components/visual/AdapterDefault.tsx` | 默认Adapter(任务进度)标签页 |
| **ToolDock.tsx** | `src/components/visual/ToolDock.tsx` | 中间工具栏(黄色方块) |
| **ToolEditor.tsx** | `src/components/visual/ToolEditor.tsx` | 工具编辑器弹窗 |
| **BlueprintCanvas.tsx** | `src/components/BlueprintCanvas.tsx` | 主画布(引用VisualAdapter) |

---

## 3. 类型定义

### 3.1 TabType - 标签页类型

```typescript
export type TabType = 'canvas' | 'web' | 'ide' | 'default';
```

| 类型值 | 含义 | 对应组件 |
|--------|------|----------|
| `'canvas'` | 可视化画布(ReactFlow) | `CanvasPage` 内部组件 |
| `'web'` | Web浏览器模拟 | `WebBrowser` |
| `'ide'` | IDE编辑器模拟 | `IDE` |
| `'default'` | 默认Adapter(任务进度) | `AdapterDefault` |

### 3.2 TabInfo - 标签页数据结构

```typescript
export interface TabInfo {
  id: string;       // 唯一标识, 固定标签: 'canvas'/'web'/'ide', 新建: 'tab-<timestamp>'
  label: string;    // 显示名称, 如 "画布"/"Web"/"IDE"/"任务监控"
  type: TabType;    // 标签页类型, 决定渲染哪个组件
  closable: boolean; // 是否可关闭(固定标签false, 新建标签true)
}
```

### 3.3 ToolItem - 工具项(黄色方块数据)

```typescript
export interface ToolItem {
  id: string;           // 唯一ID, 如 "mcp-1", "skill-1"
  name: string;         // 显示名称, 如 "Web Search"
  icon: LucideIcon;     // Lucide图标组件
  color: string;        // 背景色(hex), 如 "#F59E0B"
  description: string;  // 描述文本
  type: 'mcp' | 'skill' | 'setting' | 'file';  // 工具分类
  content?: string;     // 可选内容/配置
}
```

### 3.4 VisualAdapterProps - 主组件入口Props

```typescript
interface VisualAdapterProps {
  droppedItems: ToolItem[];                              // 已拖入的项目列表
  onItemUse?: (item: ToolItem, target: 'thinking' | 'execution') => void;  // 工具使用回调
  onEdit?: (item: ToolItem) => void;                     // 编辑工具回调(打开编辑器)
}
```

---

## 4. 如何引用/使用

### 4.1 在 BlueprintCanvas 中引用

```typescript
// BlueprintCanvas.tsx 第24行
import { VisualAdapter } from './visual/VisualAdapter';

// BlueprintCanvas.tsx 第505-509行 - 使用方式
<VisualAdapter
  droppedItems={visualDroppedItems}   // 已拖入工具列表
  onItemUse={handleToolUse}           // 工具使用回调
  onEdit={handleEditTool}             // 编辑工具回调 -> 打开ToolEditor弹窗
/>
```

### 4.2 独立引用各子组件

```typescript
// 引用Web浏览器
import { WebBrowser } from './components/visual/WebBrowser';

// 引用IDE
import { IDE } from './components/visual/IDE';

// 引用默认Adapter(任务进度面板)
import { AdapterDefault } from './components/visual/AdapterDefault';

// 这三个组件都是零Props，可直接使用:
// <WebBrowser />
// <IDE />
// <AdapterDefault />
```

### 4.3 子组件导出方式

| 组件 | 导出类型 | Props | 说明 |
|------|----------|-------|------|
| `VisualAdapter` | 命名导出 `export function` | `VisualAdapterProps` | 主容器，必用 |
| `WebBrowser` | 命名导出 `export function` | 无 | Web浏览器标签页 |
| `IDE` | 命名导出 `export function` | 无 | IDE编辑器标签页 |
| `AdapterDefault` | 命名导出 `export function` | 无 | 默认Adapter标签页 |
| `TabType` | 类型导出 `export type` | - | 标签页类型联合类型 |
| `TabInfo` | 接口导出 `export interface` | - | 标签页数据结构 |

---

## 5. 标签页路由映射

VisualAdapter 内部通过 `activeTab.type` 决定渲染哪个组件：

```typescript
// VisualAdapter.tsx 第362-387行 renderTabContent()
switch (activeTab.type) {
  case 'canvas':   return <CanvasPage ... />;   // ReactFlow画布 + 拖放
  case 'web':      return <WebBrowser />;        // 模拟Edge浏览器
  case 'ide':      return <IDE />;               // 模拟VSCode
  case 'default':  return <AdapterDefault />;    // 任务进度面板
}
```

---

## 6. 各子组件功能详解

### 6.1 VisualAdapter (主容器)

**位置**: `src/components/visual/VisualAdapter.tsx`

**内部状态**:
```typescript
const [tabs, setTabs] = useState<TabInfo[]>([    // 标签页列表
  { id: 'canvas', label: '画布', type: 'canvas', closable: false },
  { id: 'web',    label: 'Web',  type: 'web',    closable: false },
  { id: 'ide',    label: 'IDE',  type: 'ide',    closable: false },
]);
const [activeTabId, setActiveTabId] = useState('canvas');  // 当前激活标签
const [showNewTabDialog, setShowNewTabDialog] = useState(false); // 新建对话框

// ReactFlow画布状态(仅canvas标签使用)
const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
const [edges, , onEdgesChange] = useEdgesState<Edge>([]);
```

**已实现功能**:
- [x] 顶部标签栏展示所有标签页
- [x] 点击标签切换内容
- [x] 固定标签(画布/Web/IDE)不可关闭
- [x] 新建标签(+号按钮)弹出对话框
- [x] 新建标签可关闭(鼠标悬停显示×)
- [x] 关闭标签后自动切换到上一个标签
- [x] Canvas标签页支持ReactFlow画布渲染
- [x] Canvas标签页支持拖拽接收ToolItem
- [x] 拖拽接收后在画布上创建节点
- [x] 拖拽后自动打开ToolEditor编辑器
- [x] 空状态提示(画布无节点时)

**接口函数**:
```typescript
// 创建新标签页(内部回调)
const handleCreateTab = (name: string, type: TabType) => { ... }

// 关闭标签页(内部回调)
const handleCloseTab = (tabId: string) => { ... }

// 拖放处理(仅canvas标签有效)
const handleDrop = (e: React.DragEvent) => { ... }
```

---

### 6.2 WebBrowser (Web浏览器模拟)

**位置**: `src/components/visual/WebBrowser.tsx`

**内部状态**:
```typescript
const [url, setUrl] = useState('https://www.bing.com');         // 当前URL
const [displayUrl, setDisplayUrl] = useState('https://www.bing.com'); // 地址栏显示
const [isLoading, setIsLoading] = useState(false);                // 加载状态
const [history, setHistory] = useState<string[]>(['https://www.bing.com']); // 历史记录
const [historyIndex, setHistoryIndex] = useState(0);              // 当前历史索引
```

**已实现功能**:
- [x] 地址栏显示当前URL(带锁图标)
- [x] 后退/前进导航按钮(带禁用状态)
- [x] 刷新按钮(带动画)
- [x] Home按钮(返回Bing)
- [x] 地址栏输入新URL按Enter导航
- [x] URL自动补全https前缀
- [x] 加载动画(spinner)
- [x] Bing首页模拟(Logo+搜索框+分类按钮)
- [x] 通用网页模拟(访问非Bing URL)
- [x] 底部状态栏

**未实现功能(仅前端样子)**:
- [ ] 真实网络请求(无法真正访问网页)
- [ ] 收藏夹/书签系统(Star按钮仅UI)
- [ ] Cookie/Session管理
- [ ] 开发者工具
- [ ] 下载管理

---

### 6.3 IDE (VSCode编辑器模拟)

**位置**: `src/components/visual/IDE.tsx`

**内部状态**:
```typescript
const [files, setFiles] = useState<FileItem[]>(DEFAULT_FILES);  // 文件树数据
const [openTabs, setOpenTabs] = useState<string[]>(['app.tsx']); // 打开的文件标签
const [activeTab, setActiveTab] = useState('app.tsx');           // 当前编辑文件
const [sidebarVisible, setSidebarVisible] = useState(true);      // 侧边栏显隐
const [terminalVisible, setTerminalVisible] = useState(true);    // 终端显隐
const [terminalOutput, setTerminalOutput] = useState<string[]>([...]); // 终端输出
const [isRunning, setIsRunning] = useState(true);                // 运行状态
```

**默认文件树**:
```
src/
  components/
    App.tsx      (TSX)
    Header.tsx   (TSX)
  main.tsx       (TSX)
  styles.css     (CSS)
package.json     (JSON)
tsconfig.json    (JSON)
```

**已实现功能**:
- [x] VSCode风格深色主题(#1e1e1e)
- [x] 顶部工具栏(运行/停止/调试/搜索/Git/插件/设置)
- [x] 左侧文件树(Explorer面板，支持展开/折叠文件夹)
- [x] 文件树图标颜色(按语言区分: TSX蓝色/JS黄色/CSS蓝色/JSON绿色)
- [x] 点击文件打开编辑器标签
- [x] 编辑器标签栏(带关闭按钮×，当前标签高亮)
- [x] 行号显示
- [x] 代码内容展示(预置React组件代码)
- [x] 底部终端(模拟npm run dev输出)
- [x] 终端输出带颜色($绿色/✓绿色/➜青色)
- [x] 终端输入提示符(闪烁光标)
- [x] 底部蓝色状态栏(TSX/UTF-8/Prettier/Ln Col/Spaces:2)
- [x] 侧边栏显隐切换
- [x] 终端显隐切换

**接口函数**:
```typescript
// 运行代码(模拟)
const runCode = () => { ... }   // 向终端追加 build 输出

// 停止代码(模拟)
const stopCode = () => { ... }  // 向终端追加 ^C 终止输出
```

**未实现功能(仅前端样子)**:
- [ ] 真实代码编辑(只读展示)
- [ ] 语法高亮(使用pre>code，无高亮)
- [ ] 文件系统操作(创建/删除/重命名)
- [ ] IntelliSense/自动补全
- [ ] 真实代码运行(仅模拟输出)
- [ ] Git版本控制(仅按钮)
- [ ] 插件系统(仅按钮)
- [ ] 调试功能(仅按钮)

---

### 6.4 AdapterDefault (默认Adapter - 任务进度面板)

**位置**: `src/components/visual/AdapterDefault.tsx`

**数据结构**:
```typescript
interface TaskInfo {
  id: string;       // 任务ID
  title: string;    // 标题
  description: string;  // 描述
  status: 'pending' | 'running' | 'completed' | 'error';  // 状态
  progress: number; // 进度 0-100
  type: 'thinking' | 'execution' | 'web' | 'ide';  // 任务类型
  timestamp: string; // 时间戳
}
```

**默认任务数据**(5条模拟数据):
| ID | 标题 | 状态 | 进度 | 类型 |
|----|------|------|------|------|
| 1 | 任务理解与目标分析 | completed | 100% | thinking |
| 2 | 思考蓝图构建 | completed | 100% | thinking |
| 3 | 执行蓝图生成 | running | 65% | execution |
| 4 | Web搜索-技术方案调研 | running | 40% | web |
| 5 | 代码生成-前端组件开发 | pending | 0% | ide |

**已实现功能**:
- [x] 顶部4张统计卡片(总进度/已完成/执行中/待执行)
- [x] 总进度条(动态计算平均值)
- [x] 任务列表(5条默认数据)
- [x] 每条任务显示: 状态图标/标题/状态标签/描述/类型图标/进度条
- [x] 任务可展开/折叠(点击显示详情)
- [x] 展开详情: 任务ID/时间戳/类型/状态/模拟输出
- [x] 状态颜色区分(完成=绿/执行中=黄/待执行=灰/出错=红)
- [x] 底部"任务记忆摘要"面板
- [x] 响应式布局(overflow-auto)

**未实现功能**:
- [ ] 真实任务数据绑定(当前是静态DEFAULT_TASKS)
- [ ] 与执行蓝图的实时同步
- [ ] 任务状态自动更新
- [ ] 真实时间戳更新

---

### 6.5 NewTabDialog (新建标签页对话框)

**位置**: `VisualAdapter.tsx` 内部组件(第87-205行)

**Props**:
```typescript
interface NewTabDialogProps {
  isOpen: boolean;                                  // 是否显示
  onClose: () => void;                              // 关闭回调
  onCreate: (name: string, type: TabType) => void;  // 创建回调
}
```

**已实现功能**:
- [x] 遮罩层+弹窗(backdrop-blur)
- [x] 名称输入框(必填，Enter提交)
- [x] 4种类型选择网格(单选)
- [x] 类型选中高亮(蓝色边框+背景)
- [x] 取消/创建按钮
- [x] 空名称时创建按钮禁用

---

## 7. 拖放数据流

```
ToolDock(黄色方块)
  ├── onDragStart: 将 ToolItem JSON 序列化到 dataTransfer
  │     e.dataTransfer.setData('application/json', JSON.stringify(item))
  │     e.dataTransfer.setData('text/plain', JSON.stringify(item))
  │
  ▼ 拖拽到 vis 区域
VisualAdapter.CanvasPage
  ├── onDragOver: 允许放置
  ├── onDrop: 解析 ToolItem
  │     1. 创建 ReactFlow 节点
  │     2. 调用 onEdit(item) 打开 ToolEditor
  │
  ▼
BlueprintCanvas.handleEditTool
  └── setShowToolEditor(true) 打开编辑器弹窗
```

**拖拽数据格式**:
```typescript
// 设置( ToolDock.tsx 第71-74行 )
e.dataTransfer.setData('application/json', itemData);
e.dataTransfer.setData('text/plain', itemData);

// 读取( VisualAdapter.tsx 第291-299行 )
let data = e.dataTransfer.getData('application/json');
if (!data) data = e.dataTransfer.getData('text/plain');
const item: ToolItem = JSON.parse(data);
```

---

## 8. 现有功能清单

### 8.1 已实现

| 模块 | 功能 | 说明 |
|------|------|------|
| 标签系统 | 多标签页切换 | 画布/Web/IDE/自定义 |
| 标签系统 | 新建标签页 | +号按钮+对话框 |
| 标签系统 | 关闭标签页 | 仅自定义标签可关闭 |
| 标签系统 | 标签图标 | 按类型显示不同Lucide图标 |
| 画布 | ReactFlow画布 | 支持节点渲染和缩放 |
| 画布 | 拖放接收 | 接收ToolDock黄色方块 |
| 画布 | 节点创建 | 拖放后自动创建节点 |
| 画布 | 空状态提示 | 无节点时显示提示 |
| Web浏览器 | 地址栏 | 显示/编辑URL |
| Web浏览器 | 导航按钮 | 后退/前进/刷新/Home |
| Web浏览器 | 历史记录 | 记录访问历史 |
| Web浏览器 | 加载动画 | 转圈+文字提示 |
| Web浏览器 | Bing首页 | Logo+搜索框+分类 |
| Web浏览器 | 通用网页 | 非Bing URL显示骨架屏 |
| Web浏览器 | 底部状态栏 | 加载状态+Edge标识 |
| IDE | VSCode主题 | 深色主题+蓝色状态栏 |
| IDE | 文件树 | 文件夹展开/折叠+文件图标 |
| IDE | 编辑器 | 行号+代码展示+标签栏 |
| IDE | 终端 | 模拟npm输出+颜色+闪烁光标 |
| IDE | 工具栏 | 运行/停止/调试/搜索/Git/插件 |
| IDE | 状态栏 | 语言/编码/Prettier/行列/缩进 |
| IDE | 面板控制 | 侧边栏/终端显隐切换 |
| Adapter | 统计卡片 | 总进度/已完成/执行中/待执行 |
| Adapter | 任务列表 | 5条模拟数据+进度条+状态 |
| Adapter | 任务详情 | 展开显示ID/时间/类型/状态/输出 |
| Adapter | 记忆摘要 | 底部固定摘要文本 |

### 8.2 未实现(仅前端渲染)

| 模块 | 缺失功能 | 说明 |
|------|----------|------|
| 全局 | 真实后端通信 | 所有数据均为前端静态模拟 |
| 全局 | 数据持久化 | 刷新页面数据丢失 |
| Web | 真实网页加载 | 无法真正访问互联网 |
| Web | 书签/历史管理 | 仅基础历史记录 |
| IDE | 代码编辑 | 只读展示，无法修改 |
| IDE | 语法高亮 | 纯文本展示 |
| IDE | 真实代码运行 | 仅模拟终端输出 |
| IDE | 文件操作 | 无法增删改文件 |
| IDE | Git功能 | 仅按钮，无实际功能 |
| Adapter | 真实数据绑定 | 静态模拟数据 |
| Adapter | 自动状态更新 | 不会随执行蓝图变化 |
| 画布 | 节点连线 | 拖放节点间无自动连线 |
| 画布 | 节点编辑 | 双击节点无编辑功能 |

---

## 9. 与外部系统接口

### 9.1 入口 Props

VisualAdapter 作为右下区域的容器，通过以下 Props 与外部交互：

```typescript
interface VisualAdapterProps {
  // 已拖入的项目列表(从BlueprintCanvas传递)
  droppedItems: ToolItem[];
  
  // 工具使用回调(点击"用于思考蓝图"/"用于执行蓝图"时触发)
  onItemUse?: (item: ToolItem, target: 'thinking' | 'execution') => void;
  
  // 编辑工具回调(拖拽后或点击节点时触发，打开ToolEditor)
  onEdit?: (item: ToolItem) => void;
}
```

### 9.2 BlueprintCanvas 中的集成

```typescript
// 状态传递(BlueprintCanvas.tsx)
const [visualDroppedItems, setVisualDroppedItems] = useState<ToolItem[]>([]);

// 拖拽处理
const handleVisualDrop = useCallback((item: ToolItem) => {
  setVisualDroppedItems(prev => {
    if (prev.find(i => i.id === item.id)) return prev;
    return [...prev, item];
  });
}, []);

// 编辑处理(打开ToolEditor)
const handleEditTool = useCallback((item: ToolItem) => {
  setEditingTool(item);
  setShowToolEditor(true);
}, []);

// JSX中使用
<VisualAdapter
  droppedItems={visualDroppedItems}
  onItemUse={handleToolUse}
  onEdit={handleEditTool}
/>
```

### 9.3 推荐的扩展接口

如需将 AdapterDefault 接入真实数据，建议：

```typescript
// AdapterDefault 扩展 Props
interface AdapterDefaultProps {
  tasks?: TaskInfo[];           // 从外部传入真实任务数据
  memory?: string[];            // 任务记忆摘要
  onTaskClick?: (taskId: string) => void;  // 点击任务回调
  onTaskAction?: (taskId: string, action: 'run' | 'pause' | 'stop') => void;
}

// WebBrowser 扩展 Props
interface WebBrowserProps {
  initialUrl?: string;          // 初始URL
  onNavigate?: (url: string) => void;  // 导航回调(可触发外部搜索)
}

// IDE 扩展 Props
interface IDEProps {
  files?: FileItem[];           // 外部传入文件树
  onFileOpen?: (fileId: string) => void;
  onCodeRun?: (fileId: string) => void;
  terminalOutput?: string[];    // 外部传入终端输出
}
```

---

## 10. 样式系统

| 模块 | 主背景色 | 主题 |
|------|----------|------|
| VisualAdapter 容器 | `bg-slate-900` | 深色 |
| 标签栏 | `bg-slate-800/90` | 深色半透明 |
| WebBrowser | `bg-slate-900` + `bg-white`内容区 | 深色+浅色 |
| IDE | `bg-[#1e1e1e]` | VSCode深色 |
| IDE状态栏 | `bg-[#007acc]` | VSCode蓝色 |
| AdapterDefault | `bg-slate-900` | 深色 |
| 弹窗 | `bg-slate-800` + `backdrop-blur` | 毛玻璃 |

---

## 11. 完整系统架构（三栏布局）

### 11.1 布局结构图

```
+=================================================================================+
|  Blueclaw AI - Self-Executing Blueprint Canvas                                  |
+=================================================================================+
|                                                                                 |
|  +------------------------+  +--------+  +-----------------------------------+  |
|  |     思考蓝图 (左)       |  | 工具栏  |  |        执行区域 (右)             |  |
|  |                        |  |        |  |  +---------------------------+  |  |
|  |  ReactFlow画布          |  |  设置  |  |  |     执行蓝图 (上)          |  |  |
|  |  - 思考节点(可展开)      |  |  搜索  |  |  |  ReactFlow画布              |  |  |
|  |  - 四选一选项           |  |  +号   |  |  |  - 执行节点(主/支路径)      |  |  |
|  |  - 自定义输入框         |  |        |  |  |  - 汇合节点                 |  |  |
|  |  - 重新思考按钮(红)     |  |  MCP   |  |  |  - 重新规划按钮(红)        |  |  |
|  |  - 蓝色Handle连线       |  |  Skill |  |  |  - 绿色Handle连线           |  |  |
|  |  比例: 1/(1+√5)        |  |  File  |  |  +---------------------------+  |  |
|  |                        |  |        |  |  +---------------------------+  |  |
|  |                        |  |  黄色  |  |  |    AdapterViser (下)       |  |  |
|  |                        |  |  方块  |  |  |  [画布|Web|IDE|+][x]      |  |  |
|  |                        |  |  可拖拽 |  |  |  标签页内容区域             |  |  |
|  |                        |  +--------+  |  |  - 画布(拖放区)             |  |  |
|  |                        |              |  |  - Web浏览器(模拟Edge)      |  |  |
|  |                        |              |  |  - IDE(模拟VSCode)          |  |  |
|  |                        |              |  |  - Adapter(任务进度)        |  |  |
|  +------------------------+              |  +---------------------------+  |  |
|                                          |                                   |  |
|  比例: leftRightRatio=√5 (~2.236)        |  execTopBottomRatio=2 (1:2)     |  |
|                                          |                                   |  |
+=================================================================================+
|  SettingsPanel (config.json - Unity风格折叠面板)                                |
|  左右比例 | 执行区域比例 | 思考缩放 | 执行缩放 | 思考间距 | 执行间距 | 背景样式   |
+=================================================================================+
|  InterventionPanel (干预弹窗 - 红色Alert风格)                                   |
|  继续执行 | 生成新分支 | 完全停止                                                |
+=================================================================================+
|  ToolEditor (工具编辑弹窗)                                                      |
|  类型(MCP/Skill/File) | 名称 | 描述 | 颜色 | 内容/配置                             |
+=================================================================================+
```

### 11.2 比例参数系统

所有比例通过 `CanvasConfig` 统一配置，在 `SettingsPanel` 中可视化调节：

| 参数 | 默认值 | 范围 | 作用 |
|------|--------|------|------|
| `leftRightRatio` | 2.236 (√5) | 1~5 | 左(思考) : 右(执行) = 1 : ratio |
| `execTopBottomRatio` | 2 | 0.5~4 | 执行蓝图(上) : AdapterViser(下) = 1 : ratio |
| `thinkingCanvasZoom` | 1 | 0.3~2 | 思考蓝图初始缩放 |
| `executionCanvasZoom` | 1 | 0.3~2 | 执行蓝图初始缩放 |
| `thinkingNodeSpacing` | 180px | 100~300 | 思考节点垂直间距 |
| `executionNodeSpacing` | 140px | 80~250 | 执行节点统一间距 |
| `canvasBackground` | 'gradient' | gradient/solid/grid/dots | 画布背景样式 |

---

## 12. 左侧：思考蓝图 (Thinking Blueprint)

### 12.1 组件信息

| 属性 | 值 |
|------|-----|
| **组件** | `ThinkingNodeComponent` |
| **文件** | `src/components/nodes/ThinkingNode.tsx` (246行) |
| **注册位置** | `BlueprintCanvas.tsx` 第40行: `thinkingNode: ThinkingNodeComponent` |
| **画布容器** | `BlueprintCanvas.tsx` 左侧 `ReactFlow` (fitView+minZoom+maxZoom) |
| **背景** | `bg-slate-900` 深蓝渐变 |

### 12.2 数据结构

```typescript
// src/types/index.ts 第3-18行
interface ThinkingOption {
  id: string;         // 选项ID: 'A'/'B'/'C'
  label: string;      // 选项名称: '自然风光'
  description: string; // 选项描述
  confidence: number;  // 置信度 0~1
  isDefault?: boolean; // 是否推荐(带Sparkles图标)
}

interface ThinkingNodeType {
  id: string;         // 节点ID: 'thinking_001'
  question: string;   // 问题文本: '你想规划什么样的旅行？'
  options: ThinkingOption[];  // 4个选项(含自定义)
  allowCustom: boolean;       // 是否允许自定义输入
  status: 'pending' | 'selected';  // 节点状态
  selectedOption?: string;    // 已选选项ID
  customInput?: string;       // 自定义输入内容
}
```

### 12.3 节点UI结构

```
+------------------+  <- 蓝色/灰色顶部Handle (target)
| [脑] 问题标题    |  <- 概览行(Brain图标+question+状态)
|     选择概览     |     点击展开/折叠
+------------------+
| 思考节点 #001    |  <- 展开后:
| [重新思考] 红色  |     节点编号 + 红色干预按钮
+------------------+
| A. 自然风光      |  <- 选项列表(蓝色编号+名称+描述)
|    山水户外活动  |     点击选择
| B. 城市探索      |
| C. 休闲度假      |
| 其他...  虚线框  |  <- 自定义输入开关
| [输入框][确认]   |  <- 自定义输入+确认/取消
+------------------+
| [selected内容]   |  <- 已选状态: 显示选择结果
+------------------+
   [蓝色底部Handle]  <- source Handle
```

### 12.4 已实现功能

- [x] 概览行显示：Brain图标 + 问题文本 + 选择状态概览 + Chevron展开按钮
- [x] 点击展开/折叠详情
- [x] 四个选项按钮(A/B/C + 自定义)，带编号和描述
- [x] 推荐选项标记(Sparkles黄色图标)
- [x] 自定义输入框（展开"其他..."后显示）
- [x] 自定义输入确认/取消按钮
- [x] 红色"重新思考"按钮（仅pending+thinking阶段可用）
- [x] 已选状态显示（展示选择结果）
- [x] 顶部target Handle（蓝色，10px圆形）
- [x] 底部source Handle（蓝色，10px圆形）
- [x] 选中高亮（蓝色边框+ring+shadow）
- [x] 完成状态（蓝色背景bg-blue-50）

### 12.5 交互事件流

```
用户点击选项
  → handleOptionClick(optionId)
    → selectThinkingOption(nodeId, optionId) (Zustand action)
      → 更新节点status='selected'
      → 如果不是最后节点(索引<2):
          → generateThinkingNode(index+1) 生成下一节点
          → 添加到thinkingNodes数组
      → 如果是最后节点:
          → completeThinking() 转入执行阶段

用户点击"重新思考"
  → 红色按钮(仅thinking阶段+pending状态可用)
  → 可重新选择其他选项

用户展开自定义输入
  → setShowCustomInput(true)
  → 输入内容 → handleCustomSubmit()
    → setCustomInput(nodeId, input) (Zustand action)
      → 与选择选项相同的后续逻辑
```

### 12.6 生成逻辑 (Mock)

```typescript
// src/mock/mockEngine.ts 第8-51行
generateThinkingNode(index, customQuestion?)
  → 返回 ThinkingNodeType
  → 3轮固定问题(旅行规划)
  → 每轮3个选项 + 允许自定义
  → 干预模式(带customQuestion)时返回4个干预选项
```

---

## 13. 中间：工具栏 (ToolDock)

### 13.1 组件信息

| 属性 | 值 |
|------|-----|
| **组件** | `ToolDock` |
| **文件** | `src/components/visual/ToolDock.tsx` (约180行) |
| **位置** | BlueprintCanvas中间竖栏 |
| **宽度** | 64px (w-16) |

### 13.2 默认工具列表

```typescript
// 8个内置工具
[
  { id:'mcp-1',     name:'Web Search',  type:'mcp',     color:'#F59E0B', icon:Globe },
  { id:'skill-1',   name:'Image Gen',   type:'skill',   color:'#FBBF24', icon:Image },
  { id:'skill-2',   name:'Code Editor', type:'skill',   color:'#FCD34D', icon:Code2 },
  { id:'mcp-2',     name:'Data Fetch',  type:'mcp',     color:'#FDE68A', icon:Database },
  { id:'setting-1', name:'API Config',  type:'setting', color:'#10B981', icon:Settings },
  { id:'setting-2', name:'Auth Token',  type:'setting', color:'#34D399', icon:Key },
  { id:'file-1',    name:'README.md',   type:'file',    color:'#F97316', icon:FileText },
  { id:'file-2',    name:'Config JSON', type:'file',    color:'#FB923C', icon:FileCode },
]
```

### 13.3 UI结构

```
+--------+
|  设置   |  <- 蓝色设置按钮 → 打开SettingsPanel
|  (蓝)   |
+--------+
|  搜索   |  <- 蓝色搜索按钮 → 打开搜索输入框
|  (蓝)   |
+--------+
|   +    |  <- 黄色+号按钮 → 打开ToolEditor新建
|  (黄)  |
+--------+
|  分隔  |
+--------+
| [W]   |  <- 黄色方块 Web Search  (MCP)
| [I]   |  <- 黄色方块 Image Gen    (Skill)
| [C]   |  <- 黄色方块 Code Editor  (Skill)
| [D]   |  <- 黄色方块 Data Fetch   (MCP)
| [S]   |  <- 绿色方块 API Config  (Setting)
| [K]   |  <- 绿色方块 Auth Token  (Setting)
| [R]   |  <- 橙色方块 README.md   (File)
| [J]   |  <- 橙色方块 Config JSON (File)
+--------+
```

### 13.4 已实现功能

- [x] 设置按钮（蓝色，打开SettingsPanel）
- [x] 搜索按钮（蓝色，展开搜索输入框过滤工具）
- [x] 添加按钮（黄色，打开ToolEditor新建工具）
- [x] 8个内置工具显示（彩色方块+图标+名称）
- [x] 工具点击 → 打开ToolEditor编辑
- [x] 工具拖拽 → `dataTransfer.setData('application/json', itemJSON)`
- [x] 搜索过滤（按名称实时过滤工具列表）

---

## 14. 右侧上：执行蓝图 (Execution Blueprint)

### 14.1 组件信息

| 属性 | 值 |
|------|-----|
| **执行节点组件** | `ExecutionNodeComponent` |
| **文件** | `src/components/nodes/ExecutionNode.tsx` (285行) |
| **摘要节点组件** | `SummaryNodeComponent` |
| **文件** | `src/components/nodes/SummaryNode.tsx` (168行) |
| **注册位置** | `BlueprintCanvas.tsx` 第41-42行 |
| **画布容器** | `BlueprintCanvas.tsx` 右侧上区域 ReactFlow |

### 14.2 数据结构

```typescript
// src/types/index.ts 第21-35行
interface ExecutionStep {
  id: string;              // 'step_001' 或 'branch_01'
  name: string;            // 步骤名称: '查询天气'
  description: string;     // 描述
  status: 'pending' | 'running' | 'completed' | 'failed';
  dependencies: string[];  // 依赖步骤ID数组
  result?: string;         // 执行结果
  error?: string;          // 错误信息
  position: { x: number; y: number };  // 画布坐标
  needsIntervention?: boolean;  // 是否需要干预
  isMainPath?: boolean;     // 是否主路径
  isConvergence?: boolean;  // 是否汇合点
  convergenceType?: 'parallel' | 'sequential';  // 汇合类型
  isArchived?: boolean;     // 干预后已归档
}
```

### 14.3 执行节点UI结构

```
    [绿色顶部Handle]     <- target
    [绿色左侧Handle]     <- target(接收分支)
+------------------+
| [图] 主/支 名称   |  <- 概览行(状态图标+主/支标记+name)
|     状态标签       |
+------------------+
| 步骤 #003         |  <- 展开后:
| 需干预 ▲          |     步骤编号 + "需干预"警告(黄色)
| [重新规划] 红色   |     红色干预按钮
+------------------+
| 描述文本          |  <- 步骤详细描述
| [=======    ] 60%|  <- 执行中进度条(动画)
| 结果: 完成 ✓      |  <- 完成结果(绿色)
| 错误: xxx ✗       |  <- 错误信息(红色)
| 依赖: step_001    |  <- 依赖列表
+------------------+
    [绿色底部Handle]     <- source
    [绿色右侧Handle]     <- source(输出到分支)
```

### 14.4 状态配置

| 状态 | 背景 | 边框 | 图标 | 标签 | 动画 |
|------|------|------|------|------|------|
| `pending` | bg-white/95 | border-gray-300 | Circle(灰) | 待执行 | 无 |
| `running` | bg-blue-50/95 | border-blue-500 | Zap(蓝) | 执行中 | animate-pulse |
| `completed` | bg-green-50/95 | border-green-500 | CheckCircle2(绿) | 已完成 | 无 |
| `failed` | bg-red-50/95 | border-red-500 | XCircle(红) | 失败 | 无 |

### 14.5 多路径布局设计

```
step_001(查询天气) → step_002(搜索景点) → step_003(规划交通)
                                                        │
                                            ┌───────────┼───────────┐
                                            ▼           ▼           ▼
                                        branch_01   branch_02   branch_03
                                        (查询高铁)   (查询航班)   (查询自驾)
                                            └───────────┬───────────┘
                                                        ▼
                                        step_004(对比方案) ← 汇合点
                                                        │
                                        step_005(推荐酒店) → step_006(生成行程)
```

- 主路径6个节点（水平排列）
- 3个分支节点（从step_003垂直向下排列）
- step_004为汇合点（isConvergence=true，依赖3个分支）
- 统一间距由 `executionNodeSpacing` 控制（默认140px）

### 14.6 执行引擎逻辑

```typescript
// useBlueprintStore.ts 第102-184行
executeNextStep():
  1. 找可执行步骤（pending + 所有依赖completed）
  2. 优先执行主路径(mainSteps) → 再执行分支(branchSteps)
  3. 将步骤状态设为 'running'
  4. 模拟执行(2000ms):
     - step_003 固定失败(needsIntervention=true)
     - 其他步骤 completed
  5. 完成后递归调用 executeNextStep()
  6. 无pending步骤时 → 添加 summary 节点 → phase='completed'
```

### 14.7 干预机制

```
步骤失败(如step_003)
  → needsIntervention=true
  → 节点显示黄色警告"需干预"
  → 用户点击"重新规划"红色按钮
    → interveneExecution(stepId) (Zustand)
      → 保留已完成步骤(标记isArchived)
      → 回到thinking阶段
      → 生成干预思考节点(带上下文)
      → 用户重新选择 → 生成新执行蓝图
```

### 14.8 SummaryNode (执行摘要节点)

当所有步骤执行完成后自动添加：

```
+------------------+
| ✦ 任务完成 ✓     |  <- 绿色渐变头部
+------------------+
| 执行摘要          |  <- 名称
| 点击查看详情      |  <- 描述
| ✓ N 完成  ✗ M 失败|  <- 统计
+------------------+
  点击展开:
+----------------------------------+
| 📋 执行摘要                [x]  |
+----------------------------------+
| ● N 个步骤                       |
|   全部执行成功                    |
+----------------------------------+
| 1. 查询天气        ✓              |  <- 步骤列表
| 2. 搜索景点        ✓              |
| 3. 规划交通        ✓              |
| ...                               |
+----------------------------------+
| [↺ 开始新任务]                    |  <- reset() 重置全部
+----------------------------------+
```

---

## 15. 全局状态管理 (Zustand Store)

### 15.1 Store定义

```typescript
// src/store/useBlueprintStore.ts
export const useBlueprintStore = create<BlueprintState>((set, get) => ({
  // === 状态 ===
  phase: 'input',              // 当前阶段
  userInput: '',               // 用户输入
  thinkingNodes: [],           // 思考节点数组
  currentThinkingIndex: 0,     // 当前思考轮次
  selectedThinkingNodeId: null,// 选中的思考节点
  executionSteps: [],          // 执行步骤数组
  selectedExecutionStepId: null,// 选中的执行步骤
  showInterventionPanel: false,// 是否显示干预面板
  interventionStepId: null,    // 需要干预的步骤ID
  canvasConfig: defaultCanvasConfig,  // 画布配置

  // === Actions ===
  setUserInput, startThinking, selectThinkingOption,
  setCustomInput, selectThinkingNode, completeThinking,
  startExecution, executeNextStep, selectExecutionStep,
  interveneExecution, handleIntervention, hideIntervention,
  reset, updateCanvasConfig, resetCanvasConfig,
}));
```

### 15.2 状态流转图

```
[input]                    [thinking]                  [execution]
   │    startThinking()          │    completeThinking()       │
   ▼                             ▼                             ▼
 显示输入框               显示思考节点+选项          显示执行蓝图
                           用户选择(3轮)              自动执行步骤
                               │                            │
                               ▼                    步骤失败?
                         completeThinking()              │
                                                        是 → 显示"需干预"
                                                             用户点击"重新规划"
                                                               │
                                                               ▼
                                                    [thinking] 干预模式
                                                        │
                                                        ▼
                                                    [execution] 新蓝图
                                                              │
                                                              ▼
                                                         [completed]
                                                          显示Summary
```

### 15.3 关键Action说明

| Action | 参数 | 功能 |
|--------|------|------|
| `startThinking` | 无 | 生成第一个思考节点，进入thinking阶段 |
| `selectThinkingOption` | nodeId, optionId | 选择选项，可能生成下一节点或转入执行 |
| `setCustomInput` | nodeId, input | 设置自定义输入，逻辑同上 |
| `completeThinking` | 无 | 思考完成，生成执行蓝图，进入execution |
| `executeNextStep` | 无 | 引擎核心：找就绪步骤→执行→递归 |
| `interveneExecution` | stepId | 从失败点重新思考，保留已完成步骤 |
| `handleIntervention` | 'continue'\|'newBranch'\|'stop' | 处理干预动作 |
| `updateCanvasConfig` | Partial<CanvasConfig> | 更新画布配置（含节点重算） |
| `reset` | 无 | 重置所有状态到初始值 |

---

## 16. 面板组件 (Panels)

### 16.1 InterventionPanel (干预面板)

| 属性 | 值 |
|------|-----|
| **文件** | `src/components/panels/InterventionPanel.tsx` (154行) |
| **触发** | 执行步骤失败 + 用户点击"重新规划" |

**Props**:
```typescript
interface InterventionPanelProps {
  isOpen: boolean;
  onClose: () => void;
  stepName: string;   // 失败步骤名称
  onAction: (action: 'continue' | 'newBranch' | 'stop') => void;
}
```

**三个干预选项**:
| 选项 | ID | 图标 | 说明 |
|------|-----|------|------|
| 继续执行 | `continue` | Play | 跳过当前步骤继续 |
| 生成新分支 | `newBranch` | GitBranch | 创建替代执行路径 |
| 完全停止 | `stop` | Square | 终止整个任务 |

### 16.2 SettingsPanel (设置面板)

| 属性 | 值 |
|------|-----|
| **文件** | `src/components/panels/SettingsPanel.tsx` (193行) |
| **风格** | Unity编辑器config.json折叠面板 |
| **触发** | 工具栏蓝色设置按钮 |

**可调参数**: 左右比例、执行区域比例、思考/执行缩放、思考/执行节点间距、背景样式(渐变/纯色/网格/点阵)、重置默认值

---

## 17. ToolEditor (工具编辑器弹窗)

| 属性 | 值 |
|------|-----|
| **文件** | `src/components/visual/ToolEditor.tsx` (176行) |
| **触发** | 点击工具栏+号 或 点击黄色方块 或 拖放后 |

**Props**:
```typescript
interface ToolEditorProps {
  item?: ToolItem | null;   // 编辑项(null=新建)
  isOpen: boolean;
  onClose: () => void;
  onSave: (item: Omit<ToolItem, 'id'> & { id?: string }) => void;
}
```

**表单字段**:
| 字段 | 类型 | 说明 |
|------|------|------|
| 类型 | 三选一按钮 | MCP(Cpu图标) / Skill(Sparkles图标) / File(FileText图标) |
| 名称 | text输入 | 工具名称 |
| 描述 | text输入 | 工具描述 |
| 颜色 | 10色选择 | 预设色板(黄/蓝/绿/红/紫/粉) |
| 内容 | textarea | MCP配置JSON / Skill代码 / File内容 |

---

## 18. Mock引擎

| 属性 | 值 |
|------|-----|
| **文件** | `src/mock/mockEngine.ts` (196行) |

### 18.1 generateThinkingNode
- 3轮固定问题（旅行规划主题）
- 每轮3个选项+自定义
- 干预模式返回4个干预选项
- Counter自增生成ID

### 18.2 generateExecutionBlueprint
- 6个主路径步骤（水平排列）
- 3个分支步骤（从step_003垂直排列）
- 1个汇合步骤（对比方案，依赖3个分支）
- 统一间距参数控制位置
- Counter自增生成ID

### 18.3 预设数据
```
思考问题: 你想规划什么样的旅行? → 你计划去哪里旅行? → 你计划什么时候出发?
执行步骤: 查询天气 → 搜索景点 → 规划交通 → [查询高铁/航班/自驾] → 对比方案 → 推荐酒店 → 生成行程
```

---

## 19. 完整文件清单（全部15个文件）

| # | 文件路径 | 行数 | 职责 |
|---|----------|------|------|
| 1 | `src/components/BlueprintCanvas.tsx` | ~560 | 主画布容器，三栏布局编排 |
| 2 | `src/components/visual/VisualAdapter.tsx` | ~400 | AdapterViser主容器，标签页系统 |
| 3 | `src/components/visual/WebBrowser.tsx` | ~200 | Web浏览器模拟(Edge) |
| 4 | `src/components/visual/IDE.tsx` | ~400 | VSCode IDE模拟 |
| 5 | `src/components/visual/AdapterDefault.tsx` | ~300 | 默认Adapter(任务进度面板) |
| 6 | `src/components/visual/ToolDock.tsx` | ~180 | 中间工具栏(黄色方块) |
| 7 | `src/components/visual/ToolEditor.tsx` | ~176 | 工具编辑器弹窗 |
| 8 | `src/components/nodes/ThinkingNode.tsx` | ~246 | 思考蓝图节点 |
| 9 | `src/components/nodes/ExecutionNode.tsx` | ~285 | 执行蓝图节点 |
| 10 | `src/components/nodes/SummaryNode.tsx` | ~168 | 执行摘要节点 |
| 11 | `src/components/panels/InterventionPanel.tsx` | ~154 | 干预面板弹窗 |
| 12 | `src/components/panels/SettingsPanel.tsx` | ~193 | 设置面板(config.json风格) |
| 13 | `src/store/useBlueprintStore.ts` | ~360 | Zustand全局状态管理 |
| 14 | `src/types/index.ts` | ~99 | TypeScript类型定义 |
| 15 | `src/mock/mockEngine.ts` | ~196 | Mock数据生成引擎 |

**总计约 3913 行代码**

---

## 20. 完整功能清单（全部模块）

### 20.1 已实现功能

#### A. 思考蓝图（左侧）
- [x] ReactFlow画布渲染思考节点
- [x] 节点概览行（Brain图标+问题+状态+展开按钮）
- [x] 四选一选项（A/B/C + 自定义）
- [x] 推荐选项标记（Sparkles图标）
- [x] 自定义输入框（展开/折叠）
- [x] 红色"重新思考"干预按钮
- [x] 3轮递进式思考（完成后自动转执行）
- [x] 节点选中高亮+完成状态样式
- [x] 蓝色Handle连线点（顶部target+底部source）
- [x] 3轮后自动收敛转入执行蓝图

#### B. 执行蓝图（右上）
- [x] ReactFlow画布渲染执行节点
- [x] 多路径布局（主路径+分路径+汇合点）
- [x] 4种状态样式（pending/running/completed/failed）
- [x] 主/支路径标记
- [x] 汇合点标记（橙色"汇合"标签）
- [x] 红色"重新规划"干预按钮
- [x] 执行引擎（自动按依赖顺序执行）
- [x] step_003固定模拟失败（测试干预流程）
- [x] 进度条动画（running状态）
- [x] 结果/错误展示
- [x] 依赖信息展示
- [x] Summary摘要节点（执行完成后自动添加）
- [x] Summary展开面板（步骤列表统计+"开始新任务"按钮）
- [x] 绿色Handle连线点（顶部/左侧target + 底部/右侧source）

#### C. 工具栏（中间）
- [x] 蓝色设置按钮 → SettingsPanel
- [x] 蓝色搜索按钮 → 工具搜索过滤
- [x] 黄色+号按钮 → ToolEditor新建
- [x] 8个内置工具显示（彩色方块）
- [x] 工具点击 → 打开编辑器
- [x] 工具拖拽 → dataTransfer序列化

#### D. AdapterViser（右下）
- [x] 浏览器式多标签页（画布/Web/IDE）
- [x] +号新建标签页（对话框：名称+类型选择）
- [x] 新建标签可关闭
- [x] Canvas标签：ReactFlow画布+拖放接收
- [x] Web标签：Edge浏览器模拟
- [x] IDE标签：VSCode模拟
- [x] 默认Adapter标签：任务进度面板

#### E. Web浏览器
- [x] 地址栏（URL显示/编辑/Enter导航）
- [x] 后退/前进/刷新/Home导航
- [x] Bing首页模拟
- [x] 通用网页骨架屏
- [x] 加载动画

#### F. IDE
- [x] VSCode深色主题+蓝色状态栏
- [x] 文件树（Explorer面板）
- [x] 编辑器（行号+代码+标签栏）
- [x] 终端（模拟npm输出+颜色）
- [x] 工具栏（运行/停止/调试/搜索/Git/插件）

#### G. 全局
- [x] Zustand状态管理（阶段/思考/执行/配置）
- [x] 干预机制（失败→思考→重新生成）
- [x] SettingsPanel（7项可调参数）
- [x] InterventionPanel（3种干预动作）
- [x] ToolEditor（新建/编辑工具）
- [x] Mock引擎（3轮思考+多路径执行）
- [x] 深蓝渐变背景
- [x] 可配置比例系统

### 20.2 未实现功能（纯前端样子）

| 模块 | 未实现项 |
|------|----------|
| 全局 | 无真实后端通信，所有数据Mock |
| 全局 | 无数据持久化，刷新丢失 |
| 思考蓝图 | 固定3轮旅行规划问题，非动态生成 |
| 思考蓝图 | 选项非AI生成，是预设数据 |
| 执行蓝图 | 执行是定时器模拟，非真实操作 |
| 执行蓝图 | step_003固定失败，非真实判断 |
| 工具栏 | 工具搜索仅前端过滤 |
| Web浏览器 | 不能真正访问互联网 |
| Web浏览器 | 书签/历史/Cookie均为UI |
| IDE | 代码只读，无编辑功能 |
| IDE | 无语法高亮 |
| IDE | 终端输出是模拟，不执行真实命令 |
| IDE | Git/插件/调试仅为按钮 |
| AdapterDefault | 静态模拟数据，非实时同步 |
| 画布拖放 | 拖放后节点间无自动连线 |
| 画布拖放 | 节点无双击编辑功能 |

---

*文档版本: 2025-06-14*
*适配代码版本: VisualAdapter v2.0(多标签页重构版)*
*总代码量: ~3913行（15个文件）*
