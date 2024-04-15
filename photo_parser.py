import asyncio
import os
import shutil
import time
import pandas
from contextlib import asynccontextmanager
import requests
import re
from PIL import Image
import base64
from functools import wraps
from contextlib import contextmanager
import threading


from typing import List, Tuple, Any, Callable

from playwright.async_api import async_playwright, Browser, Page

from core import CSV_READ_PATH, PHOTO_POST_PATH

PHOTO_COUNT = 5

TASKS_COUNT = 1
ROWS_PER_TASK = 5

ID = 'ID'
P_CODE = 'Арт_Пост_Ориг'
P_NAME = 'Название'

__IT_WORKS = False
__AFTER_ROW_CALLBACKS: List[Callable] = []

class _ReverseSemaphore:
    
    def __init__(self):
        self._lock = threading.Lock()
        self._cond = threading.Condition(threading.Lock())
        self._value = 0
    
    def _zero_cond(self):
        return self._value == 0
    
    def acquire(self):
        if self._lock.locked():
            self._lock.acquire()
            self._lock.release()
        
        self._value += 1
    
    __enter__ = acquire
    
    def release(self):
        if self._value == 0:
            raise RuntimeError("un-acquired")
        
        with self._cond:
            self._value -= 1
            self._cond.notify()
    
    def __exit__(self, t, v, tb):
        self.release()
    
    @contextmanager
    def wait_free(self):
        with self._lock:
            with self._cond:
                self._cond.wait_for(self._zero_cond)
                yield

__SEM = _ReverseSemaphore()

def process_b64url(url: str) -> Tuple[str, bytes]:
    metadata, data = url.split(';')
    _, b64data = data.split(',')
    bytes_ = base64.b64decode(b64data)
    
    _, format_ = metadata.split(':')
    _, extension = format_.split('/')
    
    return (extension, bytes_)

def correct_filename(filename: str):
    filename = re.sub(r'[^\w\s]', '', filename)
    filename = filename.replace(' ', '_')
    
    return filename


@asynccontextmanager
async def get_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        try:
            yield browser
        finally:
            await browser.close()
            

async def search_images_google(search_query: str, page: Page) -> List[Any]:
    selector = page.locator('input').first

    await selector.clear()
    await selector.fill(search_query)
    await selector.press('Enter')
    await page.wait_for_load_state('load')
    
    image_urls = await page.evaluate(
        '''() => {
            const images = document.querySelectorAll('img');
            return Array.from(images).map(img => img.src);
        }'''
    )
    
    return image_urls

async def search_images_yandex(search_query: str, page: Page) -> List[Any]:
    await page.goto(f'https://yandex.ru/images/search?text={search_query}')
    await page.wait_for_load_state('load')
    
    image_urls = await page.evaluate(
        '''() => {
            const images = document.querySelectorAll('img');
            return Array.from(images).map(img => img.src);
        }'''
    )
    
    return image_urls


async def download_from_yandex(search_query: str, count: int, page: Page):
    images_data = await search_images_yandex(search_query, page)
    images_data = [d for d in images_data if 'avatars.mds.yandex.net' in d]
    
    res = []
    
    for _, photo_url in zip(range(count), images_data):
        r = requests.get(photo_url)
        ext = r.headers['Content-Type'].split('/')[1]
        bytes_ = r.content
        
        res.append((ext, bytes_))
    
    return res

async def download_b64images(search_query: str, count: int, page: Page) -> List[Tuple[str, str]]:
    images_data = await search_images_google(search_query, page)
    images_data = [d for d in images_data if 'base64,' in d]
    
    res = [process_b64url(photo_url) for _, photo_url in zip(range(count), images_data) if 'base64,' in photo_url]
    
    return res
        

async def process_row(row: pandas.Series, page: Page):
    p_code = str(row[P_CODE])
    p_name: str = row[P_NAME]
    
    image_c = PHOTO_COUNT
    
    images_from_code = await download_from_yandex(p_code, image_c, page)
    images_from_name = await download_from_yandex(p_name, image_c, page)
    
    images = images_from_code + images_from_name

    return images

def product_count(csv_read_path: str = CSV_READ_PATH):
    products = pandas.read_excel(csv_read_path)
    
    return len(products)

