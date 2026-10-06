# F04 validation record

Checked on 2026-10-02 against repository base commit `3e863f1fb7ff5c21c2a777fd788538f4550bf7f3`.

| Check | Result |
|---|---|
| Backend `ruff check .` | Passed |
| Backend `pytest -q` | 31 tests passed, including the existing health test |
| Frontend `npm run lint` | Passed |
| Frontend `npm test -- --run` | 4 tests passed, including the existing App test |
| Frontend `npm run build` | Passed; shared home and standalone F04 HTML entry built |
| `git diff --check` | Passed |

Backend tests used Python 3.12.14 and a disposable environment with the repository's declared dependencies. Frontend checks used Node 24.19.0; CI specifies Node 22. CI itself has not run for this unpublished branch.

The backend suite emitted one dependency deprecation warning for Starlette's use of httpx. No test failed.

A full headless-browser check was attempted but could not run because the browser download returned an invalid archive. Frontend interaction checks ran in jsdom; manual visual and keyboard review remains part of PR review. No browser screenshot or end-to-end browser pass is claimed.

F04 is an initial rule-based English parser prototype. Authentication, persistent job records, exhaustive extraction quality evaluation and production deployment are outside this submission.
