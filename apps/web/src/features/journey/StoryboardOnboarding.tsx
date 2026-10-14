import { useEffect, useRef, useState } from "react";

export interface Profile {
  currentStatus?: string;
  career: string;
  years: string;
  arrangement: string;
  focus: string[];
  experience: string;
  resumeName: string;
}
export const EMPTY_PROFILE: Profile = {
  currentStatus: "", career: "", years: "", arrangement: "",
  focus: [], experience: "", resumeName: "",
};

interface Props {
  profile: Profile;
  setProfile: (next: Profile) => void;
  finish: () => void;
  busy: boolean;
}

const STATUS = ["Student", "Recent Graduate", "Working Professional", "Career Switcher"];
const TARGETS = ["Software Engineer", "Data Scientist", "Product Manager", "Business Analyst", "UX/UI Designer", "QA Engineer", "Other"];
const SKILLS = ["Python", "Java", "JavaScript", "SQL", "Cloud / AWS", "Data Analysis", "React", "Communication", "Testing", "Design", "Leadership", "Research"];
const YEARS = ["0–1 year", "2–3 years", "4–6 years", "7+ years"];
const prompts = [
  { label: "Current status", title: "What best describes you?", detail: "Tell us where you are in your career." },
  { label: "Target role", title: "What role are you targeting?", detail: "Select the kind of position you want to apply for." },
  { label: "Key skills", title: "Which skills do you bring?", detail: "Choose your main skills. You can edit these anytime." },
  { label: "Experience", title: "How many years of experience?", detail: "This helps us tailor your resume accurately." },
  { label: "Preferences", title: "Anything else we should know?", detail: "Add useful context or concrete experience for your profile." },
  { label: "Resume", title: "Finally, upload your resume", detail: "We'll extract career evidence for your review once importing is available." },
];

