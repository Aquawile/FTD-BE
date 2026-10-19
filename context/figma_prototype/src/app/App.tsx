import { useState, useEffect } from "react";
import type { User as FirebaseUser } from "firebase/auth";

import { firebaseAuth } from "./firebase";
import { signOut, onAuthStateChanged } from "firebase/auth";

import { Page } from "./types";
import { apiRequest, API_BASE } from "../api";
import { WorkspaceResponse } from "../types";

import { AppShell } from "../components/Shell";
import { Toaster } from "./components/ui/sonner";
import { useAlertNotifications } from "../hooks/useAlertNotifications";

import {
  LoginPage,
  RegisterPage,
  VerifyEmailPage,
  ForgotPasswordPage,
  OnboardingPage,
  DashboardPage,
  SearchPage,
  TickerDashboard,
  WorkspacesPage,
  WorkspaceDetailPage,
  WorkspaceSettingsPage,
  AlertsPage,
  ProfilePage,
} from "../components/pages";

export { firebaseAuth, API_BASE };

function App() {
  const [page, setPage] = useState<Page>("login");
  const [selectedTicker, setSelectedTicker] = useState("NVDA");
  const [selectedWorkspace, setSelectedWorkspace] = useState<WorkspaceResponse | null>(null);
  const [searchText, setSearchText] = useState("");                 // top-bar search -> Research
  const [alertPrefill, setAlertPrefill] = useState<string | null>(null); // ticker page "Set Alert" -> Alerts
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);
  const [userProfile, setUserProfile] = useState<any>(null);
  const [userPermissions, setUserPermissions] = useState<string[]>([]);
  const [profileLoading, setProfileLoading] = useState(false);
  // Firebase restores the session asynchronously on load; render nothing until it has,
  // so a signed-in user isn't shown the login page on every refresh.
  const [authReady, setAuthReady] = useState(false);
  const [, setProfileVersion] = useState(0);   // bumped after a name change so the top bar re-reads displayName

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(firebaseAuth, async (user) => {
      setFirebaseUser(user);
      setAuthReady(true);
      // Signed in: leave the sign-in screens for the dashboard. Signed out: back to login.
      setPage(prev => {
        const signInScreens: Page[] = ["login", "register", "forgot-password"];
        if (user && signInScreens.includes(prev)) return "dashboard";
        if (!user && !["login", "register", "verify-email", "forgot-password"].includes(prev)) return "login";
        return prev;
      });
      if (user) {
        setProfileLoading(true);
        try {
          const [profileRes, permsRes] = await Promise.all([
            apiRequest("/auth/me/user", user),
            apiRequest("/users/me/permissions", user),
          ]);
          if (profileRes.ok) {
            const profile = await profileRes.json();
            setUserProfile(profile);
          }
          if (permsRes.ok) {
            const perms = await permsRes.json();
            setUserPermissions(perms.permissions || []);
          }
        } catch {
          // ignore fetch errors during initial auth state resolution
        } finally {
          setProfileLoading(false);
        }
      } else {
        setUserProfile(null);
        setUserPermissions([]);
      }
    });
    return () => unsubscribe();
  }, []);

  const navigate = (p: Page) => setPage(p);
  const { unreadAlerts, refreshAlerts } = useAlertNotifications(firebaseUser, page, () => navigate("alerts"));

  const refreshWorkspace = async () => {
    if (!firebaseUser || !selectedWorkspace) return;
    try {
      const res = await apiRequest(`/workspaces/${selectedWorkspace.id}/tickers`, firebaseUser);
      if (res.ok) {
        const tickers = await res.json();
        setSelectedWorkspace({ ...selectedWorkspace, tickers });
      }
    } catch {
      // ignore
    }
  };

  const handleSignOut = async () => {
    try { await signOut(firebaseAuth); } catch {}
    navigate("login");
  };

  const publicPages: Page[] = ["login", "register", "verify-email", "forgot-password", "onboarding-done"];
  const isPublic = publicPages.includes(page);

  const userEmail = firebaseUser?.email || userProfile?.email || "";
  const userName = firebaseAuth.currentUser?.displayName || firebaseUser?.displayName || userProfile?.email?.split("@")[0] || "";

  const renderPage = () => {
    switch (page) {
      case "login": return <LoginPage navigate={navigate} />;
      case "register": return <RegisterPage navigate={navigate} />;
      case "verify-email": return <VerifyEmailPage navigate={navigate} userEmail={firebaseUser?.email ?? undefined} />;
      case "forgot-password": return <ForgotPasswordPage navigate={navigate} />;
      case "onboarding-done": return <OnboardingPage navigate={navigate} />;
      case "dashboard": return <DashboardPage navigate={navigate} setSelectedTicker={setSelectedTicker} firebaseUser={firebaseUser} setSelectedWorkspace={setSelectedWorkspace} />;
      case "search": return <SearchPage navigate={navigate} setSelectedTicker={setSelectedTicker} firebaseUser={firebaseUser} initialQuery={searchText} />;
      case "ticker": return <TickerDashboard navigate={navigate} ticker={selectedTicker} firebaseUser={firebaseUser} onSetAlert={t => { setAlertPrefill(t); navigate("alerts"); }} />;
      case "workspaces": return <WorkspacesPage navigate={navigate} firebaseUser={firebaseUser} setSelectedWorkspace={setSelectedWorkspace} />;
      case "workspace-detail": return <WorkspaceDetailPage navigate={navigate} setSelectedTicker={setSelectedTicker} selectedWorkspace={selectedWorkspace} firebaseUser={firebaseUser} refreshWorkspace={refreshWorkspace} />;
      case "workspace-settings": return <WorkspaceSettingsPage navigate={navigate} selectedWorkspace={selectedWorkspace} firebaseUser={firebaseUser} onSaved={setSelectedWorkspace} onArchived={() => { setSelectedWorkspace(null); navigate("workspaces"); }} />;
      case "alerts": return <AlertsPage navigate={navigate} setSelectedTicker={setSelectedTicker} firebaseUser={firebaseUser} onAlertsChanged={refreshAlerts} prefillTicker={alertPrefill} onPrefillUsed={() => setAlertPrefill(null)} />;
      case "profile": return <ProfilePage navigate={navigate} userEmail={userEmail} userName={userName} userPermissions={userPermissions} loading={profileLoading} onProfileUpdated={() => setProfileVersion(v => v + 1)} />;
      default: return <DashboardPage navigate={navigate} setSelectedTicker={setSelectedTicker} firebaseUser={firebaseUser} setSelectedWorkspace={setSelectedWorkspace} />;
    }
  };

  if (!authReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" aria-label="Loading" />
      </div>
    );
  }

  return (
    <>
      {isPublic ? (
        <div className="min-h-screen bg-background">{renderPage()}</div>
      ) : (
        <AppShell page={page} navigate={navigate} userEmail={userEmail} userName={userName} onSignOut={handleSignOut} unreadAlerts={unreadAlerts} onSearch={setSearchText}>
          {renderPage()}
        </AppShell>
      )}
      <Toaster position="top-right" theme="dark" />
    </>
  );
}

export default App;
