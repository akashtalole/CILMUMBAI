# ADR 0008: A managed multilingual embedding model behind an interface, chosen by test

**Status:** Proposed; the model is chosen after testing · 15 November 2026

## Context

Vector search must work for Marathi, Hindi and English, including questions that mix them and names written in either script. Anthropic's platform is used here for generation, not embeddings, so the embedding model is a separate choice.

## Options

| Option | For | Against |
|---|---|---|
| A multilingual embedding model on Amazon Bedrock (Amazon's Titan text embeddings or Cohere's multilingual model) | No servers; pay per use; IAM | Quality on Marathi is unknown until tested; availability in Mumbai to confirm; changing model means re-embedding |
| An open multilingual model (for example BGE-M3 or multilingual E5) on a SageMaker endpoint or a Fargate task | Full control; strong published multilingual results; no per-call fee | An endpoint to run; a floor cost; we handle scaling |
| An open model run only in batch jobs, with a small always-on task for queries | Cheap for bulk embedding | Two paths to maintain |

## Decision

Define one embedding interface. Begin with a managed multilingual model on Bedrock for zero operations. Before the 30-day mark, compare it with one open model on a hundred real questions per language from the evaluation set, and keep whichever retrieves better for Marathi. Store the model name and version with every vector so a change is a clean re-embed from parsed text on S3.

## Consequences

- Retrieval quality is reported by language; a model that helps English and hurts Marathi is rejected.
- Re-embedding the corpus must be a scripted job.

## To confirm

Which embedding models Bedrock offers in Mumbai and their documented language coverage.
