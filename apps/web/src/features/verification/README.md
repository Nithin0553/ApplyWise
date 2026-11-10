# F08 Claim Verification UI

Feature-owned UI for independent claim verification.

`VerificationPanel` submits a claim plus the approved evidence it cites, and
renders F08's classification together with the findings behind it. Every
verdict shows its reasons: a user told "unsupported" without an explanation can
only guess, and guessing here means deleting true claims.

Backend: `app/modules/verification/`. Contract:
`docs/contracts/F08_CLAIM_VERIFICATION_CONTRACT.md`.

**Verification is not approval.** F08 says what the evidence supports; F09 is
where the user decides to stand behind a claim. Nothing in this folder may
render a classification as an approval or as export authorization — only
`UNSUPPORTED` blocks export, and that is reported as `export_eligible`.
