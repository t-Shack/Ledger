import { z } from "zod";
import { apiFetch, type Result } from "./api-client";
import { TransactionSchema, type Transaction } from "./schemas";

export async function getReviewQueue(): Promise<Result<Transaction[]>> {
  return apiFetch("/transactions?needs_review=true", z.array(TransactionSchema));
}
