import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";

export interface Company {
  id: string;
  name: string;
  code: string;
  registration_number?: string;
  tax_number?: string;
  is_active?: boolean;
  parent_id?: string | null;
  is_group?: boolean;
  address?: string;
  city?: string;
  state?: string;
  postcode?: string;
  country?: string;
  phone?: string;
  email?: string;
  base_currency?: string;
  date_format?: string;
  timezone?: string;
  logo?: string;
}

export function useCurrentCompany() {
  const { user } = useAuth();
  return {
    company: user?.current_company ?? null,
    companies: user?.companies ?? [],
  };
}

export function useCompanies() {
  return useQuery({
    queryKey: ["companies"],
    queryFn: async (): Promise<Company[]> => {
      const { data } = await api.get("/core/companies/");
      return data.results || data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompanyContext() {
  return useQuery({
    queryKey: ["currentCompany"],
    queryFn: async (): Promise<Company> => {
      const { data } = await api.get("/core/companies/current/");
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompanyMutations() {
  const queryClient = useQueryClient();

  const switchCompany = useMutation({
    mutationFn: async (companyId: string) => {
      const { data } = await api.post("/core/companies/switch/", {
        id: companyId,
        name: "",
        code: "",
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["currentCompany"] });
      queryClient.invalidateQueries({ queryKey: ["companies"] });
    },
  });

  const setDefault = useMutation({
    mutationFn: async (companyId: string) => {
      const { data } = await api.put("/core/companies/default/", {
        id: companyId,
        name: "",
        code: "",
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["currentCompany"] });
    },
  });

  return { switchCompany, setDefault };
}
