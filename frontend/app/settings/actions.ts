"use server";

import { z } from "zod";
import { apiFetch, type Result } from "@/lib/api-client";
import { AccountSchema, CategorySchema, ACCOUNT_PURPOSES, CATEGORY_TYPES, type Account, type Category } from "@/lib/schemas";

const AccountInputSchema = z.object({
  name: z.string().trim().min(1, "name is required").max(100),
  purpose: z.enum(ACCOUNT_PURPOSES),
  is_tracked: z.boolean(),
});

export async function createAccount(formData: FormData): Promise<Result<Account>> {
  const parsed = AccountInputSchema.safeParse({
    name: formData.get("name"),
    purpose: formData.get("purpose"),
    is_tracked: formData.get("is_tracked") === "on",
  });
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0]?.message ?? "invalid input" };
  }
  return apiFetch("/accounts", AccountSchema, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsed.data),
  });
}

const TrackedInputSchema = z.object({
  accountId: z.string().uuid(),
  isTracked: z.boolean(),
});

export async function setAccountTracked(accountId: string, isTracked: boolean): Promise<Result<Account>> {
  const parsed = TrackedInputSchema.safeParse({ accountId, isTracked });
  if (!parsed.success) {
    return { ok: false, error: "invalid account" };
  }
  return apiFetch(`/accounts/${parsed.data.accountId}`, AccountSchema, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_tracked: parsed.data.isTracked }),
  });
}

const CategoryInputSchema = z.object({
  name: z.string().trim().min(1, "name is required").max(100),
  type: z.enum(CATEGORY_TYPES),
});

export async function createCategory(formData: FormData): Promise<Result<Category>> {
  const parsed = CategoryInputSchema.safeParse({
    name: formData.get("name"),
    type: formData.get("type"),
  });
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0]?.message ?? "invalid input" };
  }
  return apiFetch("/categories", CategorySchema, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsed.data),
  });
}
