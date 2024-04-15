import os
from PIL import Image, ImageTk
from contextlib import contextmanager
import tkinter as tk
from tkinter import filedialog, messagebox
import shutil
import pyperclip
pyperclip.ENCODING = 'utf-16'
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, Future, FIRST_COMPLETED

from core import PHOTO_POST_PATH, get_photo_files
from photo_parser import product_count, start_downloading, add_after_row_callback, turn_off_parsing, is_works, ID

_MUTEX = threading.Lock()
_T_EXECUTOR = ThreadPoolExecutor()

def start_parsing():
    global progress_count, progress_t, total
    
    total = product_count()
    progress_t = progress_t.format(total=total)
    progress_label.config(text=progress_t.format(count=0))
    __switch_start_stop_button()
    
    add_after_row_callback(lambda: inc_progress(1))
    
    t = threading.Thread(target=start_downloading)
    t.start()
    
    mainplate.update()
    

def shutdown_showing():
    photo_dirs_q.put(None)

def __switch_start_stop_button():
    if progress_start_button.started:
        progress_start_button.config(text="Начать обработку файла", command=start_parsing)
    else:
        progress_start_button.config(text="Закончить обработку файла", command=turn_off_parsing) 

    progress_start_button.started = not progress_start_button.started
    
def _add_dir(photo_dir: str):
    global photo_dirs
    
    folder_path = os.path.join(PHOTO_POST_PATH, photo_dir)
    
    photo_dirs.append(folder_path)
    photo_dirs_q.put(folder_path)

def open_folder():
    global photo_dirs, photo_dirs_q
    
    with _MUTEX:
        def __callback(row):
            with _MUTEX:
                _add_dir(str(row[ID]))
        
        def __check_end_progress():
            if progress_count >= total:
                shutdown_showing()
        
        add_after_row_callback(__callback, in_end=False)
        add_after_row_callback(__check_end_progress)
    
        photo_dirs = []
        photo_dirs_q = queue.Queue()
        
        for _, dirs, _ in os.walk(PHOTO_POST_PATH):
            for dir_name in dirs:
                _add_dir(dir_name)

def show_images_plate():
    global root
    
    root = tk.Toplevel(mainplate)

    open_folder()

    root.title("Loading")
    root.geometry("2000x700")
    root.grid_columnconfigure((0,1,2), weight=1, uniform="column")
    
    root.update()
    
    start_showing()

def copy_bind(name: str):
    def __func(event):
        pyperclip.copy(name)
    
    return __func

#@contextmanager
def close_offer(cv: tk.Frame):
    cv.pack()
    
    tk.Label(cv, text='Долгое ожидание новых картинок. Возможно парсинг завис.').pack(pady=10)
    
    root.update()

def get_folder_path():
    
    if not is_works():
        folder_path = photo_dirs_q.get()
    else:
        try:
            folder_path = photo_dirs_q.get(block=False)
        except queue.Empty:
            folder_path = None
        
    return folder_path

def start_showing():
    global image_files, folder_path, root
    
    root.update()
    
    folder_path = get_folder_path()
    
    if folder_path is None:
        root.destroy()
        before_end()
        return
    
    image_files = get_photo_files(folder_path)
    
    if len(image_files) > 0:
        image_base_name: str = image_files[0]
        image_base_name = image_base_name.rsplit('_', 1)[0]
        
        prod_code, prod_name = image_base_name.split('_', 1)
        
        root.title(image_base_name)
        
        root.bind("<Button-3>", copy_bind(prod_name.replace('_', ' ')))
        root.bind("<Button-1>", copy_bind(prod_code))
        
        buttons = []
        img_width = 300
        img_height = 300
        
        for i, image_file in enumerate(image_files):
            image_path = os.path.join(folder_path, image_file)
            image = Image.open(image_path)
            image.thumbnail((img_width, img_height))
                
            photo = ImageTk.PhotoImage(image)
            row = i // 5
            column = i % 5
            
            btn = tk.Button(
                root, 
                image=photo, 
                command=lambda img=image_file: delete_other_images(img),
                width=img_width, 
                height=img_height
            )
            btn.image = photo
            
            buttons.append(btn)
            btn.grid(row=row, column=column, padx=5, pady=5)
    else:
        start_showing()    
        

def delete_other_images(selected_image):
    for image_file in image_files:
        if image_file != selected_image:
            image_path = os.path.join(folder_path, image_file)
            os.remove(image_path)
    
    for widget in root.winfo_children():
        widget.destroy()
    
    root.title("Loading")
    photo_dirs_q.task_done()
    
    start_showing()

def before_end():
    for folder in photo_dirs:
        files = os.listdir(folder)
        
        if files:
            first_file = files[0]
            
            file_path = os.path.join(folder, first_file)
            
            _, ext = os.path.splitext(file_path)
            foldername, _ = os.path.splitext(folder)
            
            new_file_path = foldername + ext
            os.rename(file_path, new_file_path)
            
        shutil.rmtree(folder)
        #resize_image(new_file_path)

def inc_progress(size=1):
    global progress_count
    
    progress_count += size
    progress_label.config(text=progress_t.format(count=progress_count))
    progress_label.update()


mainplate = tk.Tk()
mainplate.title('Start Exel processing')

progress_start_button = tk.Button(mainplate, text="Начать обработку файла", command=start_parsing)
progress_start_button.started = False
progress_start_button.pack(pady=10)

progress_t_default = f"Progress: ..."
progress_t = "Progress: {{count}}/{total}"
progress_count = 0
progress_label = tk.Label(mainplate, text=progress_t_default)
progress_label.pack(pady=5)

choosing_start_button = tk.Button(mainplate, text="Начать выбирать фото", command=show_images_plate)
choosing_start_button.pack(pady=10)

def run():
    mainplate.mainloop()
