"use client";

import { useState, useTransition } from "react";
import { createAccount, setAccountTracked } from "./actions";
import { ACCOUNT_PURPOSES, type Account } from "@/lib/schemas";

type Purpose = (typeof ACCOUNT_PURPOSES)[number];

export function AccountsSection({ accounts: initial }: { accounts: Account[] }) {
  const [accounts, setAccounts] = useState(initial);
  const [name, setName] = useState("");
  const [purpose, setPurpose] = useState<Purpose>("spending");
  const [isTracked, setIsTracked] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setFormError("name is required");
      return;
    }
    setFormError(null);

    const formData = new FormData();
    formData.set("name", name.trim());
    formData.set("purpose", purpose);
    if (isTracked) formData.set("is_tracked", "on");

    startTransition(async () => {
      const outcome = await createAccount(formData);
      if (!outcome.ok) {
        setFormError(outcome.error);
        return;
      }
      setAccounts((prev) => [...prev, outcome.data]);
      setName("");
    });
  }

  function handleToggle(account: Account) {
    startTransition(async () => {
      const outcome = await setAccountTracked(account.id, !account.is_tracked);
      if (!outcome.ok) return; // toggle stays at its prior state; nothing silently changes
      setAccounts((prev) => prev.map((a) => (a.id === outcome.data.id ? outcome.data : a)));
    });
  }

  return (
    <div className="mt-3">
      {accounts.length === 0 ? (
        <p className="text-sm text-text-secondary">No accounts yet.</p>
      ) : (
        <ul className="divide-y divide-border">
          {accounts.map((a) => (
            <li key={a.id} className="flex items-center justify-between py-3">
              <div>
                <p className="text-sm text-text-primary">{a.name}</p>
                <p className="text-xs text-text-secondary">{a.purpose}</p>
              </div>
              <label className="flex items-center gap-2 text-xs text-text-secondary">
                <input
                  type="checkbox"
                  checked={a.is_tracked}
                  onChange={() => handleToggle(a)}
                  disabled={isPending}
                />
                Feeds the worksheet
              </label>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleCreate} className="mt-6 flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="account-name" className="block text-xs font-medium text-text-primary">
            Name
          </label>
          <input
            id="account-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Palmpay"
            className="mt-1 w-40 rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus-visible:border-accent-600"
          />
        </div>
        <div>
          <label htmlFor="account-purpose" className="block text-xs font-medium text-text-primary">
            Purpose
          </label>
          <select
            id="account-purpose"
            value={purpose}
            onChange={(e) => setPurpose(e.target.value as Purpose)}
            className="mt-1 rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus-visible:border-accent-600"
          >
            {ACCOUNT_PURPOSES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <label className="flex items-center gap-2 pb-2 text-xs text-text-secondary">
          <input type="checkbox" checked={isTracked} onChange={(e) => setIsTracked(e.target.checked)} />
          Feeds the worksheet
        </label>
        <button
          type="submit"
          disabled={isPending}
          className="rounded-md bg-accent-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-accent-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isPending ? "Adding…" : "Add account"}
        </button>
      </form>
      {formError && (
        <p role="alert" className="mt-2 text-xs text-danger-600">
          {formError}
        </p>
      )}
    </div>
  );
}
