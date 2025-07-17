from celery import shared_task
from engine.api.services.analysis_service import perform_full_analysis

@shared_task(bind=True)
def run_organization_analysis(self, organization_name: str):
    """
    Celery task for running the analysis.
    Args:
        organization_name (str): Name of the organization.
    Returns:
        dict: Status and result.
    """
    try:
        result = perform_full_analysis(organization_name, task_updater=self.update_state)
        return {'status': 'Completed', 'result': result}
    except Exception as e:
        raise 