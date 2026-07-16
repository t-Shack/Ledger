import { getAccounts } from "@/lib/accounts";
import { UploadForm } from "./upload-form";

export default async function UploadPage() {
  const result = await getAccounts();

  if (!result.ok) {
    return (
      <main className="mx-auto max-w-md px-6 py-16">
        <h1 className="font-display text-2xl font-medium text-text-primary">Upload a statement</h1>
        <p className="mt-4 rounded-md border border-danger-600/20 bg-danger-50 px-4 py-3 text-sm text-danger-600">
          Your accounts didn't load: {result.error}
        </p>
      </main>
    );
  }

  if (result.data.length === 0) {
    return (
      <main className="mx-auto max-w-md px-6 py-16">
        <h1 className="font-display text-2xl font-medium text-text-primary">Upload a statement</h1>
        <p className="mt-4 text-sm text-text-secondary">
          No accounts yet. Add one, like Opay or Palmpay, before uploading a statement.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <h1 className="font-display text-2xl font-medium text-text-primary">Upload a statement</h1>
      <p className="mt-2 text-sm text-text-secondary">Pick an account and drop in a CSV, XLSX, or PDF export.</p>
      <UploadForm accounts={result.data} />
    </main>
  );
}
