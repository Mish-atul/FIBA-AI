# Contributing to FIBA AI

## Branching strategy
- `main`: stable branch used for demo-ready code and approved docs.
- `feature/atul-*`: Atul's implementation branches.
- `feature/tanishk-*`: Tanishk's implementation branches.
- `feature/yash-*`: Yash's implementation branches.

## Workflow
1. Pull latest `main`.
2. Create your feature branch.
3. Commit small logical changes.
4. Open a pull request to `main`.
5. Request review from at least 1 teammate.
6. Merge only after checks pass and no unresolved comments remain.

## Commit format
Use one of these prefixes:
- `feat:` new feature
- `fix:` bug fix
- `docs:` markdown/document updates
- `perf:` latency/performance improvements
- `refactor:` code structure changes without behavior changes
- `test:` tests and validation scripts

Example:
`feat: add rule-based opening inference from rotation`

## Pull request checklist
- Scope is clear and focused.
- Interface contracts in `common_integration.md` remain compatible.
- New dependencies are documented.
- Evidence screenshots or logs are attached for behavior changes.
- Latency impact is noted if pipeline logic changed.

## Integration guardrails
- Do not change result keys expected by frontend without updating all consumers.
- Keep models and heavy assets outside git history unless explicitly required.
- Preserve edge constraints: low memory, low latency, explainable output.
