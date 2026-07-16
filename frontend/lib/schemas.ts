import { z } from "zod";

export const ACCOUNT_PURPOSES = ["income", "spending", "savings", "other"] as const;

export const AccountSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  purpose: z.enum(ACCOUNT_PURPOSES),
  is_tracked: z.boolean(),
});
export type Account = z.infer<typeof AccountSchema>;

export const SkippedRowSchema = z.object({
  row_number: z.number().int(),
  reason: z.string(),
});
export type SkippedRow = z.infer<typeof SkippedRowSchema>;

export const StatementUploadResponseSchema = z.object({
  statement_id: z.string().uuid(),
  status: z.string(),
  transactions_imported: z.number().int(),
  transactions_skipped: z.number().int(),
  skipped_rows: z.array(SkippedRowSchema),
});
export type StatementUploadResponse = z.infer<typeof StatementUploadResponseSchema>;

export const CATEGORY_TYPES = ["income", "fixed_expense", "variable_expense"] as const;

export const CategorySchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  type: z.enum(CATEGORY_TYPES),
});
export type Category = z.infer<typeof CategorySchema>;

export const TransactionSchema = z.object({
  id: z.string().uuid(),
  txn_date: z.string(),
  raw_description: z.string(),
  amount: z.string(), // Decimal, serialized as a string -- never parse as float
  direction: z.enum(["debit", "credit"]),
  account_name: z.string(),
  category_id: z.string().uuid().nullable(),
  category_name: z.string().nullable(),
  confidence: z.string().nullable(),
  needs_review: z.boolean(),
  is_internal_transfer: z.boolean(),
});
export type Transaction = z.infer<typeof TransactionSchema>;

export const CategoryTotalSchema = z.object({
  category_id: z.string().uuid(),
  name: z.string(),
  type: z.enum(CATEGORY_TYPES),
  total: z.string(),
});
export type CategoryTotal = z.infer<typeof CategoryTotalSchema>;

export const MonthlySummarySchema = z.object({
  month: z.string(),
  total_income: z.string(),
  total_fixed_expenses: z.string(),
  total_variable_expenses: z.string(),
  discretionary_income: z.string(),
  pending_review_count: z.number().int(),
  by_category: z.array(CategoryTotalSchema),
});
export type MonthlySummary = z.infer<typeof MonthlySummarySchema>;

// Client-side pre-validation, so an obviously bad file never leaves the browser.
export const ALLOWED_EXTENSIONS = ["csv", "xlsx", "xls", "pdf"] as const;
export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export function validateStatementFile(file: File): string | null {
  if (file.size === 0) return "the file is empty";
  if (file.size > MAX_FILE_SIZE_BYTES) return "file must be under 10 MB";
  const ext = file.name.split(".").pop()?.toLowerCase();
  if (!ext || !(ALLOWED_EXTENSIONS as readonly string[]).includes(ext)) {
    return "unsupported file type -- use CSV, XLSX, or PDF";
  }
  return null;
}
