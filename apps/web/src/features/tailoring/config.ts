/**
 * Which features talk to the real backend, and which are still stubbed.
 *
 * A feature is stubbed until its owner's work is merged. When their endpoint
 * lands, flip its flag to true here — nothing else in the UI changes.
 */
export const USE_REAL = {
  /** F01 authentication — Prudhvi (@Pras04ad) */
  f01_auth: false,
  /** F02 approved evidence — Nithin (@Nithin0553), PR #8 open */
  f02_evidence: false,
  /** F04 job analysis — Sampreet (@Sampreet26) */
  f04_jobAnalysis: false,
  /** F07 grounded generation — Niraali (@niraalibandi), implemented */
  f07_generation: true,
  /** F11 cover letter generation — Niraali (@niraalibandi), implemented */
  f11_coverLetter: true,
  /** F08 claim verification — Suraj (@surajloni) */
  f08_verification: false,
} as const;

/** Providers the backend can be asked to use for a preview call. */
export const AI_PROVIDERS = ["demo", "stub"] as const;
export type AiProvider = (typeof AI_PROVIDERS)[number];
