"""Progress tracking utilities for extraction and annotation processes in Semantic Web KMS."""

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from rich.progress import TaskID


@dataclass
class ProcessingStage:
    """Represents a processing stage with status and progress information."""

    name: str
    status: str  # "pending", "processing", "completed", "error"
    progress: int  # 0-100
    message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ProcessingStage to a dictionary for JSON serialization.

        Returns:
            Dict[str, Any]: Dictionary representation of the processing stage.
        """
        data = asdict(self)
        if self.start_time:
            data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        return data


class ProgressTracker:
    """Manages progress tracking for extraction and annotation processes."""

    def __init__(self, job_id: str, output_dir: str = "output"):
        """
        Initialize the ProgressTracker.

        Args:
            job_id (str): Unique identifier for the job.
            output_dir (str, optional): Directory to store progress files. Defaults to "output".
        """
        self.job_id = job_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.progress_file = self.output_dir / f"progress_{job_id}.json"

        # Thread-safe storage
        self._lock = threading.Lock()
        self._stages: Dict[str, ProcessingStage] = {}
        self._overall_progress = 0
        self._status = "pending"
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None

        # Initialize stages
        self._initialize_stages()

    def _initialize_stages(self):
        """Initialize the processing stages for the progress tracker."""
        stages = [
            ("fileExtraction", "File Extraction", "Extracting files from repositories"),
            (
                "contentExtraction",
                "Content Analysis",
                "Analyzing file contents and structure",
            ),
            (
                "codeExtraction",
                "Code Parsing",
                "Parsing code entities and relationships",
            ),
            (
                "documentationExtraction",
                "Documentation",
                "Processing documentation files",
            ),
            ("gitExtraction", "Git Analysis", "Analyzing git history and patterns"),
            (
                "semanticAnnotation",
                "Semantic Processing",
                "Creating knowledge graph and annotations",
            ),
        ]

        for key, name, description in stages:
            self._stages[key] = ProcessingStage(
                name=name, status="pending", progress=0, message=description
            )

    def start_job(self):
        """Start the processing job."""
        with self._lock:
            self._status = "processing"
            self._start_time = datetime.now()

        self._save_progress()

    def end_job(self, success: bool = True, error: Optional[str] = None):
        """
        End the processing job and set the status to 'completed' or 'error'.

        Args:
            success (bool, optional): Whether the job completed successfully. Defaults to True.
            error (Optional[str], optional): Error message if the job failed. Defaults to None.
        """
        with self._lock:
            self._status = "completed" if success else "error"
            self._end_time = datetime.now()
            if error:
                self._stages["semanticAnnotation"].error = error

        self._save_progress()

    def update_stage(
        self, stage_key: str, status: str, progress: int, message: Optional[str] = None
    ):
        """
        Update a specific stage's progress.

        Args:
            stage_key (str): The key of the stage to update.
            status (str): The status of the stage ("pending", "processing", "completed", "error").
            progress (int): Progress percentage (0-100).
            message (Optional[str], optional): Optional message for the stage. Defaults to None.
        """
        with self._lock:
            if stage_key in self._stages:
                stage = self._stages[stage_key]
                stage.status = status
                stage.progress = progress
                if message:
                    stage.message = message

                if status == "processing" and not stage.start_time:
                    stage.start_time = datetime.now()
                elif status in ["completed", "error"] and not stage.end_time:
                    stage.end_time = datetime.now()

                self._update_overall_progress()

        self._save_progress()

    def get_stage(self, stage_key: str) -> Optional[ProcessingStage]:
        """
        Get a specific stage's information.

        Args:
            stage_key (str): The key of the stage to retrieve.
        Returns:
            Optional[ProcessingStage]: The ProcessingStage object if found, else None.
        """
        with self._lock:
            return self._stages.get(stage_key)

    def get_all_stages(self) -> Dict[str, ProcessingStage]:
        """
        Get all stages' information.

        Returns:
            Dict[str, ProcessingStage]: Dictionary of all stage keys to ProcessingStage objects.
        """
        with self._lock:
            return self._stages.copy()

    def get_job_status(self) -> Dict[str, Any]:
        """
        Get overall job status and progress information.

        Returns:
            Dict[str, Any]: Dictionary containing job status, progress, and stage details.
        """
        with self._lock:
            return {
                "job_id": self.job_id,
                "status": self._status,
                "overall_progress": self._overall_progress,
                "start_time": (
                    self._start_time.isoformat() if self._start_time else None
                ),
                "end_time": self._end_time.isoformat() if self._end_time else None,
                "stages": {key: stage.to_dict() for key, stage in self._stages.items()},
            }

    def _update_overall_progress(self):
        """Update overall progress based on individual stages."""
        total_progress = sum(stage.progress for stage in self._stages.values())
        self._overall_progress = total_progress // len(self._stages)

    def _save_progress(self):
        """Save progress to file."""
        try:
            # Get job status without holding the lock
            job_status = self.get_job_status()
            with open(self.progress_file, "w") as f:
                json.dump(job_status, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save progress to {self.progress_file}: {e}")

    def load_progress(self) -> bool:
        """
        Load progress from file.

        Returns:
            bool: True if progress was loaded successfully, False otherwise.
        """
        try:
            if self.progress_file.exists():
                with open(self.progress_file, "r") as f:
                    data = json.load(f)

                with self._lock:
                    self._status = data.get("status", "pending")
                    self._overall_progress = data.get("overall_progress", 0)

                    if data.get("start_time"):
                        self._start_time = datetime.fromisoformat(data["start_time"])
                    if data.get("end_time"):
                        self._end_time = datetime.fromisoformat(data["end_time"])

                    stages_data = data.get("stages", {})
                    for key, stage_data in stages_data.items():
                        if key in self._stages:
                            stage = self._stages[key]
                            stage.status = stage_data.get("status", "pending")
                            stage.progress = stage_data.get("progress", 0)
                            stage.message = stage_data.get("message")
                            stage.error = stage_data.get("error")

                            if stage_data.get("start_time"):
                                stage.start_time = datetime.fromisoformat(
                                    stage_data["start_time"]
                                )
                            if stage_data.get("end_time"):
                                stage.end_time = datetime.fromisoformat(
                                    stage_data["end_time"]
                                )

                return True
        except Exception as e:
            print(f"Warning: Could not load progress from {self.progress_file}: {e}")
        return False


class RichProgressAdapter:
    """Adapter to connect Rich Progress with ProgressTracker."""

    def __init__(self, tracker: ProgressTracker, stage_key: str):
        """
        Initialize the Rich Progress adapter.

        Args:
            tracker (ProgressTracker): The progress tracker to adapt.
            stage_key (str): The stage key to track.
        """
        self.tracker = tracker
        self.stage_key = stage_key
        self.task_id: Optional[TaskID] = None

    def __enter__(self):
        """
        Enter the context manager.

        Returns:
            RichProgressAdapter: The context manager instance.
        """
        return self

    def __exit__(self):
        """Exit the context manager."""
        return None

    def add_task(self, description: str, total: int) -> TaskID:
        """
        Add a task to the progress tracker.

        Args:
            description (str): Description of the task.
            total (int): Total units of work for the task.
        Returns:
            TaskID: Dummy task ID (always 0).
        """
        self.tracker.update_stage(self.stage_key, "processing", 0, description)
        self.task_id = TaskID(0)  # Dummy task ID
        return self.task_id

    def advance(self, task_id: TaskID, advance: int = 1):
        """
        Advance the progress for the given task.

        Args:
            task_id (TaskID): The task ID to advance.
            advance (int, optional): Amount to advance. Defaults to 1.
        """
        if self.task_id == task_id:
            # Calculate progress percentage based on total
            # This is a simplified calculation - in practice you'd track total
            stage = self.tracker.get_stage(self.stage_key)
            if stage:
                current_progress = min(95, stage.progress + 5)
                self.tracker.update_stage(
                    self.stage_key, "processing", current_progress
                )

    def update(
        self,
        task_id: TaskID,
        completed: Optional[int] = None,
        total: Optional[int] = None,
        description: Optional[str] = None,
    ):
        """
        Update task progress.

        Args:
            task_id (TaskID): The task ID to update.
            completed (Optional[int], optional): Number of completed units. Defaults to None.
            total (Optional[int], optional): Total units of work. Defaults to None.
            description (Optional[str], optional): Task description. Defaults to None.
        """
        if self.task_id == task_id:
            if completed is not None and total is not None:
                progress = int((completed / total) * 100)
                self.tracker.update_stage(
                    self.stage_key, "processing", progress, description or ""
                )
            elif description:
                stage = self.tracker.get_stage(self.stage_key)
                if stage:
                    self.tracker.update_stage(
                        self.stage_key, "processing", stage.progress, description
                    )


# Global tracker instance
_current_tracker: Optional[ProgressTracker] = None


def get_current_tracker() -> Optional[ProgressTracker]:
    """
    Get the current progress tracker instance.

    Returns:
        Optional[ProgressTracker]: The current progress tracker if set, else None.
    """
    return _current_tracker


def set_current_tracker(tracker: ProgressTracker):
    """
    Set the current progress tracker instance.

    Args:
        tracker (ProgressTracker): The progress tracker to set as current.
    """
    global _current_tracker
    _current_tracker = tracker


def create_tracker(job_id: str) -> ProgressTracker:
    """
    Create a new progress tracker and set it as the current tracker.

    Args:
        job_id (str): Unique identifier for the job.
    Returns:
        ProgressTracker: The created progress tracker instance.
    """
    tracker = ProgressTracker(job_id)
    set_current_tracker(tracker)
    return tracker


def get_tracker_by_id(job_id: str) -> Optional[ProgressTracker]:
    """
    Get a tracker by job ID, loading progress from file if available.

    Args:
        job_id (str): Unique identifier for the job.
    Returns:
        Optional[ProgressTracker]: The loaded progress tracker if found, else None.
    """
    tracker = ProgressTracker(job_id)
    if tracker.load_progress():
        return tracker
    return None
