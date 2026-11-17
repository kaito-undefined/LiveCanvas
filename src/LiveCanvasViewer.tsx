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

const MONOSPACE_FONTS = new Set([
  "aptos mono",
  "cascadia mono",
  "cascadia code",
  "consolas",
  "courier new",
  "fira code",
  "menlo",
  "monaco",
  "source code pro",
  "monospace",
]);

function getFontFamilyFallback(fontFamily?: string, defaultFont?: string): string {
  const font = fontFamily || defaultFont || "sans-serif";
  const lower = font.toLowerCase();
  if (MONOSPACE_FONTS.has(lower) || lower.includes("mono")) {
    return `"${font}", monospace`;
  }
  return `"${font}", "Segoe UI", system-ui, -apple-system, sans-serif`;
}

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

  const isLine = shapePreset === "line";
  const isArc = shapePreset === "arc";
  const isEllipse = shapePreset === "ellipse";
  const polygon = getShapePolygon(shapePreset);
  const isVectorShape = Boolean(polygon) || isLine || isArc;

  const arrowStart = (data.arrowStart as string | undefined) || style.arrowStart;
  const arrowEnd = (data.arrowEnd as string | undefined) || style.arrowEnd;
  const hasArrowStart = arrowStart && arrowStart !== "none";
  const hasArrowEnd = arrowEnd && arrowEnd !== "none";

  const strokeColor =
    style.borderColor && style.borderColor !== "transparent"
      ? style.borderColor
      : style.background && style.background !== "transparent"
      ? style.background
      : "#000000";
  const strokeWidth = Math.max(style.borderWidth || (isLine ? 1.5 : 2), 1);
  const strokeDasharray =
    style.borderStyle === "dashed"
      ? "6 4"
      : style.borderStyle === "dotted"
      ? "3 3"
      : undefined;

  const fullText = textBody ? textBody.map((p) => p.runs.map((r) => r.text).join("")).join("").trim() : "";
  const isSingleWord = fullText.length > 0 && !fullText.includes(" ") && !fullText.includes("\n");

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
        boxShadow: isVectorShape ? undefined : style.boxShadow,
        paddingTop: isLine || isArc ? 0 : `${style.padding.top}px`,
        paddingRight: isLine || isArc ? 0 : `${style.padding.right}px`,
        paddingBottom: isLine || isArc ? 0 : `${style.padding.bottom}px`,
        paddingLeft: isLine || isArc ? 0 : `${style.padding.left}px`,
        display: "flex",
        flexDirection: "column",
        justifyContent: justifyContentMap[style.verticalAlign] || "flex-start",
        boxSizing: "border-box",
        position: "relative",
        whiteSpace: isSingleWord ? "nowrap" : (style.wordWrap ? "pre-wrap" : "pre"),
        wordBreak: isSingleWord ? "normal" : "break-word",
        userSelect: "text",
      }}
    >
      <BidirectionalPorts />

      {/* SVG Poligon Arka Planı */}
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
            filter: style.boxShadow ? `drop-shadow(${style.boxShadow})` : undefined,
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

      {/* SVG Çizgi ve Oklar */}
      {isLine && (
        <svg
          width="100%"
          height="100%"
          style={{
            position: "absolute",
            inset: 0,
            overflow: "visible",
            pointerEvents: "none",
            filter: style.boxShadow ? `drop-shadow(${style.boxShadow})` : undefined,
          }}
        >
          <defs>
            {hasArrowEnd && (
              <marker
                id={`arrow-end-${data.id}`}
                markerWidth="8"
                markerHeight="8"
                refX="6"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 7 3, 0 6" fill={strokeColor} />
              </marker>
            )}
            {hasArrowStart && (
              <marker
                id={`arrow-start-${data.id}`}
                markerWidth="8"
                markerHeight="8"
                refX="1"
                refY="3"
                orient="auto-start-reverse"
              >
                <polygon points="7 0, 0 3, 7 6" fill={strokeColor} />
              </marker>
            )}
          </defs>
          <line
            x1={geometry.width <= 2 ? geometry.width / 2 : 0}
            y1={geometry.width <= 2 ? 0 : geometry.height <= 2 ? geometry.height / 2 : 0}
            x2={geometry.width <= 2 ? geometry.width / 2 : geometry.width}
            y2={geometry.width <= 2 ? geometry.height : geometry.height <= 2 ? geometry.height / 2 : geometry.height}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            strokeDasharray={strokeDasharray}
            markerEnd={hasArrowEnd ? `url(#arrow-end-${data.id})` : undefined}
            markerStart={hasArrowStart ? `url(#arrow-start-${data.id})` : undefined}
          />
        </svg>
      )}

      {/* SVG Arc (Yay) */}
      {isArc && (
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            zIndex: 0,
            overflow: "visible",
            pointerEvents: "none",
            filter: style.boxShadow ? `drop-shadow(${style.boxShadow})` : undefined,
          }}
        >
          <path
            d="M 50 0 A 50 50 0 0 1 100 50"
            fill="none"
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={strokeDasharray}
          />
        </svg>
      )}

      {/* Metin Paragrafları ve Run'lar */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          width: "100%",
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
              width: "100%",
            }}
          >
            {para.bullet && (
              <span
                style={{
                  marginRight: "6px",
                  userSelect: "none",
                  color: para.runs[0]?.color,
                  fontFamily: getFontFamilyFallback(para.runs[0]?.fontFamily),
                }}
              >
                {para.bullet}
              </span>
            )}
            {para.runs.map((run, rIdx) => {
              const textDecorations: string[] = [];
              if (run.underline) textDecorations.push("underline");
              if (run.strikethrough) textDecorations.push("line-through");
              return (
                <span
                  key={rIdx}
                  style={{
                    fontFamily: getFontFamilyFallback(run.fontFamily),
                    fontSize: `${run.fontSize}px`,
                    color: run.color,
                    fontWeight: run.bold ? 700 : 400,
                    fontStyle: run.italic ? "italic" : "normal",
                    textDecoration: textDecorations.length > 0 ? textDecorations.join(" ") : "none",
                  }}
                >
                  {run.text}
                </span>
              );
            })}
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
                    fontFamily: getFontFamilyFallback(cell.fontFamily),
                    fontSize: cell.fontSize ? `${cell.fontSize}px` : "13px",
                    color: cell.color || "inherit",
                    fontWeight: cell.bold ? 700 : 400,
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

