import { useState } from "react";

export type Page =
  | "login" | "register" | "verify-email" | "forgot-password" | "onboarding-done"
  | "dashboard" | "search" | "ticker" | "ticker-timeline" | "ticker-filings" | "ticker-community" | "ticker-comparison"
  | "workspaces" | "workspace-detail" | "workspace-settings"
  | "chat" | "alerts" | "profile"
  | "admin" | "admin-mapping" | "admin-users" | "admin-system";

let currentPage: Page = "dashboard";
let navigateCallback: ((page: Page) => void) | null = null;

export function navigate(page: Page) {
  currentPage = page;
  if (navigateCallback) {
    navigateCallback(page);
  }
}

export function setNavigateCallback(cb: (page: Page) => void) {
  navigateCallback = cb;
}

export function getCurrentPage(): Page {
  return currentPage;
}

export function useNavigation() {
  const [page, setPage] = useState<Page>("dashboard");
  return { page, navigate: (p: Page) => { setPage(p); navigate(p); } };
}
