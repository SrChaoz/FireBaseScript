# Comando de compilación 
# pyinstaller --onefile --noconsole --add-data "drivers/chromedriver.exe;drivers" --add-data "drivers/unrar.exe;drivers" --icon "firebasescript.ico" "FireBaseStorageScript.py"

import os
import requests
import ffmpeg  # Para convertir videos
import firebase_admin  # para controlar lo de firebase 
from firebase_admin import credentials, storage
from selenium import webdriver  # selenium para hacer automatizaciones en chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import zipfile
import rarfile  #rarfile que se usa junto a undriver
from tqdm import tqdm
import shutil  # Para eliminar carpetas que no esten vacias
import tkinter as tk
from tkinter import filedialog, scrolledtext
from tkinter import ttk  
import sys
import threading  

# Variable global para controlar la inicialización de Firebase
firebase_initialized = False

def get_resource_path(relative_path):
    """Obtiene la ruta completa del archivo empaquetado."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class ConsoleRedirect:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)  

    def flush(self):
        pass  

def initialize_firebase(config_path, bucket_name):
    global firebase_initialized
    if not firebase_initialized:
        cred = credentials.Certificate(config_path)
        firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
        firebase_initialized = True
        print("Firebase inicializado.")
    else:
        print("Firebase ya ha sido inicializado previamente.")

def download_video_with_selenium(url, download_folder='downloads'):
    chrome_options = webdriver.ChromeOptions()
    prefs = {'download.default_directory': os.path.abspath(download_folder)}
    chrome_options.add_experimental_option('prefs', prefs)
    
    # Usar la ruta seleccionada para chromedriver.exe
    driver_path = chrome_driver_path_entry.get()
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(url)
        try:
            download_button = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, '//a[@id="downloadButton"]'))  # id PATH de el boton de descarga de mediafire
            )
            download_button.click()
            print("Botón de descarga clicado.")
        except Exception as e:
            print(f"Error al encontrar el botón de descarga: {e}")
            return None
        
        while True:
            time.sleep(1)
            downloaded_files = [f for f in os.listdir(download_folder) if f.endswith('.crdownload')]  # crdownload es el formato de archivos de chrome aun en descarga
            if not downloaded_files:
                break

        print("Descarga completada.")
    finally:
        driver.quit()
    
    downloaded_file = max([os.path.join(download_folder, f) for f in os.listdir(download_folder)], key=os.path.getctime)
    print(f"Archivo descargado: {downloaded_file}")
    return downloaded_file

def extract_file(zip_or_rar_file, extract_to='downloads'):
    extracted_video = None

    if zip_or_rar_file.endswith('.zip'):
        with zipfile.ZipFile(zip_or_rar_file, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            print(f"Archivo ZIP descomprimido en: {extract_to}")
    elif zip_or_rar_file.endswith('.rar'):
        rarfile.UNRAR_TOOL = unrar_tool_path_entry.get()
        with rarfile.RarFile(zip_or_rar_file) as rar_ref:
            rar_ref.extractall(extract_to)
            print(f"Archivo RAR descomprimido en: {extract_to}")
    else:
        print("El archivo no es un ZIP ni un RAR.")
        return None

    extracted_files = os.listdir(extract_to)
    print(f"Archivos extraídos: {extracted_files}")
    
    for file in extracted_files:
        full_path = os.path.join(extract_to, file)
        if os.path.isdir(full_path):
            video_files = os.listdir(full_path)
            for video_file in video_files:
                video_full_path = os.path.join(full_path, video_file)
                if is_video_file(video_file):
                    print(f"Archivo de video encontrado en carpeta: {video_file}")
                    mp4_filename = convert_to_mp4(video_full_path, os.path.splitext(video_full_path)[0] + "_converted.mp4")
                    return mp4_filename
        elif is_video_file(file):
            print(f"Archivo de video encontrado en raíz: {file}")
            mp4_filename = convert_to_mp4(full_path, os.path.splitext(full_path)[0] + "_converted.mp4")
            return mp4_filename

    return None

def is_video_file(filename):
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm')
    return filename.endswith(video_extensions)

def convert_to_mp4(video_file, mp4_filename):
    try:
        ffmpeg.input(video_file).output(mp4_filename).run(overwrite_output=True)
        print(f"Conversión a MP4 exitosa: {mp4_filename}")
        return mp4_filename
    except Exception as e:
        print(f"Error en la conversión a MP4: {e}")
        return None

def upload_to_firebase(file_path, folder_name):
    bucket = storage.bucket()
    blob = bucket.blob(f'{folder_name}/{os.path.basename(file_path)}')
    blob.upload_from_filename(file_path)
    print(f"Archivo subido a Firebase: {file_path}")

def delete_downloads_folder(download_folder='downloads'):
    if os.path.exists(download_folder):
        shutil.rmtree(download_folder)
        print(f"Carpeta '{download_folder}' eliminada.")

def browse_file(entry_field):
    file_path = filedialog.askopenfilename()
    entry_field.delete(0, tk.END)
    entry_field.insert(0, file_path)

def start_process(config_path, bucket_name, folder_name, video_urls_entry, progress_bar):
    initialize_firebase(config_path, bucket_name)

    progress_bar['value'] = 0  

    video_urls = video_urls_entry.split(',')
    
    total_videos = len(video_urls)
    for i, video_url in enumerate(video_urls):
        video_url = video_url.strip()
        downloaded_file = download_video_with_selenium(video_url)

        if downloaded_file:
            extracted_file = extract_file(downloaded_file)

            if extracted_file:
                upload_to_firebase(extracted_file, folder_name)
        
        progress_bar['value'] = (i + 1) / total_videos * 100
        progress_bar.update() 

    delete_downloads_folder()

def start_thread(config_path, bucket_name, folder_name, video_urls_entry, progress_bar):
    process_thread = threading.Thread(target=start_process, args=(config_path, bucket_name, folder_name, video_urls_entry, progress_bar))
    process_thread.start()

def main_gui():
    global chrome_driver_path_entry, unrar_tool_path_entry  
    
    window = tk.Tk()
    window.title("Video Uploader Tool")
    
    config_frame = tk.Frame(window)
    config_frame.pack(pady=10)
    
    tk.Label(config_frame, text="Ruta del archivo de configuración de Firebase:").grid(row=0, column=0)
    firebase_config_entry = tk.Entry(config_frame, width=50)
    firebase_config_entry.grid(row=0, column=1)
    tk.Button(config_frame, text="Buscar", command=lambda: browse_file(firebase_config_entry)).grid(row=0, column=2)

    tk.Label(config_frame, text="Nombre del bucket de Firebase:").grid(row=1, column=0)
    bucket_name_entry = tk.Entry(config_frame, width=50)
    bucket_name_entry.grid(row=1, column=1)

    tk.Label(config_frame, text="Carpeta de destino en Firebase:").grid(row=2, column=0)
    folder_name_entry = tk.Entry(config_frame, width=50)
    folder_name_entry.grid(row=2, column=1)

    tk.Label(config_frame, text="URLs de los videos (separadas por comas):").grid(row=3, column=0)
    video_urls_entry = tk.Entry(config_frame, width=50)
    video_urls_entry.grid(row=3, column=1)

    tk.Label(config_frame, text="Ruta del chromedriver:").grid(row=4, column=0)
    chrome_driver_path_entry = tk.Entry(config_frame, width=50)
    chrome_driver_path_entry.grid(row=4, column=1)
    tk.Button(config_frame, text="Buscar", command=lambda: browse_file(chrome_driver_path_entry)).grid(row=4, column=2)

    tk.Label(config_frame, text="Ruta de unrar.exe:").grid(row=5, column=0)
    unrar_tool_path_entry = tk.Entry(config_frame, width=50)
    unrar_tool_path_entry.grid(row=5, column=1)
    tk.Button(config_frame, text="Buscar", command=lambda: browse_file(unrar_tool_path_entry)).grid(row=5, column=2)

    start_button = tk.Button(window, text="Iniciar", command=lambda: start_thread(firebase_config_entry.get(), bucket_name_entry.get(), folder_name_entry.get(), video_urls_entry.get(), progress_bar))
    start_button.pack(pady=10)

    progress_bar = ttk.Progressbar(window, orient="horizontal", length=400, mode="determinate")
    progress_bar.pack(pady=10)

    console_frame = tk.Frame(window)
    console_frame.pack(pady=10)

    console_text = scrolledtext.ScrolledText(console_frame, height=10, width=80)
    console_text.pack()
    sys.stdout = ConsoleRedirect(console_text)

    window.mainloop()

if __name__ == "__main__":
    main_gui()
