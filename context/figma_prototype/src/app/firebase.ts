import { initializeApp } from "firebase/app";
import { connectAuthEmulator, getAuth } from "firebase/auth";

const firebaseConfig = {
  projectId: "ftd-2026",
  apiKey: "AIzaSyA7CWNGUFkNYt9pbRF8Hh-l9lKJWSPnoQ8",
  authDomain: "ftd-2026.firebaseapp.com",
};

const firebaseApp = initializeApp(firebaseConfig);
const firebaseAuth = getAuth(firebaseApp);

// Browser tests build the app with VITE_FIREBASE_AUTH_EMULATOR_URL so sign-up, verification and
// password-reset run against the local Firebase Auth emulator instead of the real project.
const emulatorUrl = (import.meta as any).env?.VITE_FIREBASE_AUTH_EMULATOR_URL as string | undefined;
if (emulatorUrl) connectAuthEmulator(firebaseAuth, emulatorUrl, { disableWarnings: true });

export { firebaseAuth, firebaseApp };
