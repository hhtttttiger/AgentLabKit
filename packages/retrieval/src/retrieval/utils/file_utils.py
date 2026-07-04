import os

def get_file_extension(file_name: str) -> str:
    """
    Get file extension from file name.
    Returns extension including dot (e.g., '.txt').
    """
    _, ext = os.path.splitext(file_name)
    return ext
