import { useState, useEffect } from "react";
import { FirebaseUser } from "firebase/auth";

import { firebaseAuth } from "./firebase";
import { signOut, onAuthStateChanged } from "firebase/auth";

import { Page } from "./types";
import { apiRequest, API_BASE } from "./api";
import { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, WORKSPACES, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA } from "./mockData";

import { AppShell } from "./components/Shell";
import { ReportModal } from "./components/pages/ReportModal";

import {
  LoginPage,
  RegisterPage,
  VerifyEmailPage,
  ForgotPasswordPage,
  OnboardingPage,
  DashboardPage,
  SearchPage,
  TickerDashboard,
  TimelinePage,
  FilingsPage,
  CommunityPage,
  ComparisonPage,
  WorkspacesPage,
  WorkspaceDetailPage,
  WorkspaceSettingsPage,
  ChatPage,
  AlertsPage,
  ProfilePage,
  AdminDashboard,
  AdminMappingPage,
  AdminUsersPage,
  AdminSystemPage,
  LegacyLandingPage,
} from "./components/pages";

export { firebaseAuth, API_BASE };

function App() {
  const [page, setPage] = useState<Page>("login");
  const [selectedTicker, setSelectedTicker] = useState("NVDA");
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
      case "dashboard": return <DashboardPage navigate={navigate} setSelectedTicker={setSelectedTicker} />;
      case "search": return <SearchPage navigate={navigate} setSelectedTicker={setSelectedTicker} />;
      case "ticker": return <TickerDashboard navigate={navigate} ticker={selectedTicker} firebaseUser={firebaseUser} onReport={() => setShowReport(true)} />;
      case "ticker-timeline": return <TimelinePage navigate={navigate} ticker={selectedTicker} />;
      case "ticker-filings": return <FilingsPage navigate={navigate} ticker={selectedTicker} />;
      case "ticker-community": return <CommunityPage navigate={navigate} ticker={selectedTicker} />;
      case "ticker-comparison": return <ComparisonPage navigate={navigate} />;
      case "workspaces": return <WorkspacesPage navigate={navigate} />;
      case "workspace-detail": return <WorkspaceDetailPage navigate={navigate} setSelectedTicker={setSelectedTicker} />;
      case "workspace-settings": return <WorkspaceSettingsPage navigate={navigate} />;
      case "chat": return <ChatPage navigate={navigate} />;
      case "alerts": return <AlertsPage navigate={navigate} />;
      case "profile": return <ProfilePage navigate={navigate} userEmail={userEmail} userName={userName} userPermissions={userPermissions} loading={profileLoading} />;
      case "admin": return <AdminDashboard navigate={navigate} />;
      case "admin-mapping": return <AdminMappingPage navigate={navigate} />;
      case "admin-users": return <AdminUsersPage navigate={navigate} />;
      case "admin-system": return <AdminSystemPage navigate={navigate} />;
      default: return <DashboardPage navigate={navigate} setSelectedTicker={setSelectedTicker} />;
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

export { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, WORKSPACES, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA };
export { LegacyLandingPage };
export default App;
