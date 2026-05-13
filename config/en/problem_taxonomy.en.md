# Problem Taxonomy

> English translation. Korean original (`problem_taxonomy.md`) is the canonical version referenced by the system.

## Classification Criteria

Read the problem files and classify them under one (or a combination) of the types below.
Generator/Evaluator perform classification themselves; this file is for reference.

---

### TYPE_A: Data Analysis

**Characteristics**: Process and analyze structured data to derive quantitative answers
**Trigger**: Large JSON/CSV/TXT data files + aggregation/classification/prediction questions
**Core tools**: Python (pandas, numpy, scikit-learn)
**Verification**: Re-execute code or independently recompute

---

### TYPE_B: Code Interpretation / Execution

**Characteristics**: Interpret and execute non-standard languages (DSLs) or obfuscated code
**Trigger**: Problems requiring a programming-language spec or interpreter implementation
**Core tools**: Python runtime
**Verification**: Re-implement the interpreter and re-run

---

### TYPE_C: Multimedia Extraction

**Characteristics**: Extract information from images / videos / PDFs
**Trigger**: Media files attached where text extraction is non-trivial
**Core tools**: pytesseract, pdfplumber, PyMuPDF, video analysis libraries
**Verification**: Cross-validate with a different extraction method

---

### TYPE_D: Document Synthesis

**Characteristics**: Synthesize information from multiple sources into a structured document
**Trigger**: Multiple heterogeneous files (email/document/audio/spreadsheet) integrated into a single document
**Core tools**: Format-specific parsers (docx, xlsx, m4a, pdf, etc.), provided template
**Verification**: Cross-reference originals to confirm facts

---

### TYPE_E: Spatial Simulation

**Characteristics**: Search for optimal paths/operations in a physical environment
**Trigger**: Coordinate system + collision conditions + simulator file provided
**Core tools**: Provided `simulator.py` or a pygame environment
**Verification**: Re-run the simulator to confirm path validity

---

## Composite Types

A single problem may fall under two or more types:

| Combination | Example pattern |
|---|---|
| A+C  | Extract numeric values from images, then statistical analysis |
| B+C  | OCR code from images, then execute it |
| D+C  | Document synthesis from multi-file inputs containing audio/images |

For composite types, apply the verification methods of all relevant types.

---

## Classification Flow

```
Inspect problem/files/
│
├── Large JSON/CSV/TXT data?           → TYPE_A
├── Language spec / DSL file?           → TYPE_B
├── Image / PDF / video file?           → TYPE_C
├── Multiple heterogeneous files + template? → TYPE_D
└── Simulator / coordinate-system file? → TYPE_E
```

If the problem provides no explicit type hint, decide based on the problem description in `description.md`.
