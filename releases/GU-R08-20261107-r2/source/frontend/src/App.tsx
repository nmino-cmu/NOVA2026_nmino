import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { ComparePage } from "./pages/Compare";
import { PlaybackPage } from "./pages/Playback";
import { ProviderPage } from "./pages/Provider";
import { ReviewPage } from "./pages/Review";
import { RunLibrary } from "./pages/RunLibrary";
import { RunWorkspace } from "./pages/RunWorkspace";
import { SetupWizard } from "./pages/SetupWizard";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<SetupWizard />} />
          <Route path="runs" element={<RunLibrary />} />
          <Route path="runs/:id" element={<RunWorkspace />} />
          <Route path="playback/:id" element={<PlaybackPage />} />
          <Route path="review" element={<ReviewPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="provider" element={<ProviderPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
