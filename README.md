# LiveCanvas

LiveCanvas aims to turn static classroom slides into an interactive teaching
environment. A presentation is not treated as a collection of screenshots:
its visual structure, semantic relationships, and educational content should
remain available for later interaction.

This repository currently implements one of the foundational layers of that
larger product: extracting a structured representation from PowerPoint
(`.pptx`) files and rendering it on a canvas. It is not the complete
LiveCanvas experience yet. Later layers will use the parsed teaching material
with LLM-assisted workflows to organize it and make it interactive, for
example through executable code boxes, playable data structures, and other
classroom activities.

## Why visual fidelity matters

LiveCanvas must preserve the original slide closely enough that teachers can
use their existing material without feeling that their teaching method has
been replaced. A summary, a simplified redraw, or a generic replica is not an
acceptable substitute for the original presentation. If the visual layout and
the meaning of the slide are both preserved, the interactive features can add
value without taking control away from the teacher.

## Current pipeline

```text
data/input/example.pptx
        |
        | npm run convert
        v
data/output/example.json
        |
        | Vite import
        v
React Flow canvas
```

1. `src/python/main.py` reads PresentationML content with `python-pptx` and
   `lxml`.
2. The compiler converts slides, shapes, images, tables, and connectors into
   the `LiveCanvasDeckAST` structure.
3. The AST is written as JSON to `data/output/example.json`.
4. `src/App.tsx` imports the generated JSON into the application.
5. `src/LiveCanvasViewer.tsx` displays AST nodes and edges on a React Flow
   canvas.

This pipeline is the current extraction and visualization slice of
LiveCanvas. It establishes the semantic foundation that future interaction and
LLM-assisted teaching features will build on.

## Development log: paths we evaluated

The current approach was chosen after testing or evaluating several
alternatives. The central requirement was unusually strict: preserve the
slide's visual appearance as closely as possible while also retaining
semantic information such as shape types, positions, text, relationships, and
connectors.

### Aspose.Slides

Aspose.Slides requires a company account and adds an external dependency layer.
It is also not yet certain that it belongs in the full product. More
importantly, its trial conversion performance was unacceptably poor for our
use case. A conversion that only works under restrictive account or licensing
conditions, or that produces unreliable output, is not a suitable foundation
for the core pipeline.

### LibreOffice headless and other converters

Converting presentations to SVG or PDF with LibreOffice headless, or with
similar converters, preserves an image-like rendering rather than the
semantic model we need. SVG output may reduce the slide to `<path>` elements,
while PDF output may represent it as vectors that merely draw pixels on the
screen. These formats can be useful for visual export, but they effectively
take a screenshot of the slide and flatten the semantic layer. They do not
reliably tell us that an object was a decision diamond, a connector, a table,
or a meaningful grouped shape.

### Writing a complete XML parser from scratch

Reading the PPTX XML directly is possible, but the Office Open XML and
PresentationML documentation is roughly 6,000 pages. Learning that entire
specification and implementing a complete parser alone would be an enormous
project. It would also divert effort away from the more visionary part of
LiveCanvas: turning teaching material into a useful interactive learning
environment. The current implementation therefore uses established Python
libraries where they provide the required access, while keeping the resulting
AST focused on the information the product needs.

### Asking an AI tool to extract the semantics

AI tools or tools that AI use are often good at reading a PPTX and identifying some of its text.
However, their usual output is a textual summary: a few pieces of text from
each page, not a pixel-faithful visual replica accompanied by complete
semantic metadata. This loses more than individual semantic properties. The
entire visual layer can disappear because the input presentation is converted
into text as the tool's output. That is incompatible with the requirement to
preserve both the teacher's original slide and the information needed for
future interaction.

### Why the current direction is preferable

Extracting the relevant data from the PPTX structure gives us control over both
layers that matter:

- the visual layer: positions, dimensions, rotation, flipping, text, colors,
  lines, and shape geometry;
- the semantic layer: shape types, tables, images, groups, connectors, and
  their source and target relationships.

This is not a claim that the current converter supports every PowerPoint
feature. It is a deliberate foundation that can be extended while keeping the
original slide recognizable and preserving the data required by later
LiveCanvas layers.

