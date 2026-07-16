import { apiFetch, type Result } from "./api-client";
import { MonthlySummarySchema, type MonthlySummary } from "./schemas";

export async function getMonthlySummary(month: string): Promise<Result<MonthlySummary>> {
  return apiFetch(`/summary?month=${encodeURIComponent(month)}`, MonthlySummarySchema);
}
