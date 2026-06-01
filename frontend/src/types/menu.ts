export interface MenuItem {
  id: string;
  name: string;
  slug: string;
  icon: string;
  url: string;
  level: number;
  module: string;
  sort_order: number;
  children: MenuItem[];
}

export interface MenuFlat {
  id: string;
  name: string;
  slug: string;
  icon: string;
  url: string;
  parent: string | null;
  sort_order: number;
  permission_codename: string;
  is_active: boolean;
  level: number;
  module: string;
  created_at: string;
  updated_at: string;
}