// --- 6. SLAYT ÇERÇEVESİ (ArtboardNode) ---
export const ArtboardNode = memo(({ data }: NodeProps<Node<{ width: number; height: number; background: string }>>) => {
  return (
    <div
      style={{
        width: `${data.width}px`,
        height: `${data.height}px`,
        background: data.background,
        boxShadow: "0 10px 35px rgba(0, 0, 0, 0.4)",
        borderRadius: "4px",
        pointerEvents: "none",
      }}
    />
  );
});

const NODE_TYPES = {
  shapeNode: ShapeNode,
  imageNode: ImageNode,
  tableNode: TableNode,
  anchorNode: AnchorNode,
  artboardNode: ArtboardNode,
};

// --- 7. AST -> REACT FLOW DÖNÜŞTÜRÜCÜSÜ ---
function mapSlideToReactFlow(
  slide: LiveCanvasDeckAST["slides"][number],
  presentation?: LiveCanvasDeckAST["presentation"]
): { rfNodes: Node<CanvasNodeAST>[]; rfEdges: Edge[] } {
  const rfNodes: Node<CanvasNodeAST>[] = [];

  if (presentation) {
    rfNodes.push({
      id: `slide-artboard-${slide.id}`,
      type: "artboardNode",
      position: { x: 0, y: 0 },
      selectable: false,
      draggable: false,
      focusable: false,
      deletable: false,
      zIndex: -1000,
      data: {
        width: presentation.slideWidth,
        height: presentation.slideHeight,
        background: slide.background.color || "#FFFFFF",
      } as unknown as CanvasNodeAST,
    });
  }

  for (const node of slide.nodes) {
    rfNodes.push({
      id: node.id,
      type: node.type,
      position: { x: node.geometry.x, y: node.geometry.y },
      zIndex: node.zIndex,
      data: node,
    });
  }

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

// --- 8. ANA SLAYT SAHNESİ BİLEŞENİ ---
interface LiveCanvasViewerProps {
  deckAst: LiveCanvasDeckAST;
}

export const LiveCanvasViewer: React.FC<LiveCanvasViewerProps> = ({ deckAst }) => {
  const [activeSlideIdx, setActiveSlideIdx] = useState(0);
  const currentSlide = deckAst.slides[activeSlideIdx];

  const initialGraph = useMemo(
    () => mapSlideToReactFlow(currentSlide, deckAst.presentation),
    [currentSlide, deckAst.presentation]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialGraph.rfNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialGraph.rfEdges);

  useEffect(() => {
    const { rfNodes, rfEdges } = mapSlideToReactFlow(currentSlide, deckAst.presentation);
    setNodes(rfNodes);
    setEdges(rfEdges);
  }, [currentSlide, deckAst.presentation, setNodes, setEdges]);

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
          style={{ background: "#0F172A" }}
        >
          <Background color="#334155" gap={24} size={1} />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
};

const nodeTypesMemo = NODE_TYPES;
