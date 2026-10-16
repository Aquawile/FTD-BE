import { useState, useEffect } from "react";
import { FirebaseUser } from "firebase/auth";

import { firebaseAuth } from "./firebase";
import { signOut, onAuthStateChanged } from "firebase/auth";

import { Page } from "./types";
import { apiRequest, API_BASE } from "../api";
import { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA } from "../mockData";
import { WorkspaceResponse } from "../types";

import { AppShell } from "../components/Shell";
import ReportModal from "../components/pages/ReportModal";

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
  const [showReport, setShowReport] = useState(false);
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);
  const [userProfile, setUserProfile] = useState<any>(null);
  const [userPermissions, setUserPermissions] = useState<string[]>([]);
  const [profileLoading, setProfileLoading] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(firebaseAuth, async (user) => {
      setFirebaseUser(user);
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
  const userName = firebaseUser?.displayName || userProfile?.email?.split("@")[0] || "";

  const renderPage = () => {
    switch (page) {
      case "login": return <LoginPage navigate={navigate} />;
      case "register": return <RegisterPage navigate={navigate} />;
      case "verify-email": return <VerifyEmailPage navigate={navigate} userEmail={firebaseUser?.email} />;
      case "forgot-password": return <ForgotPasswordPage navigate={navigate} />;
      case "onboarding-done": return <OnboardingPage navigate={navigate} />;
      case "dashboard": return <DashboardPage navigate={navigate} setSelectedTicker={setSelectedTicker} firebaseUser={firebaseUser} />;
      case "search": return <SearchPage navigate={navigate} setSelectedTicker={setSelectedTicker} firebaseUser={firebaseUser} />;
      case "ticker": return <TickerDashboard navigate={navigate} ticker={selectedTicker} firebaseUser={firebaseUser} onReport={() => setShowReport(true)} />;
      case "workspaces": return <WorkspacesPage navigate={navigate} firebaseUser={firebaseUser} setSelectedWorkspace={setSelectedWorkspace} />;
      case "workspace-detail": return <WorkspaceDetailPage navigate={navigate} setSelectedTicker={setSelectedTicker} selectedWorkspace={selectedWorkspace} firebaseUser={firebaseUser} refreshWorkspace={refreshWorkspace} />;
      case "workspace-settings": return <WorkspaceSettingsPage navigate={navigate} selectedWorkspace={selectedWorkspace} firebaseUser={firebaseUser} />;
      case "alerts": return <AlertsPage navigate={navigate} firebaseUser={firebaseUser} />;
      case "profile": return <ProfilePage navigate={navigate} userEmail={userEmail} userName={userName} userPermissions={userPermissions} loading={profileLoading} />;
      default: return <DashboardPage navigate={navigate} setSelectedTicker={setSelectedTicker} firebaseUser={firebaseUser} />;
    }
  };

  return (
    <>
      {isPublic ? (
        <div className="min-h-screen bg-background">{renderPage()}</div>
      ) : (
        <AppShell page={page} navigate={navigate} userEmail={userEmail} userName={userName} onSignOut={handleSignOut}>
          {renderPage()}
        </AppShell>
      )}
      {showReport && <ReportModal onClose={() => setShowReport(false)} />}
    </>
  );
}

export { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA };
export default App;
