import { useParams } from "react-router-dom";
import { WorkspaceScreen } from "../components/WorkspaceScreen";

export function RunWorkspace() {
  const { id } = useParams<{ id: string }>();
  if (!id) return <div className="error-banner">Missing run id.</div>;
  return <WorkspaceScreen runId={id} />;
}
