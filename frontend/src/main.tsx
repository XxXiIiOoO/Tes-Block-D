import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { AppPreferencesProvider } from "./preferences/AppPreferencesContext";
import { registerServiceWorker } from "./pwa";
import "./styles.css";

registerServiceWorker();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppPreferencesProvider>
      <AuthProvider>
        <App />
      </AuthProvider>
    </AppPreferencesProvider>
  </React.StrictMode>,
);
