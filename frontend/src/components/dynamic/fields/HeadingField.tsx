import type { DynamicFieldProps } from "./types";

export default function HeadingField({ field }: DynamicFieldProps) {
  return (
    <h3 className="text-base font-semibold text-secondary-800 pt-4 first:pt-0">
      {field.label}
    </h3>
  );
}
