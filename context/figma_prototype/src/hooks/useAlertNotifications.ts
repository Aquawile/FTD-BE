import { useCallback, useEffect, useRef, useState } from "react";
import { FirebaseUser } from "firebase/auth";
import { toast } from "sonner";
import { getAlertSummary } from "../api";

// Alerts are only created at the end of each data sync (22:20 / 00:20 UTC), so a
// light re-check is enough: on sign-in, on every page change, and every 5 minutes
// for a tab left open across a sync.
const RECHECK_MS = 5 * 60 * 1000;

const seenKey = (uid: string) => `ftd.alerts.lastNotifiedId.${uid}`;
function readSeen(uid: string): number {
  try { return Number(localStorage.getItem(seenKey(uid)) || 0); } catch { return 0; }
}
function writeSeen(uid: string, id: number) {
  try { localStorage.setItem(seenKey(uid), String(id)); } catch { /* storage unavailable */ }
}

/** Unread alert count for the bell/nav badge, plus a one-time pop-up for each new alert. */
export function useAlertNotifications(firebaseUser: FirebaseUser | null, page: string, onOpenAlerts: () => void) {
  const [unread, setUnread] = useState(0);
  const openRef = useRef(onOpenAlerts);
  openRef.current = onOpenAlerts;

  const refresh = useCallback(async () => {
    if (!firebaseUser) { setUnread(0); return; }
    try {
      const summary = await getAlertSummary(firebaseUser);
      setUnread(summary.unread_count);
      const newest = summary.newest_unread;
      if (newest && Number(newest.id) > readSeen(firebaseUser.uid)) {
        writeSeen(firebaseUser.uid, Number(newest.id));
        const more = summary.unread_count > 1 ? ` (+${summary.unread_count - 1} more unread)` : "";
        toast(`${newest.ticker ?? "Alert"}: alert triggered`, {
          description: newest.message + more,
          action: { label: "View", onClick: () => openRef.current() },
          duration: 10000,
        });
      }
    } catch {
      // Not signed in to the API yet, or offline: keep the last known count.
    }
  }, [firebaseUser]);

  useEffect(() => { refresh(); }, [refresh, page]);
  useEffect(() => {
    if (!firebaseUser) return;
    const id = window.setInterval(refresh, RECHECK_MS);
    return () => window.clearInterval(id);
  }, [firebaseUser, refresh]);

  return { unreadAlerts: unread, refreshAlerts: refresh };
}
