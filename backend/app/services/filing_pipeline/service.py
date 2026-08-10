"""FilingPipeline's entity-specific behavior. Restores what the legacy
Base44 `updateFilingStage` function used to do (docs/legacy-base44-functions/
updateFilingStage/entry.ts) but got dropped when the stage-advance UI was
rebuilt as StageUpdateModal.jsx, which only ever wrote current_stage/
stage_history: stamping final_confirmation_date when a pipeline reaches
"Completed", and pushing the linked ServiceFiling's status forward to match.

The ServiceFiling status push goes through service_filing.service.after_update
directly (not a raw attribute set) so that update carries its normal side
effects too — filed_date stamping, firm notification, activity log, and
auto-invoice-generation on reaching Completed — rather than silently
bypassing them the way _sync_tasks_for_filing's direct Task mutation does."""

import datetime
import logging

from ...models import MODELS
from .._shared.hooks import EntityHooks
from ..service_filing.service import after_update as service_filing_after_update

logger = logging.getLogger(__name__)

# Mirrors the legacy filingStatusMap in docs/legacy-base44-functions/
# updateFilingStage/entry.ts — stage names match exactly what's still used
# today (src/features/compliance/pages/FilingPipeline.jsx's `stages` list).
STAGE_TO_FILING_STATUS = {
    "Client Data Collection": "Documents Pending",
    "Internal Review": "In Progress",
    "Manager Approval": "Review",
    "CRA Submission": "Review",
    "Final Filing Confirmation": "Filed",
    "Completed": "Completed",
}


def snapshot_before_update(obj):
    return {"old_stage": getattr(obj, "current_stage", None)}


async def after_update(db, user, obj, snapshot, body, ctx):
    old_stage = snapshot["old_stage"]
    if old_stage == obj.current_stage:
        return obj

    if obj.current_stage == "Completed":
        obj.final_confirmation_date = datetime.date.today().isoformat()
        try:
            await db.commit()
            await db.refresh(obj)
        except Exception:
            logger.exception("Failed to persist final_confirmation_date for pipeline %s", obj.id)

    new_filing_status = STAGE_TO_FILING_STATUS.get(obj.current_stage)
    if new_filing_status and obj.service_filing_id:
        filing = await db.get(MODELS["ServiceFiling"], obj.service_filing_id)
        if filing and filing.status != new_filing_status:
            filing_snapshot = {"old_status": filing.status}
            filing.status = new_filing_status
            try:
                await db.commit()
                await db.refresh(filing)
                await service_filing_after_update(db, user, filing, filing_snapshot, {}, {})
            except Exception:
                logger.exception(
                    "Failed to sync ServiceFiling %s status from pipeline %s advancing to %s",
                    filing.id, obj.id, obj.current_stage,
                )

    return obj


hooks = EntityHooks(
    snapshot_before_update=snapshot_before_update,
    after_update=after_update,
)
