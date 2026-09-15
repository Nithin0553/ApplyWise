# Contributing to ApplyWise

All contributors must read `docs/TEAM_WORKFLOW.md` before starting feature work.

## Rules
1. Do not push feature work directly to `main`.
2. Start from a GitHub issue with a Feature ID and acceptance criteria.
3. Use a short-lived branch.
4. Add or update tests with behavior changes.
5. Keep pull requests focused and small.
6. Never commit secrets, real resumes, or real applicant data.
7. Preserve evidence provenance, verification, approval, and unsupported-claim blocking constraints.
8. Squash merge after CI and review.

## Branch examples
- `feat/F02-evidence-profile`
- `fix/F08-unsupported-metric`
- `test/F05-matching-cases`
- `docs/requirements-v1`

## Commit examples
- `feat(evidence): add approved evidence entity`
- `test(matching): cover partial support classification`
- `docs(architecture): record export adapter decision`
