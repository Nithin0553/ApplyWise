import { TailoringPage } from "./features/tailoring/TailoringPage";

export function App() {
  return (
    <main className="shell">
      <h1>ApplyWise</h1>
      <p>
        F07 tailoring prototype: generated statements stay candidates and always carry the
        evidence they came from.
      </p>
      <TailoringPage />
    </main>
  );
}
