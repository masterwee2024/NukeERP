import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import type { MenuItem } from "@/types/menu";

async function fetchMenuTree(): Promise<MenuItem[]> {
  const { data } = await axios.get("/api/v1/core/menus/");
  return data;
}

export function useMenu() {
  return useQuery({
    queryKey: ["menus"],
    queryFn: fetchMenuTree,
    staleTime: 5 * 60 * 1000,
  });
}
