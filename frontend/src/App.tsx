import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { PlaybackPage } from "./pages/Playback";
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
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
