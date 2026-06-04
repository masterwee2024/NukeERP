"""Column mapping — auto-detect and manual column mapping for CSV imports."""

import re


def auto_detect_columns(
    csv_headers: list[str], column_defs: list[dict]
) -> dict[str, str]:
    """Auto-match CSV headers to template column definitions.
    Returns a mapping: {csv_header: template_field_name}
    """
    mapping = {}
    normalized_headers = {_normalize(h): h for h in csv_headers}
    normalized_defs = {_normalize(d["name"]): d["name"] for d in column_defs}
    aliases = {_normalize(k): v for k, v in _ALIASES.items()}

    for norm_header, original_header in normalized_headers.items():
        best_match = None
        best_score = 0

        # Direct match
        if norm_header in normalized_defs:
            best_match = normalized_defs[norm_header]
            best_score = 100

        # Alias match
        if norm_header in aliases:
            alias_target = _normalize(aliases[norm_header])
            if alias_target in normalized_defs:
                candidate = normalized_defs[alias_target]
                if best_score < 90:
                    best_match = candidate
                    best_score = 90

        # Fuzzy match (substring)
        for norm_def, orig_def in normalized_defs.items():
            if norm_header in norm_def or norm_def in norm_header:
                score = (
                    min(len(norm_header), len(norm_def))
                    / max(len(norm_header), len(norm_def))
                    * 80
                )
                if score > best_score:
                    best_match = orig_def
                    best_score = score

        if best_match:
            mapping[original_header] = best_match

    return mapping


def manual_map(user_mapping: dict[str, str], column_defs: list[dict]) -> dict[str, str]:
    """Apply user-provided column mapping.
    user_mapping: {csv_header: template_field_name}
    Validates against column_defs and returns only valid mappings.
    """
    valid_names = {d["name"] for d in column_defs}
    return {k: v for k, v in user_mapping.items() if v in valid_names}


def apply_mapping(row: dict[str, str], mapping: dict[str, str]) -> dict[str, str]:
    """Transform a raw CSV row using the column mapping.
    Returns a dict keyed by template field names.
    """
    mapped = {}
    for csv_header, field_name in mapping.items():
        mapped[field_name] = row.get(csv_header, "")
    return mapped


def _normalize(s: str) -> str:
    """Normalize a string for comparison: lowercase, strip, remove underscores/spaces."""
    return re.sub(r"[_\s]+", "", s.strip().lower())


_ALIASES = {
    "code": "code",
    "item_code": "code",
    "sku": "code",
    "name": "name",
    "item_name": "name",
    "description": "name",
    "contact": "contact_person",
    "contactperson": "contact_person",
    "person": "contact_person",
    "email": "email",
    "e_mail": "email",
    "phone": "phone",
    "telephone": "phone",
    "tel": "phone",
    "mobile": "phone",
    "category": "category",
    "type": "type",
    "subtype": "subtype",
    "parent": "parent_code",
    "parentcode": "parent_code",
    "uom": "uom",
    "unit": "uom",
    "tax": "tax_code",
    "taxcode": "tax_code",
    "price": "selling_price",
    "sellingprice": "selling_price",
    "cost": "cost",
    "reorder": "reorder_level",
    "reorderlevel": "reorder_level",
    "department": "department",
    "dept": "department",
    "designation": "designation",
    "grade": "grade",
    "ic": "ic_no",
    "icno": "ic_no",
    "nric": "ic_no",
    "joiningdate": "joining_date",
    "joindate": "joining_date",
    "bank": "bank_name",
    "bankname": "bank_name",
    "bankaccount": "bank_account",
    "accountno": "bank_account",
    "account_number": "bank_account",
    "creditlimit": "credit_limit",
    "credit": "credit_limit",
    "paymentterms": "payment_terms",
    "terms": "payment_terms",
    "sst": "sst_no",
    "sstno": "sst_no",
    "employeeno": "employee_no",
    "employeenumber": "employee_no",
    "assetcode": "asset_code",
    "asset": "asset_code",
    "purchasedate": "purchase_date",
    "purchased": "purchase_date",
    "accdep": "accumulated_depreciation",
    "accumulateddepreciation": "accumulated_depreciation",
    "source": "source_currency",
    "sourcecurrency": "source_currency",
    "target": "target_currency",
    "targetcurrency": "target_currency",
    "rate": "rate",
    "exchangerate": "rate",
    "ratedate": "rate_date",
}
