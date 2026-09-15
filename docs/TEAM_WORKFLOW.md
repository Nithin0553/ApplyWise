# Six-Person Team Workflow

## Roles
- Project Manager: Nithin Thirumani
- Project Technical Manager: Niraali Deepak Bandi
- Project Requirements Manager: Sampreet Ajjanagouda Patil
- Project Design Manager: Daniel Hernandez
- Project Test Manager / Quality Assurance Manager: Suraj Loni
- Project Configuration Manager: Prudhvi Prasad Sikharam
- All six members are also software developers.

## Mandatory flow
`Issue -> branch -> code/tests -> pull request -> CI -> review -> squash merge`

Never push feature work directly to `main`.

## Branch naming
- `feat/F02-evidence-profile`
- `feat/F04-job-analysis`
- `fix/F08-unsupported-metric`
- `test/F05-matching-cases`
- `docs/requirements-v1`
- `chore/ci-cache`

Avoid permanent personal branches.

## Before work
1. Create or claim a GitHub issue.
2. Ensure it includes Feature ID, acceptance criteria, dependencies, and expected tests.
3. Update local `main`.
4. Branch from current `main`.
5. Stay within the feature-owned module unless the PR declares a cross-cutting change.

## Review routing
- Requirements impact -> Requirements Manager
- Cross-module architecture -> Technical Manager
- UX/design-system impact -> Design Manager
- CI/config/dependencies -> Configuration Manager
- Test/release-quality -> Test/QA Manager
- Scope/release/change control -> Project Manager

A developer should not be the sole approver of their own feature.

## Preventing crossover
- One primary module per feature.
- Agree on contracts before parallel dependent work.
- Never edit another developer's merged migration.
- Feature UI stays in `src/features/<feature>`.
- Shared UI stays in `src/components`.
- Shared backend utilities need a named purpose.

## Sync habit
```bash
git checkout main
git pull
git checkout <branch>
git rebase main
```

Before review:
```bash
make check
```

## Merge strategy
Use **Squash and merge**. Keep PRs small enough to review in roughly 15-30 minutes.

## Definition of Done
A feature is done only when acceptance criteria pass, tests pass, authorization/data-isolation implications are covered, contracts/docs are updated, provenance/verification rules are preserved where relevant, accessibility is checked for UI work, CI is green, review is complete, and traceability is updated.

## Recommended first split
Start with F01 Authentication/RBAC, F02 Career Evidence Profile, F13 core version/application model, F04 Job Description Analysis contract/prototype, F08 Claim Verification contract/prototype, and shared frontend navigation/design-system foundation.
