"""Policy service — condition evaluation and workflow auto-routing engine."""

import logging
from uuid import UUID

from apps.core.models import ApprovalPolicy, WorkflowDefinition

logger = logging.getLogger(__name__)

SUPPORTED_OPERATORS = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def evaluate_condition(condition: dict, document_data: dict) -> bool:
    """Evaluate a single condition against document data.

    Condition format:
        {"field": "total_amount", "operator": ">=", "value": 50000}
        {"field": "department", "operator": "==", "value": "procurement"}
        {"field": "amount", "operator": "between", "value": 10000, "value_to": 50000}
        {"field": "status", "operator": "in", "value": ["pending", "draft"]}
    """
    field = condition.get("field")
    operator = condition.get("operator")
    value = condition.get("value")

    if not field or not operator:
        return True

    doc_value = document_data.get(field)
    if doc_value is None:
        return False

    if operator == "between":
        value_to = condition.get("value_to")
        if value_to is None:
            return False
        try:
            return float(value) <= float(doc_value) <= float(value_to)
        except (TypeError, ValueError):
            return False

    if operator == "in":
        if not isinstance(value, list):
            return False
        return doc_value in value

    if operator == "not_in":
        if not isinstance(value, list):
            return False
        return doc_value not in value

    compare = SUPPORTED_OPERATORS.get(operator)
    if not compare:
        logger.warning("Unknown operator: %s", operator)
        return False

    try:
        if isinstance(doc_value, (int, float)) and not isinstance(value, (int, float)):
            return compare(float(doc_value), float(value))
        return compare(doc_value, value)
    except (TypeError, ValueError) as exc:
        logger.warning("Condition eval error: %s", exc)
        return False


def evaluate_policy(policy: ApprovalPolicy, document_data: dict) -> bool:
    """Evaluate all conditions of a policy (AND logic). Returns True if all match."""
    if not policy.conditions:
        return True
    return all(evaluate_condition(c, document_data) for c in policy.conditions)


def get_applicable_policy(
    module: str,
    document_type: str,
    document_data: dict,
    company_id: UUID | None = None,
) -> ApprovalPolicy | None:
    """Find the highest-priority (lowest number) matching policy.

    Evaluation order:
    1. Company-specific policies for (module, document_type)
    2. Global policies (company=null) for (module, document_type)
    3. Highest priority (lowest priority number) wins
    """
    policies = ApprovalPolicy.objects.filter(
        module=module,
        document_type=document_type,
        is_active=True,
    ).order_by("priority", "name")

    if not policies.exists():
        return None

    # Try company-specific first
    if company_id:
        for policy in policies:
            if policy.company_id == company_id and evaluate_policy(
                policy, document_data
            ):
                return policy

    # Fall back to global
    for policy in policies:
        if policy.company_id is None and evaluate_policy(policy, document_data):
            return policy

    return None


def get_default_workflow(
    module: str,
    document_type: str,
    company_id: UUID | None = None,
) -> WorkflowDefinition | None:
    """Return the default workflow if no policy matches."""
    qs = WorkflowDefinition.objects.filter(
        module=module,
        document_type=document_type,
        is_active=True,
    ).order_by("-is_global_template", "name")

    if company_id:
        company_workflow = qs.filter(company_id=company_id).first()
        if company_workflow:
            return company_workflow

    return qs.filter(is_global_template=True).first()


def resolve_workflow(
    module: str,
    document_type: str,
    document_data: dict,
    company_id: UUID | None = None,
) -> WorkflowDefinition | None:
    """Full resolution: policy match → applicable workflow → default workflow."""
    policy = get_applicable_policy(module, document_type, document_data, company_id)
    if policy:
        return policy.workflow

    return get_default_workflow(module, document_type, company_id)
