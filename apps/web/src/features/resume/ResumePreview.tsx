type ResumePreviewProps = {
  template: string;
};

export function ResumePreview({ template }: ResumePreviewProps) {
  return (
    <article
      className={`resume-preview resume-preview--${template}`}
      aria-label="Sample resume preview"
    >
      <header>
        <h3>Alex Morgan</h3>
        <p>IT Support Specialist</p>
        <p>Corpus Christi, TX · alex.morgan@example.com</p>
      </header>

      <section>
        <h4>Professional Summary</h4>
        <p>
          IT support professional with experience troubleshooting computers,
          assisting users, and documenting technical procedures.
        </p>
      </section>

      <section>
        <h4>Experience</h4>
        <p>
          <strong>IT Support Specialist · Example Company</strong>
        </p>
        <p>January 2023 – Present</p>
        <ul>
          <li>Resolve hardware and software issues for staff.</li>
          <li>Prepare computers and support new employee onboarding.</li>
          <li>Document recurring issues and troubleshooting procedures.</li>
        </ul>
      </section>

      <section>
        <h4>Education</h4>
        <p>Bachelor of Science in Computer Science</p>
        <p>Example University · 2022</p>
      </section>

      <section>
        <h4>Skills</h4>
        <p>Technical support · Windows · Linux · Python · Documentation</p>
      </section>
    </article>
  );
}