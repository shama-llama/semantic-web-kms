import os
import pathlib
from engine.core.paths import PathManager

def get_input_directory():
    """
    Get the input directory for uploads.
    Returns:
        dict: Input directory info (path, exists, is_directory).
    """
    input_dir = os.environ.get('DEFAULT_INPUT_DIR', '~/downloads/repos/Thinkster/')
    pm = PathManager(pathlib.Path(input_dir).expanduser().resolve())
    input_dir_path = str(pm.input_dir)
    exists = pathlib.Path(input_dir_path).exists()
    is_directory = pathlib.Path(input_dir_path).is_dir() if exists else False
    return {
        'input_directory': input_dir_path,
        'exists': exists,
        'is_directory': is_directory,
    } 