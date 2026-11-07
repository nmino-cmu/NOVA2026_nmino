import { BrowserRouter, HashRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { ComparePage } from "./pages/Compare";
import { PlaybackPage } from "./pages/Playback";
import { ProviderPage } from "./pages/Provider";
import { ReviewPage } from "./pages/Review";
import { RunLibrary } from "./pages/RunLibrary";
import { RunWorkspace } from "./pages/RunWorkspace";
import { WorkspaceScreen } from "./components/WorkspaceScreen";
import { ConversationPage } from "./pages/Conversation";

const routerBase = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");
const Router = import.meta.env.VITE_HASH_ROUTER === "1" ? HashRouter : BrowserRouter;
// Hash routes live after #. A basename there is the URL path, which the hash location does not include.
const basename =
  import.meta.env.VITE_HASH_ROUTER === "1"
    ? undefined
    : routerBase && routerBase !== "/"
      ? routerBase
      : undefined;

export default function App() {
  return (
    <Router basename={basename}>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<ConversationPage />} />
          <Route path="c/:id" element={<ConversationPage />} />
          <Route path="board" element={<WorkspaceScreen />} />
          <Route path="new" element={<Navigate to="/?new=1" replace />} />
          <Route path="runs" element={<RunLibrary />} />
          <Route path="runs/:id" element={<RunWorkspace />} />
          <Route path="playback/:id" element={<PlaybackPage />} />
          <Route path="review" element={<ReviewPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="provider" element={<ProviderPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Router>
  );
}
