# json2xml knowledge graph

This directory records the project's architecture, behavior rules, and anchored tests so code and intent stop drifting apart in the dark.

## Documentation map

Start here to find the major concepts and the code they describe.

- [[architecture]] describes the library, CLI, and backend-selection paths.
- [[behavior]] captures conversion rules, input handling, and XPath mode.
- [[tests]] anchors a first set of regression-critical tests to documented behavior.

## Semantic search setup

Semantic search depends on an LLM key, so local `lat search` is unavailable until the environment is configured.

Set one of `LAT_LLM_KEY`, `LAT_LLM_KEY_FILE`, or `LAT_LLM_KEY_HELPER` before relying on semantic search. Without that key, direct lookups such as `lat locate` and structural validation through `lat check` still work.

## Repository hygiene

Local agent and editor directories are treated as machine-specific workspace state, not project knowledge or source.

The repository ignores `.codex`, `.pi`, and `.cursor` so local agent tooling does not pollute diffs or become part of the documented code surface. Keep durable design notes in `lat.md/` instead of those scratch directories.