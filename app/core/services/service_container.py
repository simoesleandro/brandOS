from dataclasses import dataclass
import os

from app.core.repositories.history_repository import HistoryRepository
from app.core.services.asset_service import AssetService
from app.core.services.briefing_service import BriefingService
from app.core.services.calendar_service import CalendarService
from app.core.services.cmo_service import CmoService
from app.core.services.learning_service import LearningService
from app.core.services.ops_service import OpsService
from app.core.services.operating_loop_service import OperatingLoopService
from app.core.services.publication_service import PublicationService


@dataclass
class BrandOSServices:
    history_repo: HistoryRepository
    asset_service: AssetService
    briefing_service: BriefingService
    calendar_service: CalendarService
    cmo_service: CmoService
    learning_service: LearningService
    ops_service: OpsService
    operating_loop_service: OperatingLoopService
    publication_service: PublicationService


def create_brandos_services(base_dir: str = ".", llm_client=None) -> BrandOSServices:
    history_repo = HistoryRepository(base_dir)

    if llm_client is None:
        from app.core.llm_client import LLMClient
        llm_client = LLMClient()

    asset_service = AssetService(os.path.join(base_dir, "data", "assets"), history_repo)
    briefing_service = BriefingService(base_dir)
    learning_service = LearningService(base_dir, history_repo, llm_client)
    cmo_service = CmoService(base_dir, history_repo, llm_client, learning_service)
    ops_service = OpsService(history_repo, base_dir)
    calendar_service = CalendarService(history_repo, llm_client)
    publication_service = PublicationService(base_dir, history_repo)
    operating_loop_service = OperatingLoopService(base_dir, history_repo, briefing_service, cmo_service)

    return BrandOSServices(
        history_repo=history_repo,
        asset_service=asset_service,
        briefing_service=briefing_service,
        calendar_service=calendar_service,
        cmo_service=cmo_service,
        learning_service=learning_service,
        ops_service=ops_service,
        operating_loop_service=operating_loop_service,
        publication_service=publication_service,
    )
