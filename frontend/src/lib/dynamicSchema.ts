import { z } from "zod";
import type { PageConfigField } from "@/hooks/usePageConfig";

export function buildZodSchema(
  fields: PageConfigField[],
  visibilityMap: Record<string, boolean> = {}
) {
  const shape: Record<string, z.ZodTypeAny> = {};

  for (const field of fields) {
    const isFieldVisible = visibilityMap[field.field_name] !== false && !field.hidden;

    if (!isFieldVisible || field.readonly) {
      shape[field.field_name] = z.any().optional();
      continue;
    }

    let fieldSchema: z.ZodTypeAny;

    if (field.field_type === "number" || field.field_type === "decimal") {
      let baseNumSchema = z.number({
        error: "Invalid number",
      });

      if (field.min_value !== null && field.min_value !== undefined) {
        baseNumSchema = baseNumSchema.min(field.min_value, {
          message: `Minimum value is ${field.min_value}`,
        });
      }

      if (field.max_value !== null && field.max_value !== undefined) {
        baseNumSchema = baseNumSchema.max(field.max_value, {
          message: `Maximum value is ${field.max_value}`,
        });
      }

      if (field.required) {
        fieldSchema = z.preprocess((val) => {
          if (val === "" || val === undefined || val === null) return undefined;
          const parsed = Number(val);
          return isNaN(parsed) ? val : parsed;
        }, baseNumSchema);
      } else {
        fieldSchema = z.preprocess((val) => {
          if (val === "" || val === undefined || val === null) return null;
          const parsed = Number(val);
          return isNaN(parsed) ? val : parsed;
        }, baseNumSchema.nullable().optional());
      }
    } else if (
      field.field_type === "boolean" ||
      field.field_type === "toggle" ||
      field.field_type === "checkbox"
    ) {
      const boolSchema = z.boolean({
        error: "Must be a boolean",
      });
      if (field.required) {
        fieldSchema = boolSchema;
      } else {
        fieldSchema = boolSchema.optional().nullable();
      }
    } else {
      // Default string schemas
      let strSchema = z.string({
        error: "Must be a string",
      });

      if (field.field_type === "email") {
        strSchema = strSchema.email({ message: "Invalid email format" });
      }

      if (field.min_length !== null && field.min_length !== undefined) {
        strSchema = strSchema.min(field.min_length, {
          message: `Minimum ${field.min_length} characters required`,
        });
      }

      if (field.max_length !== null && field.max_length !== undefined) {
        strSchema = strSchema.max(field.max_length, {
          message: `Maximum ${field.max_length} characters allowed`,
        });
      }

      if (field.pattern) {
        try {
          const regex = new RegExp(field.pattern);
          strSchema = strSchema.regex(regex, {
            message: `Invalid format for ${field.label}`,
          });
        } catch {
          // ignore invalid regex pattern
        }
      }

      if (field.required) {
        strSchema = strSchema.min(1, { message: `${field.label} is required` });
        fieldSchema = strSchema;
      } else {
        fieldSchema = strSchema.optional().or(z.literal("")).nullable();
      }
    }

    shape[field.field_name] = fieldSchema;
  }

  return z.object(shape);
}
