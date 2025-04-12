# config_loader.py
import configparser
import os
import sys

CONFIG_FILENAME = 'config.ini'

# --- Значения по умолчанию на случай проблем с файлом конфигурации ---
DEFAULT_API_KEYS = []
DEFAULT_DB_NAME = 'youtube_analytics_default.db'
DEFAULT_CHANNELS_FILE = 'channels_default.txt'
DEFAULT_MAX_VIDEOS = 50
DEFAULT_FETCH_API = True
DEFAULT_ANALYZE_DB = True

# --- Чтение конфигурации ---
config = configparser.ConfigParser(allow_no_value=True) # allow_no_value для пустых ключей, если нужно
loaded_files = config.read(CONFIG_FILENAME, encoding='utf-8') # Укажем кодировку

if not loaded_files:
    print(f"WARNING: Configuration file '{CONFIG_FILENAME}' not found. Using default settings.")
    API_KEYS = DEFAULT_API_KEYS
    DATABASE_NAME = DEFAULT_DB_NAME
    CHANNELS_FILE = DEFAULT_CHANNELS_FILE
    MAX_VIDEOS_TO_FETCH_PER_CHANNEL = DEFAULT_MAX_VIDEOS
    FETCH_DATA_FROM_API = DEFAULT_FETCH_API
    ANALYZE_DATA_FROM_DB = DEFAULT_ANALYZE_DB
else:
    print(f"DEBUG Config: Loaded configuration from '{CONFIG_FILENAME}'")
    # --- Секция [API] ---
    try:
        keys_str = config.get('API', 'KEYS', fallback='')
        # Разделяем по запятой, убираем пробелы, фильтруем пустые строки
        API_KEYS = [key.strip() for key in keys_str.split(',') if key.strip() and 'YOUR_' not in key]
        if not API_KEYS:
            print("WARNING: No valid API keys found in [API] -> KEYS section of config.ini (or only placeholder keys present). Using default (empty list).")
            API_KEYS = DEFAULT_API_KEYS
    except (configparser.NoSectionError, configparser.NoOptionError):
        print("WARNING: [API] section or KEYS option not found in config.ini. Using default (empty list).")
        API_KEYS = DEFAULT_API_KEYS

    # --- Секция [FILES] ---
    try:
        DATABASE_NAME = config.get('FILES', 'DATABASE_NAME', fallback=DEFAULT_DB_NAME)
        CHANNELS_FILE = config.get('FILES', 'CHANNELS_FILE', fallback=DEFAULT_CHANNELS_FILE)
    except configparser.NoSectionError:
        print("WARNING: [FILES] section not found in config.ini. Using default file paths.")
        DATABASE_NAME = DEFAULT_DB_NAME
        CHANNELS_FILE = DEFAULT_CHANNELS_FILE

    # --- Секция [SETTINGS] ---
    try:
        # Используем getint для числа
        max_videos_raw = config.getint('SETTINGS', 'MAX_VIDEOS_TO_FETCH', fallback=DEFAULT_MAX_VIDEOS)
        if max_videos_raw <= 0:
            MAX_VIDEOS_TO_FETCH_PER_CHANNEL = None # None означает "без лимита" в логике API
            print("DEBUG Config: MAX_VIDEOS_TO_FETCH <= 0, set to None (fetch all available).")
        else:
            MAX_VIDEOS_TO_FETCH_PER_CHANNEL = max_videos_raw

        # Используем getboolean для флагов True/False
        FETCH_DATA_FROM_API = config.getboolean('SETTINGS', 'FETCH_FROM_API', fallback=DEFAULT_FETCH_API)
        ANALYZE_DATA_FROM_DB = config.getboolean('SETTINGS', 'ANALYZE_FROM_DB', fallback=DEFAULT_ANALYZE_DB)
    except configparser.NoSectionError:
        print("WARNING: [SETTINGS] section not found in config.ini. Using default settings.")
        MAX_VIDEOS_TO_FETCH_PER_CHANNEL = DEFAULT_MAX_VIDEOS
        FETCH_DATA_FROM_API = DEFAULT_FETCH_API
        ANALYZE_DATA_FROM_DB = DEFAULT_ANALYZE_DB
    except ValueError as e:
         print(f"ERROR: Invalid value type in [SETTINGS] section of config.ini: {e}. Check if MAX_VIDEOS_TO_FETCH is an integer and boolean flags are True/False. Using defaults for settings.")
         MAX_VIDEOS_TO_FETCH_PER_CHANNEL = DEFAULT_MAX_VIDEOS
         FETCH_DATA_FROM_API = DEFAULT_FETCH_API
         ANALYZE_DATA_FROM_DB = DEFAULT_ANALYZE_DB

# --- Финальная проверка критичных настроек ---
if not API_KEYS:
    print("CRITICAL ERROR: No API keys available after checking config.ini and defaults. YouTube API calls will fail. Exiting.")
    sys.exit(1) # Выход, если нет ключей API

# --- Вывод загруженной конфигурации для проверки ---
print("--- Loaded Configuration ---")
print(f"API Keys Loaded: {len(API_KEYS)}")
print(f"Database File: {DATABASE_NAME}")
print(f"Channels File: {CHANNELS_FILE}")
print(f"Max Videos To Fetch: {MAX_VIDEOS_TO_FETCH_PER_CHANNEL if MAX_VIDEOS_TO_FETCH_PER_CHANNEL is not None else 'All'}")
print(f"Fetch from API: {FETCH_DATA_FROM_API}")
print(f"Analyze from DB: {ANALYZE_DATA_FROM_DB}")
print("---------------------------")