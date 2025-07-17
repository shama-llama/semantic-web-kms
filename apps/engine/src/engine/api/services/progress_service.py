from engine.core.progress_tracker import get_tracker_by_id

def get_progress(job_id: str):
    """
    Get the progress for a given job ID.
    Returns:
        dict or None: Job status and stage information, or None if not found.
    """
    tracker = get_tracker_by_id(job_id)
    if tracker:
        return tracker.get_job_status()
    return None

def get_progress_stages(job_id: str):
    """
    Get all progress stages for a job.
    Returns:
        dict or None: Stage details, or None if not found.
    """
    tracker = get_tracker_by_id(job_id)
    if tracker:
        stages = tracker.get_all_stages()
        return {key: stage.to_dict() for key, stage in stages.items()}
    return None

def get_progress_stage(job_id: str, stage_key: str):
    """
    Get a specific progress stage for a job.
    Returns:
        dict or None: Stage information, or None if not found.
    """
    tracker = get_tracker_by_id(job_id)
    if tracker:
        stage = tracker.get_stage(stage_key)
        if stage:
            return stage.to_dict()
    return None 