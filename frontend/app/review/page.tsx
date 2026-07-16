import { getCategories } from "@/lib/categories";
import { getReviewQueue } from "@/lib/transactions";
import { ReviewList } from "./review-list";

export default async function ReviewPage() {
  const [transactionsResult, categoriesResult] = await Promise.all([getReviewQueue(), getCategories()]);

  if (!transactionsResult.ok) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-16">
        <h1 className="font-display text-2xl font-medium text-text-primary">Review queue</h1>
        <p className="mt-4 rounded-md border border-danger-600/20 bg-danger-50 px-4 py-3 text-sm text-danger-600">
          Transactions didn't load: {transactionsResult.error}
        </p>
      </main>
    );
  }

  if (!categoriesResult.ok) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-16">
        <h1 className="font-display text-2xl font-medium text-text-primary">Review queue</h1>
        <p className="mt-4 rounded-md border border-danger-600/20 bg-danger-50 px-4 py-3 text-sm text-danger-600">
          Categories didn't load: {categoriesResult.error}
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="font-display text-2xl font-medium text-text-primary">Review queue</h1>
      <p className="mt-2 text-sm text-text-secondary">Confirm or correct the category for each flagged transaction.</p>
      <ReviewList transactions={transactionsResult.data} categories={categoriesResult.data} />
    </main>
  );
}
