from typing import List
from pydantic import BaseModel
from retrieval.utils import file_utils

class Page(BaseModel):
    content: str = ''
    metadata: dict = {}  # DEPRECATED: 所有 loader 均未填充此字段，下游也未使用，将在后续版本移除
    page_number: int = 0

class Document(BaseModel):
    content: str = ''
    page_list: List[Page] = []
    use_splitter: bool = True 
    is_md: bool = False


class FileInfo:
    def __init__(self, path: str, name: str):
        self.file_path = path
        self.file_name = name
        self.extension = file_utils.get_file_extension(name)

class LoaderException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"{self.message}"
