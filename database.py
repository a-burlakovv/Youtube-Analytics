# database.py
import sqlite3
from datetime import datetime, date, timezone
# Импортируем загрузчик конфигурации
import config_loader as app_config

# Используем имя БД из конфигурации
DB_NAME = app_config.DATABASE_NAME

def connect_db():
    """Устанавливает соединение с базой данных SQLite."""
    try:
        # Убираем detect_types, т.к. будем конвертировать вручную при чтении
        conn = sqlite3.connect(DB_NAME)
        print(f"DEBUG DB: Successfully connected to database '{DB_NAME}'.")
        return conn
    except sqlite3.Error as e:
        print(f"ERROR DB: Could not connect to database '{DB_NAME}': {e}")
        return None

def create_tables(conn):
    """Создает таблицы channels и videos, если они еще не существуют."""
    if not conn: return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                channel_name TEXT,
                uploads_playlist_id TEXT,
                last_fetched INTEGER, -- Время последнего обновления (Unix timestamp)
                subscriber_count INTEGER, -- Количество подписчиков
                date_added DATE -- Дата первого добавления канала в БД
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                title TEXT,
                published_at INTEGER, -- Дата публикации видео (Unix timestamp UTC)
                duration_seconds INTEGER,
                view_count INTEGER,
                like_count INTEGER,
                comment_count INTEGER,
                fetch_date TEXT, -- Дата получения данных из API (YYYY-MM-DD)
                FOREIGN KEY (channel_id) REFERENCES channels (channel_id)
            )
        """)
        conn.commit()
        print("DEBUG DB: Tables 'channels' and 'videos' checked/created successfully (with subscribers, date_added).") # Обновлено сообщение
    except sqlite3.Error as e:
        print(f"ERROR DB: Failed to create tables: {e}")

def save_channel(conn, channel_data):
    """
    Сохраняет или обновляет информацию о канале в таблице channels.
    `date_added` устанавливается только при первой вставке.
    """
    if not conn: return False
    # Добавляем subscriber_count и date_added
    sql = """
        INSERT INTO channels (channel_id, channel_name, uploads_playlist_id,
                              last_fetched, subscriber_count, date_added)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET
            channel_name = excluded.channel_name,
            uploads_playlist_id = excluded.uploads_playlist_id,
            last_fetched = excluded.last_fetched,
            subscriber_count = excluded.subscriber_count
            -- date_added НЕ обновляется при конфликте
    """
    try:
        cursor = conn.cursor()
        now_timestamp = int(datetime.now(timezone.utc).timestamp())
        today_date = datetime.now().date() # Получаем текущую дату
        sub_count = channel_data.get('subscriber_count') # Может быть None

        # Преобразуем в int, если не None, иначе оставляем None для БД
        if sub_count is not None:
             try:
                 sub_count = int(sub_count)
             except (ValueError, TypeError):
                 print(f"Warning DB: Could not convert subscriber count '{sub_count}' to int for channel {channel_data.get('id')}. Setting to NULL.")
                 sub_count = None # Сохраняем как NULL, если не можем конвертировать

        cursor.execute(sql, (
            channel_data.get('id'),
            channel_data.get('title'),
            channel_data.get('uploads_playlist_id'),
            now_timestamp,
            sub_count,          # Сохраняем количество подписчиков (может быть None)
            today_date          # Устанавливаем дату добавления (игнорируется при UPDATE)
        ))
        conn.commit()
        print(f"DEBUG DB: Channel '{channel_data.get('title')}' (ID: {channel_data.get('id')}) saved/updated (Subs: {sub_count}, Added: {today_date} - if new).") # Обновлено сообщение
        return True
    except sqlite3.Error as e:
        print(f"ERROR DB: Failed to save channel {channel_data.get('id')}: {e}")
        return False

# --- Добавим функцию для чтения даты добавления ---
def get_channel_add_date(conn, channel_id):
    """Получает дату добавления канала из базы данных."""
    if not conn: return None
    sql = "SELECT date_added FROM channels WHERE channel_id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (channel_id,))
        result = cursor.fetchone()
        if result and result[0]:
            # SQLite хранит DATE как TEXT 'YYYY-MM-DD', конвертируем обратно в date
            try:
                return date.fromisoformat(result[0])
            except (TypeError, ValueError):
                print(f"Warning DB: Could not parse date_added '{result[0]}' for channel {channel_id}")
                return None
        return None
    except sqlite3.Error as e:
        print(f"ERROR DB: Failed to get channel add date for {channel_id}: {e}")
        return None

# --- Новая функция для получения общего кол-ва видео канала в БД ---
def get_total_videos_count(conn, channel_id):
    """Получает общее количество видео для канала, сохраненных в БД."""
    if not conn: return 0
    sql = "SELECT COUNT(video_id) FROM videos WHERE channel_id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (channel_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    except sqlite3.Error as e:
        print(f"ERROR DB: Failed to get total videos count for {channel_id}: {e}")
        return 0

# --- Добавление функции для чтения подписчиков ---
def get_channel_subscribers(conn, channel_id):
    """Получает количество подписчиков канала из базы данных."""
    if not conn: return None
    sql = "SELECT subscriber_count FROM channels WHERE channel_id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (channel_id,))
        result = cursor.fetchone()
        # Возвращаем None если в базе NULL или канал не найден
        return result[0] if result and result[0] is not None else None
    except sqlite3.Error as e:
        print(f"ERROR DB: Failed to get channel subscribers for {channel_id}: {e}")
        return None

def save_videos(conn, videos_data, channel_id):
    """Сохраняет или обновляет информацию о видео в таблице videos."""
    if not conn: return False
    if not videos_data: return True

    sql = """
        INSERT INTO videos (video_id, channel_id, title, published_at, duration_seconds,
                          view_count, like_count, comment_count, fetch_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            title = excluded.title,
            published_at = excluded.published_at,
            duration_seconds = excluded.duration_seconds,
            view_count = excluded.view_count,
            like_count = excluded.like_count,
            comment_count = excluded.comment_count,
            fetch_date = excluded.fetch_date
    """
    videos_to_save = []
    for video in videos_data:
        published_dt = video.get('published_at') # Это datetime объект
        # Конвертируем в Unix timestamp UTC, если дата есть, иначе NULL
        published_timestamp = int(published_dt.timestamp()) if published_dt else None

        fetch_dt = video.get('fetch_date')
        fetch_date_str = fetch_dt.isoformat() if isinstance(fetch_dt, date) else None

        videos_to_save.append((
            video.get('id'),
            channel_id,
            video.get('title'),
            published_timestamp, # Сохраняем как INTEGER
            video.get('duration_seconds'),
            video.get('view_count'),
            video.get('like_count'),
            video.get('comment_count'),
            fetch_date_str
        ))

    try:
        cursor = conn.cursor()
        cursor.executemany(sql, videos_to_save)
        conn.commit()
        print(f"DEBUG DB: Saved/updated {len(videos_to_save)} videos for channel {channel_id}.")
        return True
    except sqlite3.Error as e:
        print(f"ERROR DB: Failed to save videos for channel {channel_id}: {e}")
        return False

def get_video_stats_for_channel(conn, channel_id):
    """
    Извлекает статистику (просмотры, лайки, длительность) для всех видео
    указанного канала из базы данных.

    Args:
        conn: Объект соединения с БД.
        channel_id (str): ID канала, для которого нужно получить статистику видео.

    Returns:
        list: Список кортежей, где каждый кортеж содержит (view_count, like_count, duration_seconds)
              для одного видео. Возвращает пустой список, если канал не найден или нет видео.
    """
    if not conn:
        print("ERROR DB: No connection provided to get_video_stats.")
        return []

    stats_data = []
    sql = """
        SELECT view_count, like_count, duration_seconds
        FROM videos
        WHERE channel_id = ?
          AND view_count IS NOT NULL   -- Игнорируем видео без статистики просмотров
          AND like_count IS NOT NULL   -- Игнорируем видео без статистики лайков (если важно)
          AND duration_seconds > 0     -- Игнорируем видео с нулевой длительностью (например, ошибки парсинга)
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (channel_id,))
        rows = cursor.fetchall() # Получаем все строки результата

        # Преобразуем строки в список кортежей с целыми числами
        for row in rows:
            # row[0] = view_count, row[1] = like_count, row[2] = duration_seconds
            # Убедимся, что значения действительно числовые перед добавлением
            try:
                views = int(row[0])
                likes = int(row[1])
                duration = int(row[2])
                stats_data.append((views, likes, duration))
            except (TypeError, ValueError):
                # Пропускаем строку, если данные не могут быть преобразованы в int
                print(f"DEBUG DB: Skipping row with non-integer data: {row} for channel {channel_id}")
                continue

        print(f"DEBUG DB: Fetched stats for {len(stats_data)} videos from DB for channel {channel_id}.")
        return stats_data
    except sqlite3.Error as e:
        print(f"ERROR DB: Failed to fetch video stats for channel {channel_id}: {e}")
        return []

