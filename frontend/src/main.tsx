import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { installApiOrigin, installStaticDemoFetch } from "./api/client";
import App from "./App";
import "./index.css";
import "./figma.css";

installApiOrigin();
installStaticDemoFetch();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
