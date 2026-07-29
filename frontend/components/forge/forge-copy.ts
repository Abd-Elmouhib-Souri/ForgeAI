import type { ForgeLang } from "@/lib/language-context";

export const forgeCommonCopy = {
  fr: {
    brand: "ForgeAI",
    dashboard: "Dashboard",
    projects: "Mes projets",
    newProject: "Nouveau projet",
    logout: "Déconnexion",
    login: "Connexion",
    register: "Créer un compte",
    back: "Retour",
    loading: "Chargement...",
    error: "Une erreur est survenue.",
    connected: "Connecté",
  },
  en: {
    brand: "ForgeAI",
    dashboard: "Dashboard",
    projects: "My projects",
    newProject: "New project",
    logout: "Logout",
    login: "Login",
    register: "Create account",
    back: "Back",
    loading: "Loading...",
    error: "An error occurred.",
    connected: "Connected",
  },
} satisfies Record<ForgeLang, Record<string, string>>;