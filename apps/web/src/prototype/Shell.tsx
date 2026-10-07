import { useEffect, useRef, useState, type ReactElement } from "react";

import "./softly.css";
import { useAuth } from "../features/auth";
import { ApprovalContext, approvableIds } from "./store";
import { CoverLetterPage } from "./pages/CoverLetterPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EvidencePage } from "./pages/EvidencePage";
import { JobsPage } from "./pages/JobsPage";
import { MatchPage } from "./pages/MatchPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ResumePage } from "./pages/ResumePage";
import { ReviewPage } from "./pages/ReviewPage";
import { TailoringPage } from "./pages/TailoringPage";
import { TrackerPage } from "./pages/TrackerPage";

/**
 * Labels name the task, not the module. The ids are unchanged so existing
 * hash links keep working.
 */
const ROUTES = [
  { id: "home", label: "Dashboard", inNav: true },
  { id: "evidence", label: "Evidence", inNav: true },
  { id: "jobs", label: "Job Analysis", inNav: true },
  { id: "match", label: "Matching", inNav: true },
  { id: "tailor", label: "Tailoring", inNav: true },
  { id: "review", label: "Review", inNav: true },
  { id: "cover", label: "Cover Letter", inNav: true },
  { id: "resume", label: "Resume", inNav: true },
  { id: "tracker", label: "Applications", inNav: true },
  { id: "profile", label: "Profile", inNav: false },
] as const;

export type RouteId = (typeof ROUTES)[number]["id"];

const SUPPORT_EMAIL = import.meta.env.VITE_SUPPORT_EMAIL ?? "";

/** Hash routing, so the app needs no router dependency. */
function useRoute(): [RouteId, (next: RouteId) => void] {
  const read = (): RouteId => {
    const raw = window.location.hash.replace("#", "") as RouteId;
    return ROUTES.some((route) => route.id === raw) ? raw : "home";
  };

  const [route, setRoute] = useState<RouteId>(read);

  useEffect(() => {
    const onChange = () => setRoute(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const go = (next: RouteId) => {
    window.location.hash = next;
    setRoute(next);
    window.scrollTo({ top: 0 });
  };

  return [route, go];
}

function initialsOf(name: string, email: string): string {
  const source = name.trim() || email.trim();
  const parts = source.split(/[\s@._-]+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** Account menu: avatar, name, and the actions that genuinely exist. */
function AccountMenu({ go }: PageProps) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!user) return null;

  return (
    <div className="sf-account" ref={container}>
      <button
        type="button"
        className="sf-account__trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="sf-avatar" aria-hidden="true">
          {initialsOf(user.full_name, user.email)}
        </span>
        <span className="sf-account__name">{user.full_name || user.email}</span>
      </button>

      {open && (
        <div className="sf-menu" role="menu">
          <div className="sf-menu__head">
            <strong>{user.full_name || "Account"}</strong>
            <span>{user.email}</span>
          </div>
          <button
            type="button"
            role="menuitem"
            className="sf-menu__item"
            onClick={() => {
              setOpen(false);
              go("profile");
            }}
          >
            Profile
          </button>
          <button
            type="button"
            role="menuitem"
            className="sf-menu__item sf-menu__item--quiet"
            onClick={() => {
              setOpen(false);
              logout();
            }}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

function SiteFooter() {
  return (
    <footer className="sf-footer">
      <span className="sf-footer__brand">ApplyWise</span>
      <nav className="sf-footer__links" aria-label="Support">
        {SUPPORT_EMAIL ? (
          <a href={`mailto:${SUPPORT_EMAIL}`}>Contact support</a>
        ) : (
          <span className="sf-muted">Contact support</span>
        )}
        <a href="#profile">Account</a>
      </nav>
    </footer>
  );
}

export function Shell() {
  const [route, go] = useRoute();
  const [approvedIds, setApprovedIds] = useState<string[]>(approvableIds().slice(0, 2));

  const approvals = {
    approvedIds,
    toggle: (id: string) =>
      setApprovedIds((current) =>
        current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
      ),
  };

  const pages: Record<RouteId, ReactElement> = {
    home: <DashboardPage go={go} />,
    evidence: <EvidencePage go={go} />,
    jobs: <JobsPage go={go} />,
    match: <MatchPage go={go} />,
    tailor: <TailoringPage go={go} />,
    review: <ReviewPage go={go} />,
    cover: <CoverLetterPage go={go} />,
    resume: <ResumePage go={go} />,
    tracker: <TrackerPage go={go} />,
    profile: <ProfilePage go={go} />,
  };

  return (
    <ApprovalContext.Provider value={approvals}>
      <div className="sf">
        <h1 className="sf-sr">ApplyWise</h1>

        <nav className="sf-nav" aria-label="Main">
          <span className="sf-logo">
            <span className="sf-logo-dot" aria-hidden="true" />
            ApplyWise
          </span>
          <div className="sf-navlinks">
            {ROUTES.filter((item) => item.inNav).map((item) => (
              <button
                key={item.id}
                type="button"
                className="sf-navlink"
                aria-current={route === item.id ? "page" : undefined}
                onClick={() => go(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <AccountMenu go={go} />
        </nav>

        {pages[route]}
        <SiteFooter />
      </div>
    </ApprovalContext.Provider>
  );
}

export interface PageProps {
  go: (next: RouteId) => void;
}
