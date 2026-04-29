import React from 'react';
import { useDnD } from './DnDContext';

export default ({ onSave, onSaveAs, onStatistics }) => {
  const [_, setType] = useDnD();

  const onDragStart = (event, nodeType) => {
    setType(nodeType);
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', nodeType);
    const ghost = document.createElement('div');
    ghost.style.position = 'absolute';
    ghost.style.top = '-1000px';
    document.body.appendChild(ghost);
    event.dataTransfer.setDragImage(ghost, 0, 0);
    setTimeout(() => document.body.removeChild(ghost), 0);
  };

  return (
    <aside>
      <div className="description">You can drag and drop nodes to the pane on the left.</div>
      <div className="dndnode input" onDragStart={(event) => onDragStart(event, 'circleDefault')} draggable>
        Node
      </div>
      <button className="save-btn" onClick={onStatistics}>
        Statistics page
      </button>
      <button className="save-btn" onClick={onSave}>
        Save
      </button>
      <button className="save-btn" onClick={onSaveAs}>
        Save As
      </button>
    </aside>
  );
};
