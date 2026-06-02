import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { MenuItem } from "@/types/menu";

async function fetchMenuTree(): Promise<MenuItem[]> {
  const { data } = await api.get("/core/menus/");
  return data;
}

export function useMenu() {
  return useQuery({
    queryKey: ["menus"],
    queryFn: fetchMenuTree,
    staleTime: 5 * 60 * 1000,
  });
}
