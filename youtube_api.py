from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# Заменяем импорт config на config_loader
import config_loader as app_config
import isodate
import re
from datetime import datetime, timezone
import time

# Глобальный сервис API - без изменений
youtube_service = None

# !!! Функция get_authenticated_service теперь использует app_config.API_KEYS[0]
#    (если мы не используем менеджер ключей, который сейчас отложен)
def get_authenticated_service():
    """
    Инициализирует и возвращает объект сервиса YouTube API.
    Использует ПЕРВЫЙ ключ из списка в config_loader.py.
    """
    global youtube_service
    if not app_config.API_KEYS: # Проверка, что ключи есть
        print("ERROR youtube_api: No API keys loaded from configuration.")
        return None

    if youtube_service is None:
        current_key = app_config.API_KEYS[0] # Берем первый ключ
        print(f"Initializing YouTube service with the first key from config.")
        try:
            youtube_service = build('youtube', 'v3', developerKey=current_key)
            print("YouTube Service Initialized Successfully.")
        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred during service initialization with key: {current_key[:4]}...{current_key[-4:]}\n{e.content}")
            youtube_service = None
            return None
        except Exception as e:
            print(f"An unexpected error occurred during service initialization: {e}")
            youtube_service = None
            return None
    return youtube_service

def get_channel_details(channel_id):
    """
    Получает информацию о канале, включая ID плейлиста загрузок и кол-во подписчиков.
    """
    youtube = get_authenticated_service()
    if not youtube: return None

    try:
        request = youtube.channels().list(
            # Добавляем 'statistics' к запрашиваемым частям
            part="snippet,contentDetails,statistics",
            id=channel_id
        )
        response = request.execute()

        if not response.get('items'):
            print(f"Error: No channel found with ID: {channel_id}")
            return None

        channel_item = response['items'][0]
        channel_title = channel_item['snippet']['title']
        uploads_playlist_id = channel_item['contentDetails']['relatedPlaylists']['uploads']

        # Извлекаем статистику, если она есть
        statistics = channel_item.get('statistics', {})
        subscriber_count = statistics.get('subscriberCount') # Может отсутствовать, если скрыто
        # view_count = statistics.get('viewCount') # Общее число просмотров канала (если нужно)
        # video_count = statistics.get('videoCount') # Общее число видео (если нужно)

        # Если подписчики скрыты ('hiddenSubscriberCount' == True), subscriberCount не будет в ответе
        if statistics.get('hiddenSubscriberCount', False):
             print(f"Channel {channel_title}: Subscriber count is hidden.")
             subscriber_count = None # Устанавливаем None, если скрыто

        print(f"Found Channel: {channel_title} (ID: {channel_id})")
        print(f"Uploads Playlist ID: {uploads_playlist_id}")
        print(f"Subscriber Count: {'Hidden' if subscriber_count is None else subscriber_count}") # Обновлено сообщение

        return {
            'id': channel_id,
            'title': channel_title,
            'uploads_playlist_id': uploads_playlist_id,
            'subscriber_count': subscriber_count # Добавляем подписчиков в результат
            # 'total_views': view_count, # Можно добавить при необходимости
            # 'total_videos': video_count # Можно добавить при необходимости
        }

    except HttpError as e:
        # ... обработка ошибок остается прежней ...
        print(f"An HTTP error {e.resp.status} occurred while fetching channel details for {channel_id}:\n{e.content}")
        if e.resp.status == 403 and 'quotaExceeded' in str(e.content): print("!!! YouTube API Quota Exceeded !!!")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while fetching channel details for {channel_id}: {e}")
        return None