def _save_images_callback(row, images):
    path = PHOTO_POST_PATH
    
    p_id = str(row[ID])
    p_name: str = row[P_NAME]
    p_code = str(row[P_CODE])
    
    photo_path = f"{path}/{p_id}"
    
    if os.path.exists(photo_path):
        shutil.rmtree(photo_path)
    
    try:   
        os.makedirs(photo_path)
    except:
        pass
    
    for i, photo in enumerate(images):
        _, b_img = photo
        image_name = correct_filename(p_name)
        filename = f"{p_code}_{image_name}_{i+1}.png"
        
        with open(f"{photo_path}/{filename}", "wb") as f:
            f.write(b_img)

__AFTER_ROW_CALLBACKS.append(_save_images_callback)

async def async_start_downloading(
    tasks_count: int = TASKS_COUNT, 
    csv_read_path: str = CSV_READ_PATH
):
    products = pandas.read_excel(csv_read_path)
    products_iterator = products.iterrows()
    
    async with get_browser() as browser:
    
        async def _rows_processor():
            nonlocal browser, products_iterator
            
            page = await browser.new_page()
            await page.goto('https://yandex.ru/images/search?text=1')#https://www.google.com/search?q=1&sca_esv=ae27c76c7331fca2&tbm=isch&sxsrf=ACQVn0-hVVuzpNNGKZllVvs1qB1M-LTDWQ%3A1710782336984&source=hp&biw=3440&bih=1351&ei=gHf4ZfbZOfmgwPAPmM6RgAc&iflsig=ANes7DEAAAAAZfiFkLtCUFsFkW2aYf9-2pwOeu4gkZNH&udm=&ved=0ahUKEwj2me3rqP6EAxV5EBAIHRhnBHAQ4dUDCA8&oq=1&gs_lp=EgNpbWciATEyBBAjGCcyBRAAGIAEMggQABiABBixAzIFEAAYgAQyBRAAGIAEMgUQABiABDIFEAAYgAQyBRAAGIAEMgUQABiABDIFEAAYgARIyARQSVhJcAF4AJABAJgBUqABUqoBATG4AQzIAQD4AQGKAgtnd3Mtd2l6LWltZ5gCAqACV6gCCsICBxAjGOoCGCeYAwSSBwEyoAeEBg&sclient=img

            row_done = True
                
            while __IT_WORKS:
                if row_done:
                    try:
                        _, row = next(products_iterator)
                        row_done = False
                    except StopIteration:
                        break
                try:
                    images = await process_row(row, page)
                    
                    with __SEM:
                        for callback in __AFTER_ROW_CALLBACKS: 
                            _callback_wrapper(callback)(row, images)
                    
                    row_done = True
                except Exception as e:
                    await page.reload()
        
        tasks = []
        
        for _ in range(tasks_count):
            tasks.append(asyncio.create_task(_rows_processor()))
    
        await asyncio.gather(*tasks)

def _callback_wrapper(callback: Callable):
    @wraps(callback)
    def _wrap(*args, **kwargs):
        filtered_kwargs = {}
        args_c = 0
        args_l = len(args)
        
        for var in callback.__code__.co_varnames:
            if (val := kwargs.get(var)):
                filtered_kwargs[var] = val
            elif args_l > args_c:
                args_c += 1
        
        return callback(*args[:args_c], **filtered_kwargs)

    return _wrap

@wraps(async_start_downloading)
def start_downloading(*args, **kwargs):
    global __IT_WORKS
    
    __IT_WORKS = True
    
    asyncio.run(async_start_downloading(*args, **kwargs))
    
    __IT_WORKS = False

def turn_off_parsing():
    global __IT_WORKS
    
    __IT_WORKS = False

def is_works():
    return __IT_WORKS

def add_after_row_callback(callback: Callable, in_end: bool = True):
    with __SEM.wait_free():
        if in_end:
            __AFTER_ROW_CALLBACKS.append(callback)
        else:
            __AFTER_ROW_CALLBACKS.insert(0, callback)
    

#asyncio.run(start_downloading())
#products_iterator = pandas.read_excel(CSV_READ_PATH)
#for i in products_iterator.loc:
#    print(f"{i[ID]} {i[P_CODE]} {i[P_NAME]}")
