import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export interface Attachment {
  id: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  description: string;
  uploaded_by_name: string;
  uploaded_by_id: string;
  created_at: string;
  download_url: string;
}

export function useAttachments(contentType: string, objectId: string | undefined) {
  const queryClient = useQueryClient();
  const queryKey = ["attachments", contentType, objectId];

  const { data: attachments = [], isLoading } = useQuery({
    queryKey,
    queryFn: async (): Promise<Attachment[]> => {
      if (!contentType || !objectId) return [];
      const { data } = await api.get(`/core/attachments/list/${contentType}/${objectId}/`);
      return data;
    },
    enabled: !!contentType && !!objectId,
    staleTime: 30 * 1000,
  });

  const uploadMutation = useMutation({
    mutationFn: async ({
      file,
      description,
    }: {
      file: File;
      description?: string;
    }): Promise<Attachment> => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("content_type_label", contentType);
      formData.append("object_id", objectId!);
      if (description) formData.append("description", description);

      const { data } = await api.post("/core/attachments/upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: () => {},
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });

  const removeMutation = useMutation({
    mutationFn: async (attachmentId: string) => {
      await api.delete(`/core/attachments/${attachmentId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });

  return {
    attachments,
    isLoading,
    isUploading: uploadMutation.isPending,
    upload: (file: File, description?: string) => uploadMutation.mutateAsync({ file, description }),
    remove: (attachmentId: string) => removeMutation.mutateAsync(attachmentId),
  };
}
