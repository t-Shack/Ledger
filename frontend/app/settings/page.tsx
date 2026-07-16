import { getAccounts } from "@/lib/accounts";
import { getCategories } from "@/lib/categories";
import { AccountsSection } from "./accounts-section";
import { CategoriesSection } from "./categories-section";

export default async function SettingsPage() {
  const [accountsResult, categoriesResult] = await Promise.all([getAccounts(), getCategories()]);

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="font-display text-2xl font-medium text-text-primary">Accounts &amp; categories</h1>

      <section className="mt-10">
        <h2 className="font-display text-lg font-medium text-text-primary">Accounts</h2>
        {!accountsResult.ok ? (
          <p className="mt-3 rounded-md border border-danger-600/20 bg-danger-50 px-4 py-3 text-sm text-danger-600">
            Accounts didn't load: {accountsResult.error}
          </p>
        ) : (
          <AccountsSection accounts={accountsResult.data} />
        )}
      </section>

      <section className="mt-12">
        <h2 className="font-display text-lg font-medium text-text-primary">Categories</h2>
        {!categoriesResult.ok ? (
          <p className="mt-3 rounded-md border border-danger-600/20 bg-danger-50 px-4 py-3 text-sm text-danger-600">
            Categories didn't load: {categoriesResult.error}
          </p>
        ) : (
          <CategoriesSection categories={categoriesResult.data} />
        )}
      </section>
    </main>
  );
}
