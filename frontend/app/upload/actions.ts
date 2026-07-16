"use server";

import { z } from "zod";
import { apiFetch, type Result } from "@/lib/api-client";
import { StatementUploadResponseSchema, type StatementUploadResponse } from "@/lib/schemas";

export type UploadActionResult = Result<StatementUploadResponse>;

const AccountIdSchema = z.string().uuid();

export async function uploadStatement(formData: FormData): Promise<UploadActionResult> {
  const file = formData.get("file");
  if (!(file instanceof File)) {
    return { ok: false, error: "no file was received" };
  }
  if (file.size === 0) {
    return { ok: false, error: "the file is empty" };
  }

  const rawAccountId = formData.get("account_id");
  const parsedAccountId = AccountIdSchema.safeParse(rawAccountId);
  if (!parsedAccountId.success) {
    return { ok: false, error: "choose a valid account" };
  }

  const backendForm = new FormData();
  backendForm.set("file", file, file.name);

  return apiFetch(`/accounts/${parsedAccountId.data}/statements`, StatementUploadResponseSchema, {
    method: "POST",
    body: backendForm,
  });
}
