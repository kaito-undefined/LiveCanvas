import { useState } from "react";
import { LiveCanvasViewer } from "./LiveCanvasViewer";
import type { LiveCanvasDeckAST } from "./types";

const deckAsts = Object.values(
  import.meta.glob("../data/output/*.json", {
    eager: true,
    import: "default",
  }),
) as LiveCanvasDeckAST[];

export function App() {
  const [deckAst] = useState<LiveCanvasDeckAST>(deckAsts[3]); //for devolopment, remove later

  return <LiveCanvasViewer deckAst={deckAst} />;
}

export default App;