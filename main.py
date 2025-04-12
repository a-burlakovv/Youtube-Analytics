print("DEBUG: Starting main.py execution...")

# --- Импорты ---
import sys
import os
# Импортируем наши модули
import youtube_api
import database
import analyzer
import config_loader as app_config # Импортируем загрузчик конфигурации
# Остальные импорты
from datetime import datetime, timedelta, date
import math
import pprint
import traceback
try:
    from tabulate import tabulate
except ImportError:
    print("WARNING: 'tabulate' library not found...")
    tabulate = None
try:
    import isodate
except ImportError:
    print("ERROR: 'isodate' library not found. Please install it using: pip install isodate")
    sys.exit(1)


# --- КОНФИГУРАЦИЯ ---
CHANNELS_FILE = 'channels.txt'
MAX_VIDEOS_TO_FETCH_PER_CHANNEL = 50
FETCH_DATA_FROM_API = True
ANALYZE_DATA_FROM_DB = True

print(f"DEBUG: Channels file: {CHANNELS_FILE}")
print(f"DEBUG: Max videos to fetch per channel: {MAX_VIDEOS_TO_FETCH_PER_CHANNEL}")
print(f"DEBUG: Fetch data from API: {FETCH_DATA_FROM_API}")
print(f"DEBUG: Analyze data from DB: {ANALYZE_DATA_FROM_DB}")


# --- Функции ---
def load_channel_ids(filename):
    """Загружает ID каналов из файла (по одному ID на строку)."""
    if not os.path.exists(filename):
        print(f"ERROR: Channels file '{filename}' not found.")
        return []
    try:
        with open(filename, 'r', encoding='utf-8') as f: # Добавим кодировку
            ids = [line.strip() for line in f if line.strip()]
        print(f"DEBUG: Loaded {len(ids)} channel IDs from '{filename}'.")
        return ids
    except Exception as e:
        print(f"ERROR: Failed to read channels file '{filename}': {e}")
        return []

