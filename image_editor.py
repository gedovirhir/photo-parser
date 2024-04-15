import os
import cv2
import concurrent.futures
from PIL import Image
import time

from core import PHOTO_POST_PATH, get_photo_files

BASE_FORMAT_SIZE = (500, 500)

def resize_image(input_path: str, target_size=BASE_FORMAT_SIZE):
    full_path = os.path.join(PHOTO_POST_PATH, input_path)
    img = cv2.imread(full_path)

    img_resized = cv2.resize(img, target_size, interpolation=cv2.INTER_LINEAR)
    
    cv2.imwrite(f"{full_path}", img_resized)

def show_image_resolution(image_path):
    try:
        # Открываем изображение
        img = Image.open(image_path)
        
        # Получаем разрешение изображения
        width, height = img.size
        
        print(f"Ширина: {width} пикселей")
        print(f"Высота: {height} пикселей")
    except Exception as e:
        print("Произошла ошибка:", str(e))

def formatting_images():
    with concurrent.futures.ThreadPoolExecutor() as exec:
        exec.map(resize_image, get_photo_files())
