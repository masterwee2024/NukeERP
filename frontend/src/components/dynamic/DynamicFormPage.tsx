import { useCallback, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { PageConfig, PageConfigField } from "@/hooks/usePageConfig";
import { useViewport } from "@/hooks/useViewport";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import DynamicField from "./fields/DynamicField";
import FieldGroup from "./FieldGroup";
import TabGroup from "./TabGroup";
import GridLayout from "./GridLayout";
import ResponsiveFieldFilter from "./ResponsiveFieldFilter";
import ConditionalEngine from "./ConditionalEngine";
import {
  useForm,
  Controller,
  type FieldValues,
  type Resolver,
  type Control,
  type FieldErrors,
} from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { buildZodSchema } from "@/lib/dynamicSchema";
import { evaluateVisibility } from "@/hooks/useConditionalDisplay";

interface DynamicFormPageProps {
  config: PageConfig;
  recordId?: string;
  showTitle?: boolean;
  onCancel?: () => void;
  onSuccess?: (record: Record<string, unknown>) => void;
}

export default function DynamicFormPage({
  config,
  recordId,
  showTitle = true,
  onCancel,
  onSuccess,
}: DynamicFormPageProps) {
  const isEdit = !!recordId;
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();
  const { isMobile } = useViewport();

  const { data: record, isLoading: loadingRecord } = useQuery({
    queryKey: [config.api_endpoint, recordId],
    queryFn: async () => {
      if (!recordId) return {};
      const { data } = await api.get(`/${config.api_endpoint}/${recordId}/`);
      return data as Record<string, unknown>;
    },
    enabled: isEdit,
  });

  const resolver = useCallback<Resolver<FieldValues>>(
    (values, context, options) => {
      const visibility = evaluateVisibility(config.fields, values || {});
      const schema = buildZodSchema(config.fields, visibility);
      return zodResolver(schema)(values, context, options);
    },
    [config.fields]
  );

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FieldValues>({
    resolver,
    defaultValues: {},
  });

  useEffect(() => {
    if (record) {
      reset(record);
    }
  }, [record, reset]);

  const mutation = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      const payload: Record<string, unknown> = {
        ...values,
        ...(isEdit && record?.updated_at ? { updated_at: record.updated_at } : {}),
      };

      // Check if any value is a File or FileList
      let hasFile = false;
      for (const key of Object.keys(payload)) {
        const val = payload[key];
        if (val instanceof File || (val instanceof FileList && val.length > 0)) {
          hasFile = true;
          break;
        }
      }

      if (hasFile) {
        const formData = new FormData();
        for (const key of Object.keys(payload)) {
          const val = payload[key];
          if (val instanceof FileList) {
            for (let i = 0; i < val.length; i++) {
              formData.append(key, val[i]);
            }
          } else if (val instanceof File) {
            formData.append(key, val);
          } else if (val === null || val === undefined) {
            formData.append(key, "");
          } else if (typeof val === "object") {
            formData.append(key, JSON.stringify(val));
          } else {
            formData.append(key, String(val));
          }
        }

        const headers = { "Content-Type": "multipart/form-data" };
        if (isEdit) {
          const { data } = await api.put(
            `/${config.api_endpoint}/${recordId}/`,
            formData,
            { headers }
          );
          return data;
        } else {
          const { data } = await api.post(`/${config.api_endpoint}/`, formData, {
            headers,
          });
          return data;
        }
      } else {
        if (isEdit) {
          const { data } = await api.put(
            `/${config.api_endpoint}/${recordId}/`,
            payload
          );
          return data;
        } else {
          const { data } = await api.post(`/${config.api_endpoint}/`, payload);
          return data;
        }
      }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: [config.api_endpoint] });
      onSuccess?.(data);
    },
  });

  const onSubmit = async (data: FieldValues) => {
    const confirmed = await confirm({
      title: isEdit ? "Update Record" : "Create Record",
      message: `Are you sure you want to ${
        isEdit ? "update this" : "create a new"
      } record?`,
      variant: "warning",
    });

    if (!confirmed) return;
    mutation.mutate(data);
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
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="flex items-center justify-between">
        {showTitle && (
          <h2 className="text-lg font-semibold text-secondary-900">
            {isEdit ? `Edit ${config.page_title}` : `New ${config.page_title}`}
          </h2>
        )}
        <div className="flex gap-2 ml-auto">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="rounded-md border border-secondary-300 bg-white px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
            >
              Cancel
            </button>
          )}
          {config.actions.some(
            (a) =>
              a.label.toLowerCase() === "save" ||
              a.label.toLowerCase() === "submit"
          ) ? (
            config.actions
              .filter(
                (a) =>
                  a.label.toLowerCase() === "save" ||
                  a.label.toLowerCase() === "submit"
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
              ))
          ) : (
            <button
              type="submit"
              disabled={mutation.isPending}
              className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {mutation.isPending ? "Saving..." : "Save"}
            </button>
          )}
        </div>
      </div>

      <ConditionalEngine fields={config.fields} control={control}>
        {(visibility) => (
          <ResponsiveFieldFilter fields={config.fields} visibilityMap={visibility}>
            {(visibleFields) => {
              if (activeLayout === "tabs") {
                return renderTabs(visibleFields);
              }
              if (activeLayout === "single") {
                return renderFields(visibleFields, control, errors);
              }
              return renderFields(visibleFields, control, errors);
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
                <Controller
                  control={control}
                  name={f.field_name}
                  render={({ field: { onChange, value } }) => (
                    <DynamicField
                      field={f}
                      value={value}
                      onChange={onChange}
                      error={errors[f.field_name]?.message as string}
                    />
                  )}
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
                <Controller
                  control={control}
                  name={f.field_name}
                  render={({ field: { onChange, value } }) => (
                    <DynamicField
                      field={f}
                      value={value}
                      onChange={onChange}
                      error={errors[f.field_name]?.message as string}
                    />
                  )}
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
  control: Control<FieldValues>,
  errors: FieldErrors<FieldValues>
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
            <Controller
              control={control}
              name={f.field_name}
              render={({ field: { onChange, value } }) => (
                <DynamicField
                  field={f}
                  value={value}
                  onChange={onChange}
                  error={errors[f.field_name]?.message as string}
                />
              )}
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
                  <Controller
                    control={control}
                    name={f.field_name}
                    render={({ field: { onChange, value } }) => (
                      <DynamicField
                        field={f}
                        value={value}
                        onChange={onChange}
                        error={errors[f.field_name]?.message as string}
                      />
                    )}
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
                  <Controller
                    control={control}
                    name={f.field_name}
                    render={({ field: { onChange, value } }) => (
                      <DynamicField
                        field={f}
                        value={value}
                        onChange={onChange}
                        error={errors[f.field_name]?.message as string}
                      />
                    )}
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
