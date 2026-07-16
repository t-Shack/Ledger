"use client";

import { useRouter } from "next/navigation";

export function MonthPicker({ value }: { value: string }) {
  const router = useRouter();

  return (
    <input
      type="month"
      value={value}
      onChange={(e) => {
        if (e.target.value) router.push(`/dashboard?month=${e.target.value}`);
      }}
      aria-label="Select month"
      className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus-visible:border-accent-600"
    />
  );
}