# --- Новая функция для получения названия канала из БД ---
def get_channel_name(conn, channel_id):
    """Получает название канала по его ID из базы данных."""
    if not conn: return None
    sql = "SELECT channel_name FROM channels WHERE channel_id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (channel_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        print(f"ERROR DB: Failed to get channel name for {channel_id}: {e}")
        return None

def get_videos_published_between(conn, channel_id, start_date, end_date):
    """
    Извлекает данные видео, опубликованных в заданном диапазоне дат [start_date, end_date).
    Использует Unix timestamps для сравнения.
    """
    if not conn: return []
    videos_data = []
    start_ts = int(datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc).timestamp())
    end_ts = int(datetime.combine(end_date, datetime.min.time(), tzinfo=timezone.utc).timestamp())

    # !!! Добавляем duration_seconds в SELECT !!!
    sql = """
        SELECT video_id, published_at, view_count, like_count, comment_count, duration_seconds
        FROM videos
        WHERE channel_id = ?
          AND published_at >= ?
          AND published_at < ?
          AND published_at IS NOT NULL
          AND view_count IS NOT NULL
          AND like_count IS NOT NULL
          AND comment_count IS NOT NULL
          AND duration_seconds IS NOT NULL -- Добавим проверку и на длительность
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (channel_id, start_ts, end_ts))
        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]

        for row in rows:
            row_dict = dict(zip(column_names, row))
            timestamp = row_dict.get('published_at')
            # Конвертируем timestamp и проверяем числовые значения
            try:
                 row_dict['published_at'] = datetime.fromtimestamp(int(timestamp), tz=timezone.utc) if timestamp is not None else None
                 row_dict['view_count'] = int(row_dict['view_count'])
                 row_dict['like_count'] = int(row_dict['like_count'])
                 row_dict['comment_count'] = int(row_dict['comment_count'])
                 row_dict['duration_seconds'] = int(row_dict['duration_seconds']) # Добавлено преобразование для длительности
                 if row_dict['published_at'] is not None: # Добавляем только если дата ок
                      videos_data.append(row_dict)
            except (TypeError, ValueError, OSError) as e: # OSError для невалидных timestamp
                 print(f"DEBUG DB: Skipping video {row_dict.get('video_id')} due to data conversion error: {e}")
                 continue

        print(f"DEBUG DB: Fetched {len(videos_data)} videos published between {start_date} and {end_date} (timestamps {start_ts} to {end_ts}) for channel {channel_id}.")
        return videos_data
    except sqlite3.Error as e:
        print(f"ERROR DB: Failed to fetch videos between dates for channel {channel_id}: {e}")
        return []