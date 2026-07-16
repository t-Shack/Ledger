import { z } from "zod";
import { apiFetch, type Result } from "./api-client";
import { AccountSchema, type Account } from "./schemas";

export async function getAccounts(): Promise<Result<Account[]>> {
  return apiFetch("/accounts", z.array(AccountSchema));
}