## Folder structure

```text
PPTX_CONVERT/
├── data/
│   ├── input/
│   │   └── example.pptx       # Example PPTX to convert
│   └── output/
│       └── example.json       # AST JSON generated by the compiler
├── src/
│   ├── python/
│   │   └── main.py            # PPTX -> AST JSON compiler
│   ├── App.tsx                # Connects the JSON AST to the application
│   ├── LiveCanvasViewer.tsx   # AST -> React Flow viewer
│   ├── main.tsx               # React application entry point
│   ├── types.ts               # AST and canvas TypeScript types
│   └── index.css              # Global canvas styles
├── index.html                 # Vite HTML entry point
├── package.json               # Scripts and dependencies
├── tsconfig.app.json          # Application TypeScript settings
├── tsconfig.node.json         # Vite configuration TypeScript settings
├── vite.config.ts             # Vite configuration
└── eslint.config.js           # ESLint configuration
```

Input and output files are kept separate under `data/input/` and
`data/output/`.

## Requirements

- Node.js and npm
- Python 3
- Python packages:
  - `python-pptx`
  - `lxml`

Install the Python packages with:

```powershell
python -m pip install python-pptx lxml
```

Install the JavaScript dependencies with:

```powershell
npm install
```

## Commands

### PPTX -> JSON

```powershell
npm run convert
```

This command uses the following example files:

- Input: `data/input/example.pptx`
- Output: `data/output/example.json`

To run the compiler directly with different files:

```powershell
python src/python/main.py <input.pptx> <output.json>
```

Example:

```powershell
python src/python/main.py data/input/example.pptx data/output/example.json
```

### Development server

```powershell
npm run dev
```

Starts the Vite development server. The application opens the compiled AST
imported from `../data/output/example.json` in `src/App.tsx`. After changing
the PPTX, run `npm run convert` first.

### Production build

```powershell
npm run build
```

Runs the TypeScript check and produces a Vite production build in `dist/`.

### Lint

```powershell
npm run lint
```

Runs ESLint against the TypeScript and React sources.

### Production preview

```powershell
npm run preview
```

Serves an existing Vite build locally.

## AST model

The compiler's primary output is the `LiveCanvasDeckAST` type:

- `presentation`: slide dimensions and theme fonts
- `slides`: the slide list
- `nodes`: shape, image, table, and virtual anchor nodes
- `edges`: PPTX connectors and their connection endpoints

Shape nodes carry PPTX geometry in the `shapePreset` field. Geometry includes
`x`, `y`, `width`, `height`, `rotation`, `flipH`, and `flipV`. Connectors
preserve source and target node IDs, ports, line styles, and start/end
arrowheads.

The React viewer draws non-rectangular shapes as SVG polygons, so diamonds,
triangles, arrows, and similar shapes are not reduced to plain rectangles.
Connectors are attached to the source and target ports represented in the AST.

## Converting a new PPTX

1. Put the file to convert in `data/input/`.
2. Update the `convert` command in `package.json` for the new file names, or
   call the Python compiler directly.
3. Run `npm run convert`.
4. Check that the generated JSON is imported by `src/App.tsx`.
5. Open the canvas with `npm run dev`.

## Validation

Recommended validation order:

```powershell
npm run convert
npm run lint
npm run build
```

When `npm run convert` succeeds, it reports the slide count in the terminal
and writes the JSON file under `data/output/`.

## Known limitations

- `npm run convert` currently uses fixed example file names; there is no file
  picker in the user interface.
- Not every advanced Office feature has a React Flow equivalent yet.
- `dist/` is build output and does not replace the source AST or PPTX files.

## Known issues / next steps

- Fonts are not transferred yet.
- Arrows are currently passed through as empty rectangles.
- Background colors and other background properties are missing from white
  areas.
- The current canvas is dynamic and playground-like; it still needs to become
  more structured for classroom use.
- Later LiveCanvas layers will use the parsed material to add interaction and
  LLM-assisted educational transformations without discarding the original
  slide's visual and semantic information.