export function StoryboardOnboarding({ profile, setProfile, finish, busy }: Props) {
  const [question, setQuestion] = useState(0);
  const [customRole, setCustomRole] = useState("");
  const [skillSearch, setSkillSearch] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const activeRef = useRef<HTMLDivElement>(null);
  const status = profile.currentStatus || "";

  useEffect(() => {
    if (question > 0 && activeRef.current) {
      activeRef.current.scrollIntoView?.({ behavior: "smooth", block: "center" });
    }
  }, [question]);

  const summaries = [
    status,
    profile.career,
    profile.focus.join(", "),
    profile.years,
    profile.experience.trim() ? "Notes and experience added" : "Open to opportunities",
    profile.resumeName || "Skipped",
  ];
  const valid = [!!status, !!profile.career, profile.focus.length > 0, !!profile.years, true, true];
  const set = <K extends keyof Profile>(key: K, value: Profile[K]) => setProfile({ ...profile, [key]: value });

  return <main className="aw-onboarding aw-storyboard-onboarding">
    <div className="aw-storyboard-progress">
      <span>Let's get to know you</span><span>Step {question + 1} of 6</span>
      <div className="aw-progress"><span style={{ width: `${((question + 1) / 6) * 100}%` }} /></div>
    </div>
    <div className="aw-storyboard-questions">
      {prompts.slice(0, question).map((item, i) => (
        <button className="aw-answer-strip" type="button" key={item.label}
          onClick={() => setQuestion(i)} aria-label={`Edit ${item.label}`}>
          <span className="aw-answer-strip-name"><span aria-hidden="true">✓</span> {item.label}</span>
          <span className="aw-answer-strip-value">{summaries[i]}</span>
        </button>
      ))}
      <section className="aw-question aw-storyboard-question" key={question} ref={activeRef}>
        <div className="aw-question-count">YOUR CAREER PROFILE · {String(question + 1).padStart(2, "0")}</div>
        <h2>{prompts[question].title}</h2>
        <p className="aw-muted">{prompts[question].detail}</p>

        {question === 0 && <div className="aw-choice-grid">
          {STATUS.map(value => <button type="button" key={value}
            className={status === value ? "selected" : ""}
            aria-pressed={status === value}
            onClick={() => set("currentStatus", value)}><span className="aw-radio-dot" />{value}</button>)}
        </div>}

        {question === 1 && <>
          <div className="aw-choice-grid">
            {TARGETS.map(value => <button type="button" key={value}
              className={profile.career === value ? "selected" : ""}
              aria-pressed={profile.career === value}
              onClick={() => set("career", value)}><span className="aw-radio-dot" />{value}</button>)}
          </div>
          {profile.career === "Other" && <input className="aw-text-field" aria-label="Specify your target role"
            placeholder="Type your target role" value={customRole}
            onChange={event => setCustomRole(event.target.value)} />}
        </>}

        {question === 2 && <>
          <input type="search" className="aw-text-field aw-skill-search" aria-label="Search skills"
            placeholder="Search skills..." value={skillSearch} onChange={event => setSkillSearch(event.target.value)} />
          <div className="aw-choice-grid">
            {SKILLS.filter(value => value.toLowerCase().includes(skillSearch.toLowerCase()))
              .map(value => <button type="button" key={value}
                className={profile.focus.includes(value) ? "selected" : ""}
                aria-pressed={profile.focus.includes(value)}
                onClick={() => set("focus", profile.focus.includes(value)
                  ? profile.focus.filter(skill => skill !== value) : [...profile.focus, value])}>
                <span className="aw-radio-dot" />{value}</button>)}
          </div>
        </>}

        {question === 3 && <div className="aw-choice-grid">
          {YEARS.map(value => <button type="button" key={value}
            className={profile.years === value ? "selected" : ""}
            aria-pressed={profile.years === value}
            onClick={() => set("years", value)}><span className="aw-radio-dot" />{value}</button>)}
        </div>}

        {question === 4 && <>
          <textarea className="aw-text-field aw-preferences-field" aria-label="Career preferences and real experience"
            rows={5} maxLength={1800} value={profile.experience}
            placeholder="For example, I completed an internship building REST APIs with Python. I'm interested in backend development."
            onChange={event => set("experience", event.target.value)} />
          <small className="aw-help-note">Optional. Include only experience you can verify; it will be saved as unconfirmed evidence for your approval.</small>
        </>}

        {question === 5 && <>
          <label className="aw-file-drop" htmlFor="aw-resume-upload">
            <span className="aw-file-icon" aria-hidden="true">⇧</span>
            <strong>{selectedFile ? selectedFile.name : "Drop your resume here, or browse files"}</strong>
            <span>PDF, DOC, DOCX, or TXT · 10 MB maximum</span>
            <input id="aw-resume-upload" type="file" accept=".pdf,.doc,.docx,.txt"
              onChange={event => {
                const file = event.target.files?.[0] ?? null;
                if (file && file.size > 10 * 1024 * 1024) {
                  event.target.value = ""; setSelectedFile(null); set("resumeName", ""); return;
                }
                setSelectedFile(file); set("resumeName", file?.name ?? "");
              }} />
          </label>
          {profile.resumeName && <p className="aw-upload-success">✓ {profile.resumeName} selected</p>}
          <p className="aw-help-note">File import is not connected yet. Your file stays on this device; we store only its name in this browser.</p>
        </>}

        <div className="aw-question-actions">
          {question > 0 ? <button type="button" className="aw-storyboard-back" onClick={() => setQuestion(question - 1)}>← Back</button>
            : <span />}
          <button className="aw-primary" type="button"
            disabled={busy || !valid[question] || (question === 1 && profile.career === "Other" && !customRole.trim())}
            onClick={() => {
              if (question === 1 && profile.career === "Other") {
                set("career", customRole.trim());
              }
              if (question < 5) setQuestion(question + 1);
              else finish();
            }}>
            {question === 5 ? "Finish setup" : "Continue"} <span aria-hidden="true">→</span>
          </button>
        </div>
      </section>
    </div>
  </main>;
}
