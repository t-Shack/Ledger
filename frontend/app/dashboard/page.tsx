import { getMonthlySummary } from "@/lib/summary";
import type { CategoryTotal, MonthlySummary } from "@/lib/schemas";
import { MonthPicker } from "./month-picker";
import { DashboardContent } from "./dashboard-content";

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
        <DashboardContent summary={result.data} monthValue={monthValue} />
      )}
    </main>
  );
}
