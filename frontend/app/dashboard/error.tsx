"use client";

export default function DashboardError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="font-display text-2xl font-medium text-text-primary">Something went wrong</h1>
      <p className="mt-2 text-sm text-text-secondary">The dashboard hit an unexpected error.</p>
      <button
        onClick={reset}
        className="mt-6 rounded-md bg-accent-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-accent-700"
      >
        Try again
      </button>
    </main>
  );
}
