"use client";

import { useRef, useState, useTransition, useEffect } from "react";
import { uploadStatement, type UploadActionResult } from "./actions";
import { ALLOWED_EXTENSIONS, validateStatementFile, type Account } from "@/lib/schemas";
import { getAccounts } from "@/lib/accounts";

export function UploadForm({ accounts: initialAccounts }: { accounts: Account[] }) {
  const [accounts, setAccounts] = useState(initialAccounts);
  const [accountId, setAccountId] = useState(initialAccounts[0]?.id ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadActionResult | null>(null);
  const [isPending, startTransition] = useTransition();

  // Refetch accounts on mount to ensure fresh data
  useEffect(() => {
    const refreshAccounts = async () => {
      try {
        const result = await getAccounts();
        if (!result.ok) {
          console.error("Failed to fetch accounts:", result.error);
          return;
        }
        const freshAccounts = result.data;
        setAccounts(freshAccounts);
        if (freshAccounts.length > 0 && !accountId) {
          const firstAccount = freshAccounts[0];
          if (firstAccount) {
            setAccountId(firstAccount.id);
          }
        }
      } catch (error) {
        console.error("Failed to refresh accounts:", error);
      }
    };
    refreshAccounts();
  }, [accountId]);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(candidate: File | null) {
    setResult(null);
    if (!candidate) {
      setFile(null);
      return;
    }
    const error = validateStatementFile(candidate);
    if (error) {
      setClientError(error);
      setFile(null);
      return;
    }
    setClientError(null);
    setFile(candidate);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setClientError("choose a statement file");
      return;
    }
    if (!accountId) {
      setClientError("choose an account");
      return;
    }
    setClientError(null);

    const formData = new FormData();
    formData.set("account_id", accountId);
    formData.set("file", file);

    startTransition(async () => {
      const outcome = await uploadStatement(formData);
      setResult(outcome);
      if (outcome.ok) {
        setFile(null);
        if (inputRef.current) inputRef.current.value = "";
      }
    });
  }

  return (
    <form onSubmit={handleSubmit} className="mt-8 space-y-5">
      <div>
        <label htmlFor="account" className="block text-sm font-medium text-text-primary">
          Account
        </label>
        <select
          id="account"
          value={accountId}
          onChange={(e) => setAccountId(e.target.value)}
          className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-primary focus-visible:border-accent-600"
        >
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="file" className="block text-sm font-medium text-text-primary">
          Statement file
        </label>
        <input
          ref={inputRef}
          id="file"
          type="file"
          accept={ALLOWED_EXTENSIONS.map((ext) => `.${ext}`).join(",")}
          onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
          className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-secondary file:mr-3 file:rounded-md file:border-0 file:bg-accent-50 file:px-3 file:py-1.5 file:text-accent-700"
        />
        <p className="mt-1 text-xs text-text-secondary">CSV, XLSX, or PDF, up to 10 MB.</p>
      </div>

      {clientError && (
        <p role="alert" className="rounded-md border border-danger-600/20 bg-danger-50 px-3 py-2 text-sm text-danger-600">
          {clientError}
        </p>
      )}

      <button
        type="submit"
        disabled={isPending}
        className="w-full rounded-md bg-accent-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-accent-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? "Uploading…" : "Upload statement"}
      </button>

      {result && <UploadResult result={result} />}
    </form>
  );
}

function UploadResult({ result }: { result: UploadActionResult }) {
  if (!result.ok) {
    return (
      <p role="alert" className="rounded-md border border-danger-600/20 bg-danger-50 px-3 py-2 text-sm text-danger-600">
        {result.error}
      </p>
    );
  }

  const { transactions_imported, transactions_skipped, skipped_rows } = result.data;

  return (
    <div className="rounded-md border border-success-600/20 bg-success-50 px-4 py-3">
      <p className="text-sm font-medium text-success-600">
        Imported <span className="font-mono">{transactions_imported}</span> transaction
        {transactions_imported === 1 ? "" : "s"}.
      </p>
      {transactions_skipped > 0 && (
        <div className="mt-2 border-t border-success-600/20 pt-2">
          <p className="text-xs text-text-secondary">
            Skipped <span className="font-mono">{transactions_skipped}</span> row
            {transactions_skipped === 1 ? "" : "s"}:
          </p>
          <ul className="mt-1 space-y-0.5">
            {skipped_rows.map((row) => (
              <li key={row.row_number} className="text-xs text-text-secondary">
                <span className="font-mono">row {row.row_number}</span>: {row.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
