import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { AppLayout } from "./layouts/AppLayout";
import { useAppPreferences } from "./preferences/AppPreferencesContext";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { AdminPage } from "./pages/AdminPage";
import { DashboardPage } from "./pages/DashboardPage";

import { LoginPage } from "./pages/LoginPage";
import { ProjectDetailsPage } from "./pages/ProjectDetailsPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ProfilePage } from "./pages/ProfilePage";
import { RegisterPage } from "./pages/RegisterPage";

import { RunDetailsPage } from "./pages/RunDetailsPage";
import { RunsPage } from "./pages/RunsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { TestDetailsPage } from "./pages/TestDetailsPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";


function ProtectedRoutes() {
  const { isAuthenticated, loading } = useAuth();
  const { t } = useAppPreferences();

  if (loading) {
    return <div className="screen-state">{t("loading.app")}</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}


function PublicOnlyRoutes() {
  const { isAuthenticated, loading } = useAuth();
  const { t } = useAppPreferences();

  if (loading) {
    return <div className="screen-state">{t("loading.session")}</div>;
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}


function NotFound() {
  const { t } = useAppPreferences();
  return (
    <div className="screen-state">
      <p>{t("error.notFound")}</p>
    </div>
  );
}


export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<PublicOnlyRoutes />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />

        </Route>

        <Route element={<ProtectedRoutes />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/:projectId" element={<ProjectDetailsPage />} />
            <Route path="/tests/:testId" element={<TestDetailsPage />} />
            <Route path="/runs" element={<RunsPage />} />
            <Route path="/runs/:runId" element={<RunDetailsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}
