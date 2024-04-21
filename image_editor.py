import os
import cv2
from cv2.typing import MatLike
import concurrent.futures
from PIL import Image, ImageFilter
import time
import numpy

from core import PHOTO_POST_PATH, get_photo_files

BASE_FORMAT_SQUARE_SIZE = 500

def resize_image(input_path: str, target_square_size=BASE_FORMAT_SQUARE_SIZE):
    try:
        full_path = os.path.join(PHOTO_POST_PATH, input_path)
        
        pil_img = Image.open(full_path)
        main_color = (255,255,255)#get_main_color(pil_img)
        spaced_img = spacing_resize(pil_img, fill_color=main_color)
        
        img = numpy.array(spaced_img)[:, :, ::-1].copy()
        rescaled_img = proportial_rescale(img, target_square_size)
        
        name, ext = full_path.split('.')
        path, name = name.split('/')
        path = f"{path}/{name}.{ext}"
        cv2.imwrite(path, rescaled_img)
    except Exception as ex:
        print(ex)

def get_main_color(img: Image.Image):
    colors = img.getcolors(img.size[0]*img.size[1])
    main_color = max(colors)
    
    return main_color[1]

def proportial_rescale(img: MatLike, target_square_size=BASE_FORMAT_SQUARE_SIZE):
    target_scale_coef = target_square_size / max(img.shape)
    alg = cv2.INTER_CUBIC if target_scale_coef > 0 else cv2.INTER_AREA
    
    img_resized = cv2.resize(img, None, fx=target_scale_coef, fy=target_scale_coef, interpolation=alg)
    
    return img_resized

def spacing_resize(img: Image.Image, fill_color=(255,255,255), blur_radius=5):
    x, y = img.size
    
    max_side = max((x, y))
    paste_cords = (
        int((max_side - x) / 2), 
        int((max_side - y) / 2)
    )
    
    new_img = Image.new('RGB', (max_side, max_side), fill_color)
    new_img.paste(img, paste_cords)
    
    return new_img

def show_image_resolution(image_path):
    try:
        img = Image.open(image_path)
        
        width, height = img.size
        
        print(f"Ширина: {width} пикселей")
        print(f"Высота: {height} пикселей")
    except Exception as e:
        print("Произошла ошибка:", str(e))

def formatting_images():
    with concurrent.futures.ThreadPoolExecutor() as exec:
        exec.map(resize_image, get_photo_files())
        
        exec.shutdown()
