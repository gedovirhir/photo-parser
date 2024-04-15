import os
import shutil
from PIL.Image import Image, open

from typing import List, Iterable

CSV_READ_PATH = 'products_list.xlsx'
PHOTO_POST_PATH = 'photos'

def get_photo_files(folder_path: str = PHOTO_POST_PATH) -> List[str]:
    return [f for f in os.listdir(folder_path) if f.endswith(('png', 'jpg', 'jpeg', 'gif'))]

def iter_photos() -> Iterable[Image]:
    for path in get_photo_files():
        ...

def clear_photo_folder(directory: str = PHOTO_POST_PATH):
    if not os.path.exists(directory):
        return

    for root, dirs, files in os.walk(directory, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            os.remove(file_path)
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            shutil.rmtree(dir_path)
