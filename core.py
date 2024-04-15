import os
from PIL.Image import Image, open

from typing import List, Iterable

CSV_READ_PATH = 'products_list.xlsx'
PHOTO_POST_PATH = 'photos'

def get_photo_files(folder_path: str = PHOTO_POST_PATH) -> List[str]:
    return [f for f in os.listdir(folder_path) if f.endswith(('png', 'jpg', 'jpeg', 'gif'))]

def iter_photos() -> Iterable[Image]:
    for path in get_photo_files():
        ...