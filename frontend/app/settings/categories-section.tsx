"use client";

import { useState, useTransition } from "react";
import { createCategory } from "./actions";
import { CATEGORY_TYPES, type Category } from "@/lib/schemas";

type CategoryType = (typeof CATEGORY_TYPES)[number];

const TYPE_LABELS: Record<CategoryType, string> = {
  income: "Income",
  fixed_expense: "Fixed expenses",
  variable_expense: "Variable expenses",
};

export function CategoriesSection({ categories: initial }: { categories: Category[] }) {
  const [categories, setCategories] = useState(initial);
  const [name, setName] = useState("");
  const [type, setType] = useState<CategoryType>("variable_expense");
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
    formData.set("type", type);

    startTransition(async () => {
      const outcome = await createCategory(formData);
      if (!outcome.ok) {
        setFormError(outcome.error);
        return;
      }
      setCategories((prev) => [...prev, outcome.data]);
      setName("");
    });
  }

  return (
    <div className="mt-3">
      {CATEGORY_TYPES.map((t) => {
        const items = categories.filter((c) => c.type === t);
        return (
          <div key={t} className="mt-4 first:mt-0">
            <h3 className="text-xs font-medium uppercase tracking-wide text-text-secondary">{TYPE_LABELS[t]}</h3>
            <ul className="mt-2 flex flex-wrap gap-2">
              {items.map((c) => (
                <li key={c.id} className="rounded-full border border-border px-3 py-1 text-xs text-text-primary">
                  {c.name}
                </li>
              ))}
            </ul>
          </div>
        );
      })}

      <form onSubmit={handleCreate} className="mt-6 flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="category-name" className="block text-xs font-medium text-text-primary">
            Name
          </label>
          <input
            id="category-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Data & Airtime"
            className="mt-1 w-48 rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus-visible:border-accent-600"
          />
        </div>
        <div>
          <label htmlFor="category-type" className="block text-xs font-medium text-text-primary">
            Section
          </label>
          <select
            id="category-type"
            value={type}
            onChange={(e) => setType(e.target.value as CategoryType)}
            className="mt-1 rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus-visible:border-accent-600"
          >
            {CATEGORY_TYPES.map((t) => (
              <option key={t} value={t}>
                {TYPE_LABELS[t]}
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={isPending}
          className="rounded-md bg-accent-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-accent-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isPending ? "Adding…" : "Add category"}
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
