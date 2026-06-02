import { useState, useCallback } from "react";
import type { PageConfigField } from "@/hooks/usePageConfig";

export type ValidationErrors = Record<string, string | undefined>;

export interface UseFieldValidationReturn {
  errors: ValidationErrors;
  validate: (field: PageConfigField, value: unknown) => string | undefined;
  validateAll: (fields: PageConfigField[], values: Record<string, unknown>) => boolean;
  clearErrors: () => void;
  clearFieldError: (fieldName: string) => void;
}

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateField(
  field: PageConfigField,
  value: unknown
): string | undefined {
  if (field.required && (value === undefined || value === null || value === "")) {
    return `${field.label} is required`;
  }

  if (!value && value !== 0 && value !== false) return undefined;

  const strVal = String(value);

  if (field.field_type === "email") {
    if (!emailRegex.test(strVal)) {
      return "Invalid email format";
    }
  }

  if (
    field.min_length !== null &&
    field.min_length !== undefined &&
    strVal.length < field.min_length
  ) {
    return `Minimum ${field.min_length} characters required`;
  }

  if (
    field.max_length !== null &&
    field.max_length !== undefined &&
    strVal.length > field.max_length
  ) {
    return `Maximum ${field.max_length} characters allowed`;
  }

  if (field.field_type === "number" || field.field_type === "decimal") {
    const num = Number(value);
    if (isNaN(num)) return "Invalid number";

    if (
      field.min_value !== null &&
      field.min_value !== undefined &&
      num < field.min_value
    ) {
      return `Minimum value is ${field.min_value}`;
    }
    if (
      field.max_value !== null &&
      field.max_value !== undefined &&
      num > field.max_value
    ) {
      return `Maximum value is ${field.max_value}`;
    }
  }

  if (field.pattern) {
    try {
      const regex = new RegExp(field.pattern);
      if (!regex.test(strVal)) {
        return `Invalid format for ${field.label}`;
      }
    } catch { /* invalid pattern */ }
  }

  return undefined;
}

export function useFieldValidation(): UseFieldValidationReturn {
  const [errors, setErrors] = useState<ValidationErrors>({});

  const validate = useCallback(
    (field: PageConfigField, value: unknown): string | undefined => {
      const error = validateField(field, value);
      setErrors((prev) => ({ ...prev, [field.field_name]: error }));
      return error;
    },
    []
  );

  const validateAll = useCallback(
    (fields: PageConfigField[], values: Record<string, unknown>): boolean => {
      const newErrors: ValidationErrors = {};
      let hasError = false;

      for (const field of fields) {
        if (field.hidden || field.readonly) continue;
        const error = validateField(field, values[field.field_name]);
        if (error) {
          newErrors[field.field_name] = error;
          hasError = true;
        }
      }

      setErrors(newErrors);
      return !hasError;
    },
    []
  );

  const clearErrors = useCallback(() => setErrors({}), []);
  const clearFieldError = useCallback((fieldName: string) => {
    setErrors((prev) => ({ ...prev, [fieldName]: undefined }));
  }, []);

  return { errors, validate, validateAll, clearErrors, clearFieldError };
}
