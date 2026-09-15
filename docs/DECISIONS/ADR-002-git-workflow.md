# ADR-002: Short-lived branches with main as the integration branch

**Status:** Accepted for foundation  
**Date:** 2026-09-15

`main` is the only long-lived integration branch. Developers use issue-linked short-lived branches and merge by pull request after CI and review. Permanent per-developer branches are avoided because they create drift and merge conflicts.
