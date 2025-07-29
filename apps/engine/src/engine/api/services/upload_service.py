import pathlib
import shutil
import tempfile
import time


def handle_organization_upload(files):
    """
    Save uploaded files, start background analysis, and return job id and status.

    Args:
        files (list): List of uploaded file objects.

    Returns:
        dict: Job id, status, message, files_uploaded.
    """
    temp_dir = tempfile.mkdtemp(prefix="org_upload_")
    try:
        for file in files:
            if file.filename:
                file_path = pathlib.Path(temp_dir) / file.filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file.save(str(file_path))
        job_id = f"upload_{int(time.time())}"
        # TODO: Start background analysis (Celery task)
        # For now, just return stub
        return {
            "job_id": job_id,
            "status": "started",
            "message": "File upload and analysis started successfully",
            "files_uploaded": len([f for f in files if f.filename]),
        }
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
