import React, { memo, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  MarkerType,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type {
  LiveCanvasDeckAST,
  CanvasNodeAST,
  CanvasEdgeAST,
} from "./types";

// --- 1. PORT HANDLE YARDIMCISI (Çift Yönlü: Hem Source Hem Target) ---
const PORT_POSITIONS: Record<number, Position> = {
  0: Position.Top,
  1: Position.Left,
  2: Position.Bottom,
  3: Position.Right,
};

function getShapePolygon(shapePreset: string | undefined): string | null {
  switch (shapePreset) {
    case "triangle":
      return "50,0 100,100 0,100";
    case "rtTriangle":
      return "0,0 100,100 0,100";
    case "diamond":
    case "flowchartDecision":
      return "50,0 100,50 50,100 0,50";
    case "parallelogram":
      return "20,0 100,0 80,100 0,100";
    case "trapezoid":
      return "20,0 80,0 100,100 0,100";
    case "pentagon":
      return "50,0 100,38 82,100 18,100 0,38";
    case "hexagon":
      return "25,0 75,0 100,50 75,100 25,100 0,50";
    case "rightArrow":
      return "0,25 60,25 60,0 100,50 60,100 60,75 0,75";
    case "leftArrow":
      return "40,25 100,25 100,75 40,75 40,100 0,50 40,0";
    case "upArrow":
      return "25,40 25,100 75,100 75,40 100,40 50,0 0,40";
    case "downArrow":
      return "25,0 75,0 75,60 100,60 50,100 0,60 25,60";
    default:
      return null;
  }
}

const BidirectionalPorts: React.FC<{ visible?: boolean }> = ({ visible = false }) => {
  const hiddenStyle: React.CSSProperties = {
    opacity: visible ? 1 : 0,
    width: 6,
    height: 6,
    background: "#3B82F6",
    border: "none",
    pointerEvents: "all",
  };

  return (
    <>
      {[0, 1, 2, 3].map((idx) => {
        const pos = PORT_POSITIONS[idx];
        return (
          <React.Fragment key={idx}>
            <Handle
              type="source"
              position={pos}
              id={`port-${idx}-src`}
              style={hiddenStyle}
            />
            <Handle
              type="target"
              position={pos}
              id={`port-${idx}-tgt`}
              style={hiddenStyle}
            />
          </React.Fragment>
        );
      })}
    </>
  );
};

// --- 2. STANDART ŞEKİL VE METİN KUTUSU DÜĞÜMÜ (ShapeNode) ---
export const ShapeNode = memo(({ data }: NodeProps<Node<CanvasNodeAST>>) => {
  const { geometry, style, textBody, shapePreset } = data;
  if (!style) return null;

  const isEllipse = shapePreset === "ellipse";
  const polygon = getShapePolygon(shapePreset);
  const isVectorShape = Boolean(polygon);

  const justifyContentMap: Record<string, string> = {
    top: "flex-start",
    center: "center",
    bottom: "flex-end",
  };

  const scaleX = geometry.flipH ? -1 : 1;
  const scaleY = geometry.flipV ? -1 : 1;

  return (
    <div
      style={{
        width: `${geometry.width}px`,
        height: `${geometry.height}px`,
        transform: `rotate(${geometry.rotation}deg) scale(${scaleX}, ${scaleY})`,
        transformOrigin: "50% 50%",
        background: isVectorShape ? "transparent" : style.background,
        borderColor: isVectorShape ? "transparent" : style.borderColor,
        borderWidth: isVectorShape ? 0 : `${style.borderWidth}px`,
        borderStyle: style.borderStyle,
        borderRadius: isEllipse ? "50%" : `${style.borderRadius}px`,
        paddingTop: `${style.padding.top}px`,
        paddingRight: `${style.padding.right}px`,
        paddingBottom: `${style.padding.bottom}px`,
        paddingLeft: `${style.padding.left}px`,
        display: "flex",
        flexDirection: "column",
        justifyContent: justifyContentMap[style.verticalAlign] || "flex-start",
        boxSizing: "border-box",
        position: "relative",
        whiteSpace: style.wordWrap ? "pre-wrap" : "pre",
        wordBreak: "break-word",
        userSelect: "text",
      }}
    >
      <BidirectionalPorts />

      {/* SVG arka planı, dikdörtgen olmayan şekillerin semantiğini korur. */}
      {polygon && (
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            zIndex: 0,
            pointerEvents: "none",
          }}
        >
          <polygon
            points={polygon}
            fill={style.background.startsWith("linear") ? "#FFFFFF" : style.background}
            stroke={style.borderColor}
            strokeWidth={style.borderWidth}
          />
        </svg>
      )}

      {/* Metin Paragrafları ve Run'lar */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          transform: `scale(${scaleX}, ${scaleY})`, // Flip durumunda yazının ters dönmesini engeller
        }}
      >
        {textBody?.map((para, pIdx) => (
          <div
            key={pIdx}
            style={{
              textAlign: para.align,
              marginTop: `${para.spaceBefore}px`,
              marginBottom: `${para.spaceAfter}px`,
              paddingLeft: para.level > 0 ? `${para.level * 18}px` : 0,
              lineHeight: 1.25,
            }}
          >
            {para.bullet && (
              <span style={{ marginRight: "6px", userSelect: "none" }}>
                {para.bullet}
              </span>
            )}
            {para.runs.map((run, rIdx) => (
              <span
                key={rIdx}
                style={{
                  fontFamily: `"${run.fontFamily}", sans-serif`,
                  fontSize: `${run.fontSize}px`,
                  color: run.color,
                  fontWeight: run.bold ? 700 : 400,
                  fontStyle: run.italic ? "italic" : "normal",
                  textDecoration: run.underline ? "underline" : "none",
                }}
              >
                {run.text}
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
});

// --- 3. RESİM DÜĞÜMÜ (ImageNode) ---
export const ImageNode = memo(({ data }: NodeProps<Node<CanvasNodeAST>>) => {
  const { geometry, imageDataUri } = data;
  const scaleX = geometry.flipH ? -1 : 1;
  const scaleY = geometry.flipV ? -1 : 1;

  return (
    <div
      style={{
        width: `${geometry.width}px`,
        height: `${geometry.height}px`,
        transform: `rotate(${geometry.rotation}deg) scale(${scaleX}, ${scaleY})`,
        transformOrigin: "50% 50%",
        position: "relative",
      }}
    >
      <BidirectionalPorts />
      {imageDataUri && (
        <img
          src={imageDataUri}
          alt={data.name}
          draggable={false}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "fill",
            display: "block",
          }}
        />
      )}
    </div>
  );
});

// --- 4. TABLO DÜĞÜMÜ (TableNode) ---
export const TableNode = memo(({ data }: NodeProps<Node<CanvasNodeAST>>) => {
  const { geometry, table } = data;
  if (!table) return null;

  return (
    <div
      style={{
        width: `${geometry.width}px`,
        height: `${geometry.height}px`,
        transform: `rotate(${geometry.rotation}deg)`,
        transformOrigin: "50% 50%",
        position: "relative",
      }}
    >
      <BidirectionalPorts />
      <table
        style={{
          width: "100%",
          height: "100%",
          borderCollapse: "collapse",
          tableLayout: "fixed",
          fontSize: "13px",
        }}
      >
        <colgroup>
          {table.columnWidths.map((w, idx) => (
            <col key={idx} style={{ width: `${w}px` }} />
          ))}
        </colgroup>
        <tbody>
          {table.rows.map((row, rIdx) => (
            <tr key={rIdx} style={{ height: `${row.height}px` }}>
              {row.cells.map((cell, cIdx) => (
                <td
                  key={cIdx}
                  style={{
                    backgroundColor: cell.backgroundColor,
                    border: "1px solid #CBD5E1",
                    padding: "4px 8px",
                    verticalAlign: "middle",
                    overflow: "hidden",
                  }}
                >
                  {cell.text}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
});

// --- 5. SANAL ÇAPA DÜĞÜMÜ (Serbest Ok Uçları İçin AnchorNode) ---
export const AnchorNode = memo(() => {
  const handleStyle: React.CSSProperties = {
    opacity: 0,
    width: 2,
    height: 2,
    border: "none",
    background: "transparent",
  };

  return (
    <div style={{ width: 1, height: 1, position: "relative" }}>
      <Handle type="source" position={Position.Top} id="port-0-src" style={handleStyle} />
      <Handle type="target" position={Position.Top} id="port-0-tgt" style={handleStyle} />
    </div>
  );
});

const NODE_TYPES = {
  shapeNode: ShapeNode,
  imageNode: ImageNode,
  tableNode: TableNode,
  anchorNode: AnchorNode,
};

// --- 6. AST -> REACT FLOW DÖNÜŞTÜRÜCÜSÜ ---
function mapSlideToReactFlow(
  slide: LiveCanvasDeckAST["slides"][number]
): { rfNodes: Node<CanvasNodeAST>[]; rfEdges: Edge[] } {
  const rfNodes: Node<CanvasNodeAST>[] = slide.nodes.map((node) => ({
    id: node.id,
    type: node.type,
    position: { x: node.geometry.x, y: node.geometry.y },
    zIndex: node.zIndex,
    data: node,
  }));

  const rfEdges: Edge[] = slide.edges.map((edge: CanvasEdgeAST) => {
    const hasStartArrow = edge.style.arrowStart && edge.style.arrowStart !== "none";
    const hasEndArrow = edge.style.arrowEnd && edge.style.arrowEnd !== "none";

    const marker = (arrow: string) => {
      if (!arrow || arrow === "none") return undefined;
      const openTypes = new Set(["open", "oval", "stealth"]);
      return {
        type: openTypes.has(arrow) ? MarkerType.Arrow : MarkerType.ArrowClosed,
        color: edge.style.strokeColor,
      };
    };

    return {
      id: edge.id,
      type: edge.type === "bezier" ? "default" : edge.type,
      source: edge.sourceNodeId,
      target: edge.targetNodeId,
      sourceHandle: edge.sourceHandleId,
      targetHandle: edge.targetHandleId,
      zIndex: 9999,
      style: {
        stroke: edge.style.strokeColor,
        strokeWidth: edge.style.strokeWidth,
        strokeDasharray: edge.style.strokeDashArray || undefined,
      },
      markerStart: hasStartArrow ? marker(edge.style.arrowStart) : undefined,
      markerEnd: hasEndArrow ? marker(edge.style.arrowEnd) : undefined,
    };
  });

  return { rfNodes, rfEdges };
}

// --- 7. ANA SLAYT SAHNESİ BİLEŞENİ ---
interface LiveCanvasViewerProps {
  deckAst: LiveCanvasDeckAST;
}

export const LiveCanvasViewer: React.FC<LiveCanvasViewerProps> = ({ deckAst }) => {
  const [activeSlideIdx, setActiveSlideIdx] = useState(0);
  const currentSlide = deckAst.slides[activeSlideIdx];

  const initialGraph = useMemo(
    () => mapSlideToReactFlow(currentSlide),
    [currentSlide]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialGraph.rfNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialGraph.rfEdges);

  useEffect(() => {
    const { rfNodes, rfEdges } = mapSlideToReactFlow(currentSlide);
    setNodes(rfNodes);
    setEdges(rfEdges);
  }, [currentSlide, setNodes, setEdges]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0F172A" }}>
      {/* Üst Slayt Navigasyon Barı */}
      <div
        style={{
          height: "48px",
          background: "#1E293B",
          borderBottom: "1px solid #334155",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 16px",
          color: "#F8FAFC",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ fontWeight: 600, fontSize: "14px" }}>
          LiveCanvas — Slayt {currentSlide.slideNumber} / {deckAst.slides.length}
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            disabled={activeSlideIdx === 0}
            onClick={() => setActiveSlideIdx((i) => Math.max(0, i - 1))}
            style={{
              padding: "6px 12px",
              background: activeSlideIdx === 0 ? "#334155" : "#2563EB",
              color: "#FFF",
              border: "none",
              borderRadius: "4px",
              cursor: activeSlideIdx === 0 ? "not-allowed" : "pointer",
            }}
          >
            Önceki
          </button>
          <button
            disabled={activeSlideIdx === deckAst.slides.length - 1}
            onClick={() => setActiveSlideIdx((i) => Math.min(deckAst.slides.length - 1, i + 1))}
            style={{
              padding: "6px 12px",
              background: activeSlideIdx === deckAst.slides.length - 1 ? "#334155" : "#2563EB",
              color: "#FFF",
              border: "none",
              borderRadius: "4px",
              cursor: activeSlideIdx === deckAst.slides.length - 1 ? "not-allowed" : "pointer",
            }}
          >
            Sonraki
          </button>
        </div>
      </div>

      {/* Canvas Sahnesi */}
      <div style={{ flex: 1, position: "relative" }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypesMemo}
          fitView
          minZoom={0.2}
          maxZoom={2.5}
          style={{ background: currentSlide.background.color || "#FFFFFF" }}
        >
          <Background color="#94A3B8" gap={24} size={1} />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
};

const nodeTypesMemo = NODE_TYPES;