import { useState, useCallback, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { PageConfig, PageConfigField } from "@/hooks/usePageConfig";
import { useFieldValidation } from "@/hooks/useFieldValidation";
import { useViewport } from "@/hooks/useViewport";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import DynamicField from "./fields/DynamicField";
import FieldGroup from "./FieldGroup";
import TabGroup from "./TabGroup";
import GridLayout from "./GridLayout";
import ResponsiveFieldFilter from "./ResponsiveFieldFilter";
import ConditionalEngine from "./ConditionalEngine";

interface DynamicFormPageProps {
  config: PageConfig;
  recordId?: string;
}

export default function DynamicFormPage({ config, recordId }: DynamicFormPageProps) {
  const isEdit = !!recordId;
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();
  const { errors, validateAll, clearFieldError } = useFieldValidation();
  const { isMobile } = useViewport();

  const { data: record, isLoading: loadingRecord } = useQuery({
    queryKey: [config.api_endpoint, recordId],
    queryFn: async () => {
      if (!recordId) return {};
      const { data } = await api.get(`/${config.api_endpoint}${recordId}/`);
      return data as Record<string, unknown>;
    },
    enabled: isEdit,
  });

  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const prevRecordIdRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (isEdit && record && recordId !== prevRecordIdRef.current) {
      prevRecordIdRef.current = recordId;
      setFormValues(record as Record<string, unknown>);
    }
  }, [isEdit, record, recordId]);

  const mutation = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      const payload = {
        ...values,
        ...(isEdit && record?.updated_at ? { updated_at: record.updated_at } : {}),
      };
      if (isEdit) {
        const { data } = await api.put(`/${config.api_endpoint}${recordId}/`, payload);
        return data;
      } else {
        const { data } = await api.post(`/${config.api_endpoint}/`, payload);
        return data;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [config.api_endpoint] });
    },
  });

  const handleChange = useCallback(
    (name: string, value: unknown) => {
      setFormValues((prev) => ({ ...prev, [name]: value }));
      clearFieldError(name);
    },
    [clearFieldError]
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const isValid = validateAll(config.fields, formValues);
    if (!isValid) return;

    const confirmed = await confirm({
      title: isEdit ? "Update Record" : "Create Record",
      message: `Are you sure you want to ${isEdit ? "update this" : "create a new"} record?`,
      variant: "warning",
    });

    if (!confirmed) return;
    mutation.mutate(formValues);
  };

  const activeLayout = isMobile ? config.mobile_layout : config.desktop_layout;

  if (isEdit && loadingRecord) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-secondary-200 border-t-primary-600" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-secondary-900">
          {isEdit ? `Edit ${config.page_title}` : `New ${config.page_title}`}
        </h2>
        <div className="flex gap-2">
          {config.actions
            .filter(
              (a) =>
                a.label.toLowerCase() === "save" || a.label.toLowerCase() === "submit"
            )
            .map((action) => (
              <button
                key={action.label}
                type="submit"
                disabled={mutation.isPending}
                className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {mutation.isPending ? "Saving..." : action.label}
              </button>
            ))}
        </div>
      </div>

      <ConditionalEngine fields={config.fields} formValues={formValues}>
        {(visibility) => (
          <ResponsiveFieldFilter fields={config.fields} visibilityMap={visibility}>
            {(visibleFields) => {
              if (activeLayout === "tabs") {
                return renderTabs(visibleFields);
              }
              if (activeLayout === "single") {
                return renderFields(visibleFields, formValues, errors, handleChange);
              }
              return renderFields(visibleFields, formValues, errors, handleChange);
            }}
          </ResponsiveFieldFilter>
        )}
      </ConditionalEngine>

      {mutation.error && (
        <div className="rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
          {mutation.error instanceof Error
            ? mutation.error.message
            : "An error occurred"}
        </div>
      )}
    </form>
  );

  function renderTabs(fields: typeof config.fields) {
    const groups = fields.filter((f) => f.group_name);
    const ungrouped = fields.filter((f) => !f.group_name);
    const tabNames = [...new Set(groups.map((f) => f.group_name))];

    const tabs = tabNames.map((name) => ({
      key: name,
      label: name.charAt(0).toUpperCase() + name.slice(1),
      content: (
        <GridLayout
          items={groups
            .filter((f) => f.group_name === name)
            .map((f) => ({
              key: f.field_name,
              colSpan: isMobile ? f.mobile_col_span : f.desktop_col_span,
              children: (
                <DynamicField
                  field={f}
                  value={formValues[f.field_name]}
                  onChange={handleChange}
                  error={errors[f.field_name]}
                />
              ),
            }))}
        />
      ),
    }));

    if (ungrouped.length > 0) {
      tabs.unshift({
        key: "_general",
        label: "General",
        content: (
          <GridLayout
            items={ungrouped.map((f) => ({
              key: f.field_name,
              colSpan: isMobile ? f.mobile_col_span : f.desktop_col_span,
              children: (
                <DynamicField
                  field={f}
                  value={formValues[f.field_name]}
                  onChange={handleChange}
                  error={errors[f.field_name]}
                />
              ),
            }))}
          />
        ),
      });
    }

    return <TabGroup tabs={tabs} />;
  }
}

function groupByGroupName(
  fields: PageConfigField[]
): Record<string, PageConfigField[]> {
  const groups: Record<string, PageConfigField[]> = {};
  for (const f of fields) {
    const key = f.group_name || "_ungrouped";
    if (!groups[key]) groups[key] = [];
    groups[key].push(f);
  }
  return groups;
}

function renderFields(
  fields: PageConfigField[],
  formValues: Record<string, unknown>,
  errors: Record<string, string | undefined>,
  handleChange: (name: string, value: unknown) => void,
) {
  const grouped = groupByGroupName(fields);
  const groupKeys = Object.keys(grouped);

  if (groupKeys.length === 1 && groupKeys[0] === "_ungrouped") {
    return (
      <GridLayout
        items={grouped["_ungrouped"].map((f) => ({
          key: f.field_name,
          colSpan: 6,
          children: (
            <DynamicField
              field={f}
              value={formValues[f.field_name]}
              onChange={handleChange}
              error={errors[f.field_name]}
            />
          ),
        }))}
      />
    );
  }

  return (
    <div className="space-y-4">
      {groupKeys.map((key) => {
        if (key === "_ungrouped") {
          return (
            <GridLayout
              key={key}
              items={grouped[key].map((f) => ({
                key: f.field_name,
                colSpan: 6,
                children: (
                  <DynamicField
                    field={f}
                    value={formValues[f.field_name]}
                    onChange={handleChange}
                    error={errors[f.field_name]}
                  />
                ),
              }))}
            />
          );
        }
        return (
          <FieldGroup key={key} title={key}>
            <GridLayout
              items={grouped[key].map((f) => ({
                key: f.field_name,
                colSpan: 6,
                children: (
                  <DynamicField
                    field={f}
                    value={formValues[f.field_name]}
                    onChange={handleChange}
                    error={errors[f.field_name]}
                  />
                ),
              }))}
            />
          </FieldGroup>
        );
      })}
    </div>
  );
}
