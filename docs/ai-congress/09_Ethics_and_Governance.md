# 09 — Ethics and Governance

Goal: make "documented ethical safeguards" (Impact band 16–20) concrete and demonstrable.

## Principles

1. **Advisory only.** The AI never changes marks or official attainment.
2. **The headline AI never sees student data.** The auditor reads question text only; attainment uses aggregates.
3. **Humans decide.** Every flag can be accepted or overridden with a reason; overrides are logged.
4. **No faculty ranking.** No view ranks or scores individual teachers; reporting is aggregated by course and program.
5. **Explain every output.** Quoted evidence, reason, confidence; abstain when unsure.

## Data flow

To document as a diagram: question paper upload → pages rendered or text extracted in memory (file not stored; only the wording + SHA-256 kept; page images wait in Redis only until the worker picks them up, then are deleted) → AI gateway (provider chosen by the organization → redaction if external → model) → usage logged (`ai.calls`) → flags stored with model, prompt version and the independent judgments behind them → teacher review → audit log.

- Student names, IDs and marks never pass through the gateway to an external model. The auditor sends question wording only; the copilot sends curriculum context, and the gateway redacts the signed-in user's name and email, emails, phone numbers and student-ID patterns before any external call.
- **Data residency:** each organization chooses per feature between a self-hosted model (`local`, Ollama — nothing leaves its servers), a hosted model, or off (AI Settings page). Per-institution deployment is still offered.
- **Known limit:** redaction is pattern-based and cannot find arbitrary names typed into a copilot chat; photos sent to a hosted vision model are not redacted (question papers carry no student data, but may show the setter's name). Institutions that need a hard guarantee should choose `local`.

## Bias evaluation

Report auditor accuracy per stratum: department, theory vs lab, year level, writing style (including non-native English phrasing). Publish weak strata rather than hide them.

## Documents to produce

- **Model card:** models used, intended use, out-of-scope uses, evaluation results, known limitations.
- **Data-flow diagram.**
- **Risk register** (below).
- **Retention policy:** how long papers and AI outputs are kept; deletion on request.
- **Consent note** for using past question papers.

## Risk register

| Risk | Mitigation |
|---|---|
| Misclassification unfairly reflects on a teacher | Advisory only; override with reason; confidence threshold; abstain |
| Function creep into faculty performance evaluation | No per-teacher ranking views; aggregate-only reporting; stated in terms of use |
| Student data leakage | Auditor uses no student data; redaction in gateway; self-host option |
| Bias against certain disciplines or writing styles | Stratified evaluation; publish per-stratum accuracy |
| Prompt injection via teacher-entered text | Input sanitization, fixed tool allowlists, injection test suite |
| Over-reliance on AI judgments | Confidence shown; human sign-off required |
| Gaming the auditor (stuffing "analyze" verbs) | Classify by cognitive demand; robustness test set |
| Model or provider change shifts behaviour | Versioned prompts; evaluation harness re-run on every change |
