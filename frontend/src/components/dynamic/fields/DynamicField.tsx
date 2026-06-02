import type { PageConfigField } from "@/hooks/usePageConfig";
import TextField from "./TextField";
import NumberField from "./NumberField";
import DecimalField from "./DecimalField";
import TextareaField from "./TextareaField";
import SelectField from "./SelectField";
import MultiSelectField from "./MultiSelectField";
import AutocompleteField from "./AutocompleteField";
import DateField from "./DateField";
import DateTimeField from "./DateTimeField";
import TimeField from "./TimeField";
import ToggleField from "./ToggleField";
import CheckboxField from "./CheckboxField";
import RadioField from "./RadioField";
import FileField from "./FileField";
import ImageField from "./ImageField";
import CurrencyField from "./CurrencyField";
import PercentageField from "./PercentageField";
import HeadingField from "./HeadingField";
import SeparatorField from "./SeparatorField";
import SpacerField from "./SpacerField";
import InlineTableField from "./InlineTableField";
import ReadonlyTextField from "./ReadonlyTextField";
import BadgeField from "./BadgeField";

interface DynamicFieldProps {
  field: PageConfigField;
  value: unknown;
  onChange: (name: string, value: unknown) => void;
  error?: string;
  disabled?: boolean;
}

const fieldComponents: Record<string, React.ComponentType<DynamicFieldProps>> = {
  text: TextField,
  email: TextField,
  number: NumberField,
  decimal: DecimalField,
  textarea: TextareaField,
  select: SelectField,
  multi_select: MultiSelectField,
  autocomplete: AutocompleteField,
  date: DateField,
  datetime: DateTimeField,
  time: TimeField,
  toggle: ToggleField,
  checkbox: CheckboxField,
  radio: RadioField,
  file: FileField,
  image: ImageField,
  currency: CurrencyField,
  percentage: PercentageField,
  heading: HeadingField,
  separator: SeparatorField,
  spacer: SpacerField,
  inline_table: InlineTableField,
  readonly_text: ReadonlyTextField,
  badge: BadgeField,
};

export default function DynamicField(props: DynamicFieldProps) {
  const { field } = props;
  const Component = fieldComponents[field.field_type];

  if (!Component) {
    return (
      <div className="text-sm text-secondary-500">
        Unknown field type: {field.field_type}
      </div>
    );
  }

  return <Component {...props} />;
}
