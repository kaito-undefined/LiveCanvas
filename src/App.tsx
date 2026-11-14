import { useState } from "react";
import { LiveCanvasViewer } from "./LiveCanvasViewer";
import type { LiveCanvasDeckAST } from "./types";
import exampleAst from "../data/output/example.json";

export function App() {
  const [deckAst] = useState<LiveCanvasDeckAST>(exampleAst as LiveCanvasDeckAST);

  return <LiveCanvasViewer deckAst={deckAst} />;
}

export default App;