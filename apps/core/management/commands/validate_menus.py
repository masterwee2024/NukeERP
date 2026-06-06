"""Validate menu entries against routes and icon map."""

import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.models import Menu


class Command(BaseCommand):
    help = "Validate menu entries against frontend routes and icon map"

    def handle(self, *args, **options):
        errors = []

        # ── 1. Extract routes from App.tsx ──
        app_tsx = Path(settings.BASE_DIR) / "frontend" / "src" / "App.tsx"
        if not app_tsx.exists():
            self.stdout.write(
                self.style.WARNING("App.tsx not found, skipping route validation")
            )
            return

        route_text = app_tsx.read_text(encoding="utf-8")
        routes = set()
        for m in re.finditer(r'path="([^"]+)"', route_text):
            routes.add(m.group(1))

        # ── 2. Extract icon map keys from SidebarItem ──
        sidebar_item = (
            Path(settings.BASE_DIR)
            / "frontend"
            / "src"
            / "components"
            / "Layout"
            / "SidebarItem.tsx"
        )
        sidebar_group = (
            Path(settings.BASE_DIR)
            / "frontend"
            / "src"
            / "components"
            / "Layout"
            / "SidebarGroup.tsx"
        )
        icon_keys = set()
        for icon_file in [sidebar_item, sidebar_group]:
            if icon_file.exists():
                icon_text = icon_file.read_text(encoding="utf-8")
                for m in re.finditer(r"^\s+(\w+):", icon_text, re.MULTILINE):
                    icon_keys.add(m.group(1))

        # ── 3. Collect all menu items from seed file ──
        seed_file = (
            Path(settings.BASE_DIR)
            / "apps"
            / "core"
            / "management"
            / "commands"
            / "seed_menus.py"
        )
        if not seed_file.exists():
            self.stdout.write(
                self.style.WARNING("seed_menus.py not found, skipping seed validation")
            )
            return

        seed_text = seed_file.read_text(encoding="utf-8")
        seed_slugs = set(re.findall(r'"slug": "([^"]+)"', seed_text))
        seed_icons = set(re.findall(r'"icon": "([^"]+)"', seed_text))
        seed_urls = set()
        for m in re.finditer(r'"url": "([^"]+)"', seed_text):
            url = m.group(1)
            if url and url != "#":
                seed_urls.add(url)

        # ── 4. Build wildcard route matcher ──
        wildcard_prefixes = set()
        exact_routes = set()
        for r in routes:
            if r.endswith("/*"):
                wildcard_prefixes.add(r[:-2])  # e.g. "assets/*" → "assets"
            else:
                exact_routes.add(r)

        def route_exists(route_path: str) -> bool:
            if route_path in exact_routes:
                return True
            # Check wildcard: "financial/ap/invoices" matches "financial/*"
            for prefix in wildcard_prefixes:
                if route_path.startswith(prefix + "/") or route_path == prefix:
                    return True
            return False

        # ── 5. Validate menu URLs against routes ──
        for url in sorted(seed_urls):
            route_path = url.replace("/app/", "", 1) if url.startswith("/app/") else url
            if route_path and not route_exists(route_path):
                errors.append(
                    f"MENU URL has no matching route: {url} (expected route: {route_path})"
                )

        # ── 5. Validate icons exist in icon map ──
        for icon in sorted(seed_icons):
            if icon not in icon_keys:
                errors.append(
                    f"MENU ICON missing from iconMap: {icon} — add to SidebarItem.tsx and SidebarGroup.tsx"
                )

        # ── 6. Check for duplicate slugs in seed ──
        slug_counts = {}
        for slug in seed_slugs:
            slug_counts[slug] = slug_counts.get(slug, 0) + 1
        for slug, count in slug_counts.items():
            if count > 1:
                errors.append(
                    f"DUPLICATE slug in seed_menus.py: '{slug}' appears {count} times"
                )

        # ── 7. Check DB vs seed ──
        db_slugs = set(Menu.objects.values_list("slug", flat=True))
        orphaned = db_slugs - seed_slugs
        if orphaned:
            for slug in sorted(orphaned):
                m = Menu.objects.get(slug=slug)
                errors.append(
                    f"ORPHANED DB entry: '{slug}' ({m.name}) — exists in DB but not in seed_menus.py"
                )

        # ── 8. Report ──
        if errors:
            self.stdout.write(
                self.style.ERROR(f"Found {len(errors)} menu validation errors:")
            )
            for err in errors:
                self.stdout.write(f"  [ERR] {err}")
            raise SystemExit(1)
        else:
            self.stdout.write(
                self.style.SUCCESS("All menus validated successfully [OK]")
            )
