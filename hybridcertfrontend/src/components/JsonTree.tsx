import React from "react";
import {SimpleTreeView, TreeItem} from "@mui/x-tree-view";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";

interface JsonTreeProps {
  data: any;
  nodeIdPrefix?: string;
  indent?: number; // pixels per level
}

export function JsonTree({ data, nodeIdPrefix = "root", indent = 16 }: JsonTreeProps) {
  const renderTree = (obj: any, key: string, prefix: string, level: number = 0): React.ReactNode => {
    const nodeId = `${prefix}-${key}`;
    const marginLeft = level * indent;

    if (typeof obj !== "object" || obj === null) {
      return (
        <TreeItem
          key={nodeId}
          itemId={nodeId}
          label={
            <div style={{ marginLeft, textAlign: "left", fontFamily: "monospace" }}>
              {`${key}: ${obj}`}
            </div>
          }
        />
      );
    }

    if (Array.isArray(obj)) {
      return (
        <TreeItem
          key={nodeId}
          itemId={nodeId}
          label={
            <div style={{ marginLeft, textAlign: "left", fontFamily: "monospace" }}>
              {`${key}: Array[${obj.length}]`}
            </div>
          }
        >
          {obj.map((item, idx) => renderTree(item, `${idx}`, nodeId, level + 1))}
        </TreeItem>
      );
    }

    // Object
    return (
      <TreeItem
        key={nodeId}
        itemId={nodeId}
        label={<div style={{ marginLeft, textAlign: "left", fontFamily: "monospace" }}>{key}</div>}
      >
        {Object.entries(obj).map(([subKey, value]) =>
          renderTree(value, subKey, nodeId, level + 1)
        )}
      </TreeItem>
    );
  };

  return (
    <SimpleTreeView
      slots={{ expandIcon: ExpandMoreIcon, collapseIcon: ChevronRightIcon }}
      sx={{ maxHeight: 400, overflowY: "auto", fontFamily: "monospace" }}
    >
      {renderTree(data, "root", nodeIdPrefix)}
    </SimpleTreeView>
  );
}