# --- Основная логика ---
if __name__ == "__main__":
    print("DEBUG: Inside __main__ block.")
    print("--- YouTube Channel Analyzer - Configured Run ---") # Обновили название этапа

    # Загружаем ID каналов из файла, указанного в конфигурации
    channel_ids_to_process = load_channel_ids(app_config.CHANNELS_FILE)
    if not channel_ids_to_process:
        sys.exit("ERROR: No channel IDs to process. Exiting.")

    conn = None
    all_results = []

    try:
        # Используем имя БД из конфигурации
        conn = database.connect_db() # database.py теперь сам использует имя из app_config
        if not conn:
            sys.exit("ERROR: Could not connect to database. Exiting.")

        database.create_tables(conn)

        total_channels = len(channel_ids_to_process)
        for i, channel_id in enumerate(channel_ids_to_process):
            print(f"\n=== Processing Channel ID: {channel_id} ({i+1}/{total_channels}) ===")
            # Инициализация словаря результатов (без изменений)
            channel_results = {
                'channel_id': channel_id, 'channel_name': None, 'date_added': None,
                'subscriber_count': None, 'observed_videos_count': 0,
                'avg_views': None, 'max_views': None, 'min_views': None, 'avg_likes': None,
                'max_likes': None, 'min_likes': None, 'avg_duration_sec': None,
                'max_duration_sec': None, 'min_duration_sec': None, 'avg_duration_sec_30d': None,
                'avg_views_per_video_30d': None, 'videos_last_30d_count': 0,
                'avg_engagement_rate': 0.0, 'views_sum_last_30d': 0, 'view_trend_ratio': None }

            # --- Получение данных из БД --- (без изменений)
            channel_results['channel_name'] = database.get_channel_name(conn, channel_id)
            channel_results['date_added'] = database.get_channel_add_date(conn, channel_id)
            channel_results['subscriber_count'] = database.get_channel_subscribers(conn, channel_id)
            channel_results['observed_videos_count'] = database.get_total_videos_count(conn, channel_id)
            print(f"DEBUG DB: Channel Name: {channel_results['channel_name']}, Added: {channel_results['date_added']}, Subs (DB): {channel_results['subscriber_count']}, Videos in DB: {channel_results['observed_videos_count']}")

            # --- 1. Получение данных из API (используем флаг из конфигурации) ---
            if app_config.FETCH_DATA_FROM_API:
                print("\n--- Fetching data from API ---")
                channel_info = youtube_api.get_channel_details(channel_id)
                if channel_info:
                    channel_results['channel_name'] = channel_info['title']
                    sub_count_str = channel_info.get('subscriber_count')
                    sub_count_int = None
                    if sub_count_str is not None:
                        try: sub_count_int = int(sub_count_str)
                        except (ValueError, TypeError): sub_count_int = None
                    channel_results['subscriber_count'] = sub_count_int
                    database.save_channel(conn, channel_info)
                    uploads_playlist_id = channel_info.get('uploads_playlist_id')
                    if uploads_playlist_id:
                        # Используем MAX_VIDEOS из конфигурации
                        video_ids = youtube_api.get_playlist_video_ids(uploads_playlist_id, max_results=app_config.MAX_VIDEOS_TO_FETCH_PER_CHANNEL)
                        if video_ids:
                            videos_data = youtube_api.get_video_details(video_ids)
                            if videos_data:
                                database.save_videos(conn, videos_data, channel_id)
                                channel_results['observed_videos_count'] = database.get_total_videos_count(conn, channel_id)
                            else: print("Warning: No video details received from API.")
                        else: print("Warning: No video IDs received from API.")
                    else: print(f"Warning: No uploads playlist ID found for {channel_id}")
                else: print(f"Warning: Failed to fetch channel details from API for {channel_id}. Skipping API update.")
            else:
                # --- Логика пропуска API и получения только имени/сабов --- (без изменений, кроме вывода)
                 print("\n--- Skipping API data fetch (FETCH_FROM_API is False in config.ini) ---")
                 if not channel_results['channel_name'] or channel_results['subscriber_count'] is None:
                     # ... (код получения имени/сабов) ...
                     channel_info_name_only = youtube_api.get_channel_details(channel_id)
                     if channel_info_name_only:
                         channel_results['channel_name'] = channel_info_name_only['title']
                         sub_count_str = channel_info_name_only.get('subscriber_count')
                         sub_count_int = None
                         if sub_count_str is not None:
                             try: sub_count_int = int(sub_count_str)
                             except (ValueError, TypeError): sub_count_int = None
                         channel_results['subscriber_count'] = sub_count_int
                         database.save_channel(conn, channel_info_name_only)


            if not channel_results['channel_name']: channel_results['channel_name'] = f"Unknown (ID: {channel_id})"

            # --- 2. Анализ данных из БД (используем флаг из конфигурации) ---
            if app_config.ANALYZE_DATA_FROM_DB:
                # ... (весь блок анализа остается без изменений) ...
                print(f"\n--- Analyzing data from Database for channel: {channel_results['channel_name']} ---")
                video_stats_list = database.get_video_stats_for_channel(conn, channel_id)
                basic_stats = analyzer.calculate_basic_stats(video_stats_list) if video_stats_list else None
                if basic_stats: channel_results.update(basic_stats)
                today = datetime.now().date()
                date_30_days_ago = today - timedelta(days=30)
                date_60_days_ago = today - timedelta(days=60)
                videos_last_30d = database.get_videos_published_between(conn, channel_id, date_30_days_ago, today)
                videos_prev_30d = database.get_videos_published_between(conn, channel_id, date_60_days_ago, date_30_days_ago)
                channel_results['videos_last_30d_count'] = len(videos_last_30d)
                channel_results['avg_engagement_rate'] = analyzer.calculate_average_engagement_rate(videos_last_30d)
                channel_results['views_sum_last_30d'] = sum(v.get('view_count', 0) for v in videos_last_30d)
                if channel_results['videos_last_30d_count'] > 0:
                    total_duration_30d = sum(v.get('duration_seconds', 0) for v in videos_last_30d)
                    channel_results['avg_duration_sec_30d'] = round(total_duration_30d / channel_results['videos_last_30d_count']) if total_duration_30d > 0 else 0
                    channel_results['avg_views_per_video_30d'] = round(channel_results['views_sum_last_30d'] / channel_results['videos_last_30d_count'])
                else:
                     channel_results['avg_duration_sec_30d'] = 0
                     channel_results['avg_views_per_video_30d'] = 0
                views_sum_prev_30d = sum(v.get('view_count', 0) for v in videos_prev_30d)
                view_trend_ratio = None
                if views_sum_prev_30d > 0: view_trend_ratio = round(channel_results['views_sum_last_30d'] / views_sum_prev_30d, 2)
                elif channel_results['views_sum_last_30d'] > 0: view_trend_ratio = float('inf')
                channel_results['view_trend_ratio'] = view_trend_ratio
                print(f"DEBUG: Analysis complete for {channel_results['channel_name']}.")
            else:
                 print("\n--- Skipping Database analysis (ANALYZE_FROM_DB is False in config.ini) ---")

            all_results.append(channel_results)
            print(f"=== Finished Processing Channel ID: {channel_id} ===")

        # --- 3. Расчет Рангов --- (без изменений)
        if app_config.ANALYZE_DATA_FROM_DB: # Только если был анализ
             print("\n=== Calculating Ranks ===")
             ranked_results = analyzer.calculate_ranks(all_results)
             print(f"DEBUG: Ranking completed.")
        else:
             ranked_results = all_results # Используем all_results если не было анализа/ранжирования

        # --- 4. Вывод таблицы --- (без изменений)
        if app_config.ANALYZE_DATA_FROM_DB: # Только если был анализ
            print("\n--- Final Results & Ranking ---")
            if ranked_results:
                # ... (логика вывода таблицы tabulate) ...
                 headers = ["Rank(Views)", "Channel Name", "Subs", "Rank", "Videos(30d)", "Rank", "Avg ER(%)", "Rank", "Avg Views/Vid(30d)", "Rank", "Avg Dur(30d)", "Rank", "Trend(%)", "Rank", "Date Added", "Obs. Videos"]
                 metrics_map = [ ('rank_avg_views', ""), ('channel_name', ""), ('subscriber_count', ""), ('rank_subscriber_count', ""), ('videos_last_30d_count', ""), ('rank_videos_last_30d_count', ""), ('avg_engagement_rate', ""), ('rank_avg_engagement_rate', ""), ('avg_views_per_video_30d', ""), ('rank_avg_views_per_video_30d', ""), ('avg_duration_sec_30d', ""), ('rank_avg_duration_sec_30d', ""), ('view_trend_ratio', ""), ('rank_view_trend_ratio', ""), ('date_added', ""), ('observed_videos_count', "") ]
                 table_data = []
                 ranked_results.sort(key=lambda x: x.get('rank_avg_views', float('inf')))
                 for channel in ranked_results:
                      row = []
                      for key, _ in metrics_map:
                          value = channel.get(key)
                          formatted_value = "N/A"
                          if value is not None:
                              if 'rank_' in key: formatted_value = value
                              elif key == 'subscriber_count': formatted_value = f"{value:,}" if isinstance(value, int) else 'Hidden'
                              elif key == 'videos_last_30d_count': formatted_value = f"{value:,}"
                              elif key == 'avg_engagement_rate': formatted_value = f"{value:.2f}"
                              elif key == 'avg_views_per_video_30d': formatted_value = f"{value:,}"
                              elif key == 'avg_duration_sec_30d': formatted_value = analyzer.format_duration(value)
                              elif key == 'view_trend_ratio':
                                  if value == float('inf'): formatted_value = "+Inf%"
                                  else: formatted_value = f"{(value - 1) * 100:+.1f}%"
                              elif key == 'date_added': formatted_value = value.isoformat() if isinstance(value, date) else str(value)
                              elif key == 'observed_videos_count': formatted_value = f"{value:,}"
                              elif key == 'channel_name': formatted_value = str(value)
                              else: formatted_value = str(value)
                          row.append(formatted_value)
                      table_data.append(row)
                 if tabulate:
                     print(tabulate(table_data, headers=headers, tablefmt="grid", numalign="right", stralign="left"))
                 else:
                     print(" | ".join(headers)); print("-" * (len(" | ".join(headers)) + 20)); [print(" | ".join(map(str, row))) for row in table_data]

            else: print("No results to display.")

        # --- 5. Расчет агрегатов по группе --- (без изменений)
        if app_config.ANALYZE_DATA_FROM_DB and ranked_results: # Только если был анализ
            print("\n=== Calculating Group Aggregates (Min/Avg/Max) ===")
            group_stats = {}
            metrics_to_aggregate = [ 'subscriber_count', 'observed_videos_count', 'avg_views', 'avg_likes', 'avg_duration_sec', 'avg_duration_sec_30d', 'avg_views_per_video_30d', 'videos_last_30d_count', 'avg_engagement_rate', 'views_sum_last_30d', 'view_trend_ratio' ]
            for metric in metrics_to_aggregate:
                valid_values = []
                for channel_data in ranked_results:
                    value = channel_data.get(metric)
                    if value is not None:
                        if metric == 'view_trend_ratio' and value == float('inf'): continue
                        if isinstance(value, (int, float)) and not math.isinf(value): valid_values.append(value)
                if valid_values:
                    min_val, max_val, avg_val = min(valid_values), max(valid_values), sum(valid_values) / len(valid_values)
                    group_stats[metric] = {'min': min_val, 'avg': avg_val, 'max': max_val, 'count': len(valid_values)}
                    # print(f"DEBUG Group Stats: Metric '{metric}' - Count: {len(valid_values)}, Min: {min_val}, Avg: {avg_val:.2f}, Max: {max_val}") # Сократим лог
                else:
                    group_stats[metric] = {'min': None, 'avg': None, 'max': None, 'count': 0}
                    # print(f"DEBUG Group Stats: Metric '{metric}' - No valid values found.")

            print("\n--- Group Aggregate Statistics ---")
            pp = pprint.PrettyPrinter(indent=2)
            pp.pprint(group_stats)

    except Exception as e:
        print(f"\n!!! UNEXPECTED ERROR in main execution: {e} !!!")
        traceback.print_exc()
    finally:
        if conn:
            conn.close()
            print("\nDEBUG DB: Database connection closed.")

    print("----------------------------------------------------------------")
    print("DEBUG: End of main.py script.")