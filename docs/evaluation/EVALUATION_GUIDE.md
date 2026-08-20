# Local Evaluation & Quality Benchmark Guide

## 1. Quality Objectives

Every model profile and prompt template must be evaluated offline across four core capabilities:

1. **Citation Grounding Rate**: Percentage of statements in RAG mode backed by verbatim excerpts from retrieved documents. (Target: > 95%).
2. **Ungrounded Hallucination Rejection**: Model must explicitly state when evidence is insufficient rather than fabricating answers.
3. **Summarization Fidelity**: Preservation of factual metrics, acronym definitions, and key actors across quick, structured, and map-reduce modes.
4. **Rewriting Accuracy**: Complete preservation of original facts and numbers during grammar and dialect transformation.

---

## 2. Evaluation Datasets

The evaluation suite tests against four offline reference corpora:

- `eval_general`: Factual multi-turn conversation benchmarks.
- `eval_science`: Research papers testing acronym expansion, methodology breakdown, and limitation demarcation.
- `eval_news`: News articles testing fact vs. opinion segregation and metadata provenance capture.
- `eval_rewriting`: Complex drafts testing grammar correction and style conversion (Indian English, British English, Government Correspondence).

---

## 3. Running Automated Evaluation

Execute the evaluation benchmark suite using pytest:

```bash
python -m pytest tests/evaluation/
```
