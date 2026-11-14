/** Whether the F15 interview-preparation route exists in this deployment.
 *
 * F15 is a prototype: `require_prototype_environment` removes its route when
 * `APP_ENV=production`, where it answers a plain 404. The shell must not offer
 * an action the server will refuse, so this constant mirrors that server gate
 * and is the single place the two are kept in step.
 *
 * It is deliberately a module of its own rather than an inline
 * `import.meta.env.DEV` check, so the unavailable branch can be tested by
 * mocking this module, and so lifting the gate is one edit in one place once
 * F15 is served in production.
 */
export const INTERVIEW_PREP_AVAILABLE: boolean = import.meta.env.DEV;

/** Shown instead of a broken screen if the stage is reached while gated off. */
export const INTERVIEW_PREP_UNAVAILABLE =
  "Interview prep is a prototype feature and is not available in this build.";
