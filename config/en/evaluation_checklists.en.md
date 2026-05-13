# Evaluation Checklists

> English translation. Korean original (`evaluation_checklists.md`) is the canonical version referenced by the system.

Verification checklists used by the Evaluator per problem type.
For problem-specific conditions, read `problem/description.md` and `problem/questions.md` directly.

---

## Universal Checklist (all problems)

### Format verification
- [ ] Answer format matches the problem requirements
- [ ] JSON answers are parseable
- [ ] All required fields exist
- [ ] Value ranges are within allowed bounds (case, character class, numeric range)
- [ ] Array lengths match the requirements
- [ ] No duplicate IDs
- [ ] Character-count limits, if any, are respected

### Completeness verification
- [ ] Every sub-question has an answer
- [ ] No empty answers or leftover placeholders

### Evidence verification
- [ ] Code-computed answers have evidence files
  → Missing evidence → auto-FAIL for that sub-question

---

## TYPE_A: Data Analysis Checklist

### Data-processing verification
- [ ] The full data required by the problem was processed (no loss from over-filtering)
- [ ] Aggregation unit (row, group, time range) matches the problem condition
- [ ] Date/period conditions are applied accurately
- [ ] Rounding/truncation rules are applied as specified for numeric computations

### Statistics / analysis verification
- [ ] Aggregation functions (sum, mean, count, max, min) are used correctly
- [ ] Grouping keys match the problem conditions
- [ ] For classification/prediction models, no data leakage between train/validation splits

### Reproducibility verification
- [ ] Re-running the evidence code yields the same result
- [ ] No hardcoded paths/values that would break in another environment

---

## TYPE_B: Code Interpretation / Execution Checklist

### Interpreter correctness verification
- [ ] All operators/commands in the language spec are implemented accurately
- [ ] Edge cases (zero handling, integer division, decimal handling) follow the spec
- [ ] Function/subroutine call stack is managed correctly
- [ ] Loop termination conditions are implemented accurately

### Execution-result verification
- [ ] stdin inputs are set per the problem conditions
- [ ] Output format (case, delimiters, etc.) matches the problem requirements
- [ ] Re-running the same code yields the same result

---

## TYPE_C: Multimedia Extraction Checklist

### Extraction completeness
- [ ] All media files were processed (cross-check file list vs. processed list)
- [ ] Cross-validated with multiple extraction methods (avoid OCR-only dependence)
- [ ] Special-character/case/whitespace handling matches the problem requirements

### Extraction accuracy
- [ ] Random samples (≥ 5) were re-confirmed directly
- [ ] No extraction failures (empty results, errors)
- [ ] For PDFs, hidden text/layers were also explored

---

## TYPE_D: Document Synthesis Checklist

### Factual accuracy (cross-reference originals)
- [ ] Every factual claim in the document is verifiable in the originals
- [ ] No information contradicting the originals
- [ ] No expired/invalid information included (apply the cutoff specified by the problem)

### Information completeness
- [ ] Key information from each required source (email, document, calendar, audio, etc.) is reflected
- [ ] No missing mandatory items

### Format compliance
- [ ] Follows the structure of the provided template (TOC, section order)
- [ ] Table column names and list formatting match the template
- [ ] Required metadata (author, date, etc.) is set correctly

---

## TYPE_E: Spatial Simulation Checklist

### Constraint verification
- [ ] Vehicle/object specs (size, turning radius, etc.) match the problem spec
- [ ] Operation units (move, rotate, etc.) are within allowed ranges
- [ ] Collision checks are performed against all obstacles

### Goal-achievement verification
- [ ] Final state satisfies the goal conditions (position, angle, etc.)
- [ ] Re-running with the provided simulator yields the same result
- [ ] If required, optimization criteria (minimum count, shortest path) are reviewed

---

## Verdict Decision Matrix

| CRITICAL count | HIGH count | Verdict |
|---|---|---|
| 0 | 0 | PASS |
| 0 | 1-2 | PARTIAL_PASS |
| 0 | 3+ | FAIL |
| 1+ | any | FAIL |
