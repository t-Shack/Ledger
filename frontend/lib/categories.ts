import { z } from "zod";
import { apiFetch, type Result } from "./api-client";
import { CategorySchema, type Category } from "./schemas";

export async function getCategories(): Promise<Result<Category[]>> {
  return apiFetch("/categories", z.array(CategorySchema));
}
