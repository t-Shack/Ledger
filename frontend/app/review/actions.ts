"use server";

import { z } from "zod";
import { apiFetch, type Result } from "@/lib/api-client";
import { TransactionSchema, type Transaction } from "@/lib/schemas";

const InputSchema = z.object({
  transactionId: z.string().uuid(),
  categoryId: z.string().uuid(),
});

export async function correctCategory(transactionId: string, categoryId: string): Promise<Result<Transaction>> {
  const parsed = InputSchema.safeParse({ transactionId, categoryId });
  if (!parsed.success) {
    return { ok: false, error: "invalid transaction or category" };
  }

  return apiFetch(`/transactions/${parsed.data.transactionId}/category`, TransactionSchema, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category_id: parsed.data.categoryId }),
  });
}
