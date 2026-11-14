export interface LiveCanvasDeckAST {
  version: string;
  presentation: {
    slideWidth: number;
    slideHeight: number;
    unit: "px";
    defaultFonts: {
      major: string;
      minor: string;
    };
  };
  slides: SlideAST[];
}

export interface SlideAST {
  slideNumber: number;
  id: string;
  background: {
    color: string;
  };
  nodes: CanvasNodeAST[];
  edges: CanvasEdgeAST[];
}

export type CanvasNodeType = "shapeNode" | "imageNode" | "tableNode" | "anchorNode";

export interface NodeGeometryAST {
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  flipH: boolean;
  flipV: boolean;
}

export interface PortAST {
  id: string;
  idx: number;
  xPercent: number;
  yPercent: number;
}

export interface TextRunAST {
  text: string;
  fontFamily: string;
  fontSize: number;
  color: string;
  bold: boolean;
  italic: boolean;
  underline: boolean;
}

export interface TextParagraphAST {
  align: "left" | "center" | "right" | "justify";
  level: number;
  bullet: string | null;
  spaceBefore: number;
  spaceAfter: number;
  runs: TextRunAST[];
}

export interface ShapeStyleAST {
  background: string;
  borderColor: string;
  borderWidth: number;
  borderStyle: "solid" | "dashed" | "dotted";
  borderRadius: number;
  verticalAlign: "top" | "center" | "bottom";
  wordWrap: boolean;
  padding: {
    top: number;
    right: number;
    bottom: number;
    left: number;
  };
}

export interface TableDataAST {
  columnWidths: number[];
  rows: {
    height: number;
    cells: {
      text: string;
      backgroundColor: string;
    }[];
  }[];
}

export interface CanvasNodeAST extends Record<string, unknown> {
  id: string;
  name: string;
  type: CanvasNodeType;
  zIndex: number;
  shapePreset?: string;
  geometry: NodeGeometryAST;
  style?: ShapeStyleAST;
  textBody?: TextParagraphAST[];
  imageDataUri?: string;
  table?: TableDataAST;
  ports: PortAST[];
}

export interface CanvasEdgeAST {
  id: string;
  type: "straight" | "smoothstep" | "bezier";
  sourceNodeId: string;
  targetNodeId: string;
  sourceHandleId: string;
  targetHandleId: string;
  style: {
    strokeColor: string;
    strokeWidth: number;
    strokeDashArray?: string | null;
    arrowStart: string;
    arrowEnd: string;
  };
}