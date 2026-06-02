import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export interface Company {
  id: string;
  name: string;
  code: string;
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
