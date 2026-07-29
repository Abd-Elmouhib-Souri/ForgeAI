"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { setAdminToken } from "@/lib/admin-api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AdminLoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [twoFactorCode, setTwoFactorCode] = useState("");
  const [requiresTwoFactor, setRequiresTwoFactor] = useState(false);

  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError("");
    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_URL}/admin/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
          two_factor_code: requiresTwoFactor ? twoFactorCode : undefined,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Erreur de connexion admin.");
      }

      if (data.requires_2fa) {
        setRequiresTwoFactor(true);
        return;
      }

      if (!data.access_token) {
        throw new Error("Token admin manquant.");
      }

      setAdminToken(data.access_token);
      router.replace("/admin/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 px-6 py-10 text-white">
      <div className="absolute -left-32 -top-32 h-80 w-80 animate-pulse rounded-full bg-red-500/20 blur-3xl" />
      <div className="absolute -bottom-32 -right-32 h-80 w-80 animate-pulse rounded-full bg-cyan-500/20 blur-3xl" />

      <div className="relative w-full max-w-md rounded-2xl border border-white/10 bg-white/10 p-8 shadow-2xl backdrop-blur-xl">
        <div className="mb-8 text-center">
          <p className="text-sm font-medium text-red-300">Admin Panel</p>
          <h1 className="mt-1 text-4xl font-bold tracking-tight">
            ForgeAI Admin
          </h1>
          <p className="mt-3 text-sm text-white/60">
            Accès réservé aux administrateurs.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!requiresTwoFactor && (
            <>
              <div>
                <label className="text-sm text-white/70">Email admin</label>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  placeholder="admin@exemple.com"
                  className="mt-1 w-full rounded-lg border border-white/10 bg-white/10 px-4 py-3 text-sm outline-none transition focus:border-red-300"
                />
              </div>

              <div>
                <label className="text-sm text-white/70">Mot de passe</label>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  placeholder="••••••••"
                  className="mt-1 w-full rounded-lg border border-white/10 bg-white/10 px-4 py-3 text-sm outline-none transition focus:border-red-300"
                />
              </div>
            </>
          )}

          {requiresTwoFactor && (
            <div>
              <label className="text-sm text-white/70">
                Code de double authentification
              </label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={twoFactorCode}
                onChange={(event) => setTwoFactorCode(event.target.value)}
                required
                autoFocus
                placeholder="123456"
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/10 px-4 py-3 text-center text-lg tracking-widest outline-none transition focus:border-red-300"
              />

              <button
                type="button"
                onClick={() => {
                  setRequiresTwoFactor(false);
                  setTwoFactorCode("");
                }}
                className="mt-2 text-xs text-white/60 underline hover:text-white"
              >
                Retour à la connexion admin
              </button>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-red-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-red-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting
              ? "Connexion..."
              : requiresTwoFactor
              ? "Vérifier le code"
              : "Connexion admin"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-white/40">
          Espace sécurisé — DotJcom ForgeAI
        </p>
      </div>
    </main>
  );
}