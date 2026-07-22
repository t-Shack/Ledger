"use client";

import { useState, useTransition, useEffect } from "react";
import { correctCategory } from "./actions";
import { getReviewQueue } from "@/lib/transactions";
import type { Category, Transaction } from "@/lib/schemas";

export function ReviewList({ transactions, categories }: { transactions: Transaction[]; categories: Category[] }) {
  const [items, setItems] = useState(transactions);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Refetch review queue on mount to get any new transactions
  useEffect(() => {
    const refreshTransactions = async () => {
      try {
        const result = await getReviewQueue();
        if (result.ok) {
          setItems(result.data);
        } else {
          console.error("Failed to fetch review queue:", result.error);
        }
      } catch (error) {
        console.error("Failed to refresh transactions:", error);
      }
    };
    refreshTransactions();
  }, []);

  function handleResolved(id: string) {
    // Refetch the entire list after confirming, rather than just removing from state
    // This ensures we always have the latest data from the database
    setIsRefreshing(true);
    const refreshTransactions = async () => {
      try {
        const result = await getReviewQueue();
        if (result.ok) {
          setItems(result.data);
        } else {
          console.error("Failed to fetch review queue:", result.error);
        }
      } catch (error) {
        console.error("Failed to refresh transactions:", error);
      } finally {
        setIsRefreshing(false);
      }
    };
    refreshTransactions();
  }

  if (items.length === 0) {
    return <p className="mt-8 text-sm text-text-secondary">All caught up -- nothing needs review.</p>;
  }

  return (
    <ul className="mt-8 divide-y divide-border">
      {items.map((t) => (
        <ReviewRow key={t.id} transaction={t} categories={categories} onResolved={handleResolved} isRefreshing={isRefreshing} />
      ))}
    </ul>
  );
}

function ReviewRow({
  transaction,
  categories,
  onResolved,
  isRefreshing,
}: {
  transaction: Transaction;
  categories: Category[];
  onResolved: (id: string) => void;
  isRefreshing: boolean;
}) {
  const [categoryId, setCategoryId] = useState(transaction.category_id ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleConfirm() {
    if (!categoryId) {
      setError("choose a category");
      return;
    }
    setError(null);
    startTransition(async () => {
      const outcome = await correctCategory(transaction.id, categoryId);
      if (!outcome.ok) {
        setError(outcome.error);
        return;
      }
      onResolved(transaction.id);
    });
  }

  const confidencePct = transaction.confidence !== null ? Math.round(Number(transaction.confidence) * 100) : null;

  return (
    <li className="py-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-text-primary">{transaction.raw_description}</p>
          <p className="mt-0.5 text-xs text-text-secondary">
            {transaction.account_name} · {transaction.txn_date}
          </p>
          {transaction.category_name && (
            <p className="mt-1 text-xs text-text-secondary">
              AI suggests <span className="text-text-primary">{transaction.category_name}</span>
              {confidencePct !== null && <span className="font-mono"> ({confidencePct}%)</span>}
            </p>
          )}
        </div>
        <p className="whitespace-nowrap font-mono text-sm text-text-primary">
          {transaction.direction === "debit" ? "-" : "+"}
          {transaction.amount}
        </p>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="flex-1 rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus-visible:border-accent-600"
        >
          <option value="" disabled>
            Choose a category
          </option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={isPending || isRefreshing}
          className="whitespace-nowrap rounded-md bg-accent-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-accent-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isPending ? "Saving…" : isRefreshing ? "Updating…" : "Confirm"}
        </button>
      </div>
      {error && (
        <p role="alert" className="mt-2 text-xs text-danger-600">
          {error}
        </p>
      )}
    </li>
  );
}
