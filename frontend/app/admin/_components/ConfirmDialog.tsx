"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { type ConfirmationRequest, setConfirmationHandler } from "@/lib/admin-api";

// Sprint 7.3: the console's confirmation dialog. adminFetch(..., { confirm })
// calls the handler registered here; the returned promise resolves with the
// 6-digit code, or null when the admin cancels.
type Pending = ConfirmationRequest & { resolve: (code: string | null) => void };

export default function ConfirmDialog() {
  const [pending, setPending] = useState<Pending | null>(null);
  const [code, setCode] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setConfirmationHandler(
      (request) =>
        new Promise<string | null>((resolve) => {
          setCode("");
          setPending({ ...request, resolve });
        }),
    );
    return () => setConfirmationHandler(null);
  }, []);

  useEffect(() => {
    if (!pending) return;
    inputRef.current?.focus();
    // Escape = cancel, like any dialog.
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending]);

  function close(value: string | null) {
    pending?.resolve(value);
    setPending(null);
    setCode("");
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (code.length === 6) close(code);
  }

  if (!pending) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm">
      <form
        onSubmit={submit}
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-confirm-title"
        className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-6 text-white shadow-2xl"
      >
        <p className="text-xs font-semibold uppercase tracking-wide text-red-300">Action sensible</p>
        <h2 id="admin-confirm-title" className="mt-1 text-lg font-semibold">
          Confirmation requise
        </h2>
        <p className="mt-3 whitespace-pre-line text-sm text-white/75">{pending.message}</p>

        <label className="mt-5 block text-sm text-white/70">
          Code de votre application d&apos;authentification
          <input
            ref={inputRef}
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={code}
            onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
            placeholder="123456"
            className="mt-1 w-full rounded-lg border border-white/10 bg-white/10 px-4 py-3 text-center text-lg tracking-widest outline-none focus:border-red-300"
          />
        </label>

        {pending.error && (
          <p role="alert" className="mt-3 rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200">
            {pending.error}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-3 text-sm">
          <button
            type="button"
            onClick={() => close(null)}
            className="rounded-lg border border-white/10 px-4 py-2 text-white/80 hover:bg-white/10"
          >
            Annuler
          </button>
          <button
            type="submit"
            disabled={code.length !== 6}
            className="rounded-lg bg-red-500 px-4 py-2 font-semibold text-white hover:bg-red-400 disabled:opacity-50"
          >
            Confirmer
          </button>
        </div>
      </form>
    </div>
  );
}
