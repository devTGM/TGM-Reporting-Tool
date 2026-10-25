from typing import List, Dict, Any
from backend.app.models.schema import UnifiedAdRecord

def audit_and_validate_records(records: List[UnifiedAdRecord]) -> Dict[str, Any]:
    """
    Audits the cleaned marketing records and produces a data health report.
    Returns:
    - quality_score: 0 to 100 percentage
    - total_records
    - valid_records
    - flagged_warnings: list of issues found and auto-remediated
    """
    if not records:
        return {
            "quality_score": 100.0,
            "total_records": 0,
            "valid_records": 0,
            "flagged_warnings": [],
            "summary": "No records in batch."
        }

    warnings = []
    issues_count = 0

    for idx, r in enumerate(records):
        # Mandatory check
        if not r.client_id or not r.client_name:
            warnings.append(f"Row {idx+1}: Missing client identifier.")
            issues_count += 1
            
        if not r.date:
            warnings.append(f"Row {idx+1}: Missing date field.")
            issues_count += 1

        if r.spend > 0 and r.impressions == 0:
            warnings.append(f"Row {idx+1} ({r.platform} - {r.campaign_name}): Spend > $0 with 0 impressions.")
            issues_count += 1

        if r.ctr > 50.0:
            warnings.append(f"Row {idx+1} ({r.platform}): Unusually high CTR ({r.ctr}%).")

        if r.purchase_roas > 25.0:
            warnings.append(f"Row {idx+1} ({r.platform}): Very high ROAS ({r.purchase_roas}x) detected - check conversion value tracking.")

    total = len(records)
    penalty = min(50.0, (issues_count / max(1, total)) * 100.0)
    quality_score = round(100.0 - penalty, 1)

    return {
        "quality_score": quality_score,
        "total_records": total,
        "valid_records": total - issues_count,
        "issues_detected": issues_count,
        "flagged_warnings": warnings[:15],  # Cap preview to 15
        "summary": f"Audit complete: {quality_score}% quality score across {total} records."
    }