def get_playlist_video_ids(playlist_id, max_results=None):
    """
    Получает список ID видео из указанного плейлиста YouTube.

    Args:
        playlist_id (str): ID плейлиста (например, плейлиста загрузок канала).
        max_results (int, optional): Максимальное количество ID видео для возврата.
                                     Если None, попытается получить все видео.
                                     Полезно для ограничения использования квоты.

    Returns:
        list: Список строк с ID видео или пустой список в случае ошибки или отсутствия видео.
    """
    youtube = get_authenticated_service()
    if not youtube:
        return [] # Сервис не инициализирован

    video_ids = []
    next_page_token = None

    print(f"Fetching video IDs from playlist: {playlist_id}...")

    while True:
        try:
            request = youtube.playlistItems().list(
                part='contentDetails', # Нам нужен только videoId из contentDetails
                playlistId=playlist_id,
                maxResults=50, # Максимальное значение за раз
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response.get('items', []):
                video_id = item.get('contentDetails', {}).get('videoId')
                if video_id:
                    video_ids.append(video_id)
                    # Проверяем, не достигли ли мы лимита max_results
                    if max_results is not None and len(video_ids) >= max_results:
                        break # Прерываем внутренний цикл

            # Проверяем, не достигли ли мы лимита max_results после обработки страницы
            if max_results is not None and len(video_ids) >= max_results:
                 print(f"Reached max_results limit ({max_results}).")
                 break # Прерываем внешний цикл while

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                print("No more pages to fetch.")
                break # Больше страниц нет, выходим из цикла

            print(f"Fetching next page (found {len(video_ids)} videos so far)...")


        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred while fetching playlist items:\n{e.content}")
            if e.resp.status == 403 and 'quotaExceeded' in str(e.content):
                print("!!! YouTube API Quota Exceeded during playlist fetch !!!")
            # Возвращаем то, что успели собрать
            break
        except Exception as e:
            print(f"An unexpected error occurred while fetching playlist items: {e}")
            # Возвращаем то, что успели собрать
            break

    print(f"Finished fetching. Total video IDs found: {len(video_ids)}")
    return video_ids[:max_results] if max_results is not None else video_ids # Обрезаем на случай, если последняя страница дала больше нужного

# Можно добавить сюда другие функции API по мере необходимости

def parse_iso8601_duration(duration_str):
    """
    Парсит строку длительности ISO 8601 (например, PT1M35S) в общее количество секунд.
    Использует isodate, с резервным вариантом через regex для простых случаев.
    """
    try:
        # Основной метод через isodate
        duration = isodate.parse_duration(duration_str)
        return int(duration.total_seconds())
    except isodate.ISO8601Error:
        # Резервный метод через regex (обрабатывает только H, M, S)
        # print(f"Warning: isodate could not parse '{duration_str}'. Trying regex.")
        hours = re.search(r'(\d+)H', duration_str)
        minutes = re.search(r'(\d+)M', duration_str)
        seconds = re.search(r'(\d+)S', duration_str)
        total_seconds = 0
        if hours:
            total_seconds += int(hours.group(1)) * 3600
        if minutes:
            total_seconds += int(minutes.group(1)) * 60
        if seconds:
            total_seconds += int(seconds.group(1))
        # Проверяем, удалось ли что-то извлечь
        if total_seconds > 0 or 'PT' in duration_str and (hours or minutes or seconds):
             # print(f"Regex parsed duration '{duration_str}' to {total_seconds} seconds.")
             return total_seconds
        else:
             print(f"Error: Could not parse duration '{duration_str}' using any method.")
             return 0
    except Exception as e:
        print(f"Error parsing duration '{duration_str}': {e}")
        return 0


def get_video_details(video_ids):
    """
    Получает детальную информацию для списка ID видео.
    Запрашивает данные пакетами по 50 ID для экономии квоты.

    Args:
        video_ids (list): Список строк с ID видео.

    Returns:
        list: Список словарей, где каждый словарь содержит детали одного видео:
              {'id', 'title', 'published_at', 'duration_seconds',
               'view_count', 'like_count', 'comment_count'}
              Возвращает пустой список в случае ошибки инициализации API.
              Может вернуть неполный список, если закончилась квота.
    """
    youtube = get_authenticated_service()
    if not youtube:
        return []

    video_details_list = []
    # Обрабатываем ID пакетами по 50 штук
    for i in range(0, len(video_ids), 50):
        chunk_ids = video_ids[i:i+50]
        ids_string = ','.join(chunk_ids) # API требует ID через запятую

        print(f"Fetching details for video IDs chunk ({i+1}-{min(i+50, len(video_ids))}/{len(video_ids)})...")

        try:
            request = youtube.videos().list(
                part="snippet,contentDetails,statistics", # Запрашиваемые части
                id=ids_string,
                maxResults=50
            )
            response = request.execute()

            for item in response.get('items', []):
                video_id = item['id']
                snippet = item.get('snippet', {})
                content_details = item.get('contentDetails', {})
                statistics = item.get('statistics', {}) # Статистика может отсутствовать

                # Извлекаем данные, обрабатывая возможные отсутствующие ключи
                title = snippet.get('title', 'N/A')
                published_at_str = snippet.get('publishedAt')
                # Конвертируем дату публикации в объект datetime
                published_at_dt = None
                if published_at_str:
                    try:
                        published_at_dt = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                    except ValueError:
                        print(f"Warning: Could not parse datetime '{published_at_str}' for video {video_id}")

                duration_str = content_details.get('duration')
                duration_seconds = parse_iso8601_duration(duration_str) if duration_str else 0

                # Статистика может быть скрыта, поэтому используем .get с 0 по умолчанию
                view_count = int(statistics.get('viewCount', 0))
                like_count = int(statistics.get('likeCount', 0)) # Лайки могут быть скрыты
                comment_count = int(statistics.get('commentCount', 0)) # Комментарии могут быть отключены

                video_details_list.append({
                    'id': video_id,
                    'title': title,
                    'published_at': published_at_dt, # Сохраняем как объект datetime
                    'duration_seconds': duration_seconds,
                    'view_count': view_count,
                    'like_count': like_count,
                    'comment_count': comment_count,
                    'fetch_date': datetime.now().date() # Добавим дату сбора данных
                })

        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred while fetching video details:\n{e.content}")
            if e.resp.status == 403 and 'quotaExceeded' in str(e.content):
                print("!!! YouTube API Quota Exceeded during video details fetch !!!")
                print("Returning details fetched so far.")
                break # Прерываем цикл по пакетам ID
            # Можно добавить обработку других ошибок, если нужно
            continue # Пропускаем этот пакет и пытаемся следующий (если ошибка временная)
        except Exception as e:
            print(f"An unexpected error occurred while fetching video details chunk: {e}")
            continue # Пропускаем этот пакет

    print(f"Finished fetching details. Total videos processed: {len(video_details_list)}")
    return video_details_list