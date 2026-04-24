/**
 * AdapterAttachments
 * 显示在 ExecutionNode 右上角，展示绑定的黄色方块
 */
import React from 'react';
import type { AdapterAttachment } from '../../hooks/useAdapter';
import './AdapterAttachments.css';

interface Props {
  stepId: string;
  attachments: AdapterAttachment[];
  onAttachmentClick: (adapterId: string) => void;
}

export const AdapterAttachments: React.FC<Props> = ({
  stepId,
  attachments,
  onAttachmentClick
}) => {
  // 拖放状态 (简化版，不使用 dnd-kit)
  const [isOver, setIsOver] = React.useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsOver(true);
  };

  const handleDragLeave = () => {
    setIsOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsOver(false);
    // 处理拖放逻辑
    const data = e.dataTransfer.getData('application/json');
    if (data) {
      try {
        const item = JSON.parse(data);
        console.log('[AdapterAttachments] Dropped:', item, 'on step:', stepId);
        // 这里应该调用 attachToStep
      } catch (err) {
        console.error('Drop error:', err);
      }
    }
  };

  return (
    <div
      className={`adapter-attachments ${isOver ? 'drop-active' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {attachments.length === 0 ? (
        <span className="placeholder">+</span>
      ) : (
        <div className="adapter-icons">
          {attachments.map((att, idx) => (
            <button
              key={`${att.adapterId}-${idx}`}
              className={`adapter-icon-btn ${att.locked ? 'locked' : ''}`}
              style={{ backgroundColor: att.adapterRef.color }}
              onClick={() => onAttachmentClick(att.adapterId)}
              title={att.adapterRef.name}
            >
              <span>{att.adapterRef.icon}</span>
              {att.locked && <span className="lock-badge">🔒</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
