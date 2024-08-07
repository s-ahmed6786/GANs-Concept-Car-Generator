import base64
import mimetypes
from pathlib import Path
import random
import time
import threading
import shutil
from typing import Any
import requests
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotInteractableException,
)
from threading import Lock


def scroll_and_click_load_more(browser, LAST_HEIGHT: int):
    """Scrolls the page and clicks the 'Show more results' button if present"""
    scroll_count = 0

    while True:
        SCROLL_PAUSE_TIME = random.randint(2, 4)
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        scroll_count += 1

        try:
            load_more_buttons = browser.find_elements(By.CLASS_NAME, "LZ4I")
            if load_more_buttons:
                load_more_buttons[0].click()
                time.sleep(SCROLL_PAUSE_TIME)
                scroll_count = 0
        except (NoSuchElementException, ElementNotInteractableException):
            pass

        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == LAST_HEIGHT:
            break
        else:
            LAST_HEIGHT = new_height


def download_images(images_to_download: list[Any], IMGS_DIR: Path, counter_lock: Lock):
    global image_counter
    for image in images_to_download:
        src = image.get_attribute("src")
        if not src:
            continue

        if src.startswith("data:image"):
            base64_encoded_data = src.split(",")[1]
            image_data = base64.b64decode(base64_encoded_data)
            file_extension = src.split(";")[0].split("/")[1]
        else:
            src = src or image.get_attribute("data-src")
            if not src:
                continue
            try:
                response = requests.head(src, allow_redirects=True)
                content_type = response.headers.get("content-type")
                file_extension = mimetypes.guess_extension(content_type).strip(".")
                image_data = requests.get(src).content
            except Exception as e:
                print(f"Error - could not download image: {e}")
                continue

        with counter_lock:
            image_counter += 1
            current_counter = image_counter

        img_path = IMGS_DIR / f"img_{current_counter}.{file_extension}"
        with open(img_path, "wb") as handler:
            handler.write(image_data)


counter_lock = Lock()
image_counter = 0

NUM_THREADS = 32

# The 2nd element in the tuple is the car name with all valid characters for a file name
QUERIES = [
    "2023 Aston Martin Vantage",
    "2025 Aston Martin Vanquish",
    "Aston Martin Valhala",
    "Aston Martin Valkyrie",
    "Aston Martin Vulcan",
    "Aventador SVJ",
    "BMW i8",
    "Bugatti Bolide",
    "Bugatti Chiron",
    "Bugatti Chiron SS",
    "Bugatti Veyron",
    "Ferrari 296 GTB",
    "Ferrari 458 SPECIALE",
    "Ferrari 812 Superfast",
    "Ferrari Daytona",
    "Ferrari F8",
    "Ferrari LaFerrari",
    "Ferrari Monza SP2",
    "Ferrari Portofino",
    "Ferrari Roma",
    "Ferrari SF90",
    "Hennessey Venom F5",
    "Koenigsegg Agera",
    "Koenigsegg Jesko",
    ("Koenigsegg One:1", "Koenigsegg One_1"),
    "Koenigsegg Regera",
    "Lamborghini Gallardo",
    "Lamborghini Huracan",
    ("Lamborghini Murciélago", "Lamborghini Murcielago"),
    "Lamborghini Revuelto",
    "Lamborghini Sesto Elemento",
    "Lotus Evija",
    "McLaren F1",
    "McLaren P1",
    "McLaren Senna",
    "Mclaren Solus GT",
    "McLaren Speedtail",
    "Mercedes-AMG Project One",
    "Pagani Huayra",
    "Pininfarina Battista",
    "Porsche 911",
    "Porsche 918 Spyder",
    "Porsche GT3RS",
    "Porsche GT4RS",
    "Porsche Taycan",
    "Rimac Concept One",
    "Rimac Nevera",
    "SSC Tuatara",
    "W Motors Lykan HyperSport",
    "Zenvo ST1",
]

DATA_DIR = Path() / "data"
DATA_DIR.mkdir(exist_ok=True)

for query_data in QUERIES:
    if isinstance(query_data, tuple):
        query, file_name = query_data
    else:
        query, file_name = query_data, query_data

    IMGS_DIR = DATA_DIR / file_name
    shutil.rmtree(IMGS_DIR, True)
    IMGS_DIR.mkdir(exist_ok=True)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    browser = webdriver.Chrome(options=chrome_options)

    browser.get("https://images.google.com")
    search_box = browser.find_element(By.ID, "APjFqb")
    search_box.send_keys(query + Keys.RETURN)
    time.sleep(2)

    LAST_HEIGHT = browser.execute_script("return document.body.scrollHeight")
    scroll_and_click_load_more(browser, LAST_HEIGHT)

    images = browser.find_elements(By.CSS_SELECTOR, "img.rg_i")
    images_per_thread = len(images) // NUM_THREADS
    threads = []

    for i in range(NUM_THREADS):
        start_index = i * images_per_thread
        end_index = (
            start_index + images_per_thread if i != NUM_THREADS - 1 else len(images)
        )
        thread_images = images[start_index:end_index]
        thread = threading.Thread(
            target=download_images, args=(thread_images, IMGS_DIR, counter_lock)
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    browser.quit()
