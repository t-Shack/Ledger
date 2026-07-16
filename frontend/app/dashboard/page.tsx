import { getMonthlySummary } from "@/lib/summary";
import type { CategoryTotal, MonthlySummary } from "@/lib/schemas";
import { MonthPicker } from "./month-picker";

function currentMonthValue(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function toApiDate(monthValue: string): string {
  return `${monthValue}-01`;
}

export default async function DashboardPage({ searchParams }: { searchParams: { month?: string } }) {
  const monthValue = searchParams.month ?? currentMonthValue();
  const result = await getMonthlySummary(toApiDate(monthValue));

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-medium text-text-primary">Dashboard</h1>
        <MonthPicker value={monthValue} />
      </div>

      {!result.ok ? (
        <p className="mt-6 rounded-md border border-danger-600/20 bg-danger-50 px-4 py-3 text-sm text-danger-600">
          The summary didn't load: {result.error}
        </p>
      ) : (
        <DashboardContent summary={result.data} />
      )}
    </main>
  );
}

function DashboardContent({ summary }: { summary: MonthlySummary }) {
  const isSurplus = !summary.discretionary_income.startsWith("-");

  const bySection: Record<string, CategoryTotal[]> = { income: [], fixed_expense: [], variable_expense: [] };
  for (const c of summary.by_category) {
    bySection[c.type]?.push(c);
  }

  return (
    <>
      <div className="mt-8 rounded-lg border border-border p-6">
        <p className="text-sm text-text-secondary">Discretionary income</p>
        <p className={`mt-1 font-mono text-3xl font-medium ${isSurplus ? "text-success-600" : "text-danger-600"}`}>
          {isSurplus ? "+" : ""}
          {summary.discretionary_income}
        </p>
      </div>

      {summary.pending_review_count > 0 && (
        <p className="mt-4 rounded-md border border-accent-600/20 bg-accent-50 px-4 py-3 text-sm text-text-primary">
          <span className="font-mono">{summary.pending_review_count}</span> transaction
          {summary.pending_review_count === 1 ? "" : "s"} still need review and aren't counted above --{" "}
          <a href="/review" className="font-medium text-accent-700 underline">
            review now
          </a>
          .
        </p>
      )}

      <div className="mt-8 space-y-8">
        <Section title="Income" total={summary.total_income} items={bySection.income ?? []} />
        <Section title="Fixed expenses" total={summary.total_fixed_expenses} items={bySection.fixed_expense ?? []} />
        <Section
          title="Variable expenses"
          total={summary.total_variable_expenses}
          items={bySection.variable_expense ?? []}
        />
      </div>
    </>
  );
}

function Section({ title, total, items }: { title: string; total: string; items: CategoryTotal[] }) {
  return (
    <div>
      <div className="flex items-baseline justify-between border-b border-border pb-2">
        <h2 className="font-display text-base font-medium text-text-primary">{title}</h2>
        <p className="font-mono text-sm text-text-primary">{total}</p>
      </div>
      {items.length === 0 ? (
        <p className="mt-3 text-sm text-text-secondary">No confirmed transactions this month.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {items.map((c) => (
            <li key={c.category_id} className="flex items-baseline justify-between text-sm">
              <span className="text-text-secondary">{c.name}</span>
              <span className="font-mono text-text-primary">{c.total}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
