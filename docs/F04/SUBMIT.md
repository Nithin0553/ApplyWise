# Submit the F04 work

Owner: Sampreet Ajjanagouda Patil (@Sampreet26)

The patch contains only F04 code, tests, fixtures, documentation and a small Vite configuration change. It does not include the earlier F13 draft.

## Apply the patch

Download `ApplyWise_F04.patch` to your Mac's Downloads folder. In Terminal, open your existing ApplyWise repository. Confirm `git status` is clean before changing branches. If you do not have a clone, clone `https://github.com/Nithin0553/ApplyWise.git` and enter its folder first.

```bash
git switch main
git pull --ff-only
git switch -c feat/F04-job-analysis
git apply --check ~/Downloads/ApplyWise_F04.patch
git apply --index ~/Downloads/ApplyWise_F04.patch
git diff --cached --stat
```

If this feature branch already exists, switch to it instead of creating another. If `git apply --check` reports a conflict, stop before applying the patch and resolve against the current repository version. The patch was prepared against commit `3e863f1fb7ff5c21c2a777fd788538f4550bf7f3`.

## Review and demonstrate

Follow `docs/F04/README.md` to install dependencies and run the prototype. Review the source and tests so you can explain the contract, importance handling and extraction limitations. Run the verification commands documented there before committing.

## Commit and push

Use your own configured Git name and GitHub-associated email. Do not use another member's identity.

```bash
git commit -m "feat(job-analysis): add F04 requirement contract and parser prototype"
git push -u origin feat/F04-job-analysis
```

The commit and push happen on your computer using your GitHub authentication. No commit or remote push was performed by the assistant. If GitHub reports write permission denied, ask the repository owner to confirm your collaborator access; do not share your password or access token in chat.

## Open the pull request

1. Open the repository on GitHub and choose **Compare & pull request** for `feat/F04-job-analysis`.
2. Set the base to `main`.
3. Use the title **F04: add job analysis contract and parser prototype**.
4. Copy the body from `docs/F04/PR_DESCRIPTION.md`.
5. Link the existing F04 issue through the PR's Development section.
6. Request technical/QA review and wait for CI. Do not merge directly into main or approve your own submission.
7. Submit the PR link as your work evidence, following your instructor's submission instructions.

If no F04 issue exists yet, `docs/F04/ISSUE.md` contains the issue text. Nothing in this package creates an issue or PR automatically.
