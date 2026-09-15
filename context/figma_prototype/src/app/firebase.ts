import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  projectId: "ftd-2026",
  apiKey: "AIzaSyA7CWNGUFkNYt9pbRF8Hh-l9lKJWSPnoQ8",
  authDomain: "ftd-2026.firebaseapp.com",
};

const firebaseApp = initializeApp(firebaseConfig);
const firebaseAuth = getAuth(firebaseApp);

export { firebaseAuth, firebaseApp };
