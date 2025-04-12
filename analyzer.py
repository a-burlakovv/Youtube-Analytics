import math
from datetime import timedelta
import operator

def format_duration(seconds):
    """Форматирует длительность из секунд в строку HH:MM:SS."""
    if seconds is None or seconds < 0:
        return "N/A"
    delta = timedelta(seconds=int(seconds))
    return str(delta)

def calculate_basic_stats(video_stats_data):
    """
    Рассчитывает минимальную, максимальную и среднюю статистику
    (просмотры, лайки, длительность) на основе списка данных видео.

    Args:
        video_stats_data (list): Список кортежей [(views, likes, duration), ...].

    Returns:
        dict: Словарь с рассчитанными метриками или None, если данных нет.
              Ключи: 'count', 'avg_views', 'max_views', 'min_views', 'avg_likes',
                     'max_likes', 'min_likes', 'avg_duration_sec', 'max_duration_sec',
                     'min_duration_sec', 'avg_duration_str', 'max_duration_str', 'min_duration_str'.
    """
    if not video_stats_data:
        return None # Нечего анализировать

    count = len(video_stats_data)
    # Извлекаем данные в отдельные списки для удобства
    views = [item[0] for item in video_stats_data]
    likes = [item[1] for item in video_stats_data]
    durations = [item[2] for item in video_stats_data]

    stats = {
        'count': count,
        'avg_views': round(sum(views) / count) if count > 0 else 0,
        'max_views': max(views) if views else 0,
        'min_views': min(views) if views else 0,
        'avg_likes': round(sum(likes) / count) if count > 0 else 0,
        'max_likes': max(likes) if likes else 0,
        'min_likes': min(likes) if likes else 0,
        'avg_duration_sec': round(sum(durations) / count) if count > 0 else 0,
        'max_duration_sec': max(durations) if durations else 0,
        'min_duration_sec': min(durations) if durations else 0,
    }

    # Добавляем форматированные значения длительности
    stats['avg_duration_str'] = format_duration(stats['avg_duration_sec'])
    stats['max_duration_str'] = format_duration(stats['max_duration_sec'])
    stats['min_duration_str'] = format_duration(stats['min_duration_sec'])

    return stats

def calculate_average_engagement_rate(video_data_list):
    """
    Рассчитывает средний Engagement Rate (ER) для списка видео.
    Формула: ER = (Лайки + Комментарии) / Просмотры * 100%
    Игнорирует видео с 0 просмотров.

    Args:
        video_data_list (list): Список словарей, каждый содержит ключи
                               'view_count', 'like_count', 'comment_count'.

    Returns:
        float: Средний ER в процентах, или 0.0 если рассчитать не удалось.
    """
    if not video_data_list:
        return 0.0

    total_er = 0.0
    valid_videos_count = 0

    for video in video_data_list:
        views = video.get('view_count', 0)
        likes = video.get('like_count', 0)
        comments = video.get('comment_count', 0)

        # Пропускаем видео без просмотров, чтобы избежать деления на ноль
        if views > 0:
            engagement = likes + comments
            er = (engagement / views) * 100
            total_er += er
            valid_videos_count += 1
        # else:
            # print(f"DEBUG Analyzer: Skipping video (ID: {video.get('video_id', 'N/A')}) for ER calculation due to zero views.")


    if valid_videos_count > 0:
        average_er = total_er / valid_videos_count
        print(f"DEBUG Analyzer: Calculated average ER: {average_er:.2f}% from {valid_videos_count} videos.")
        return round(average_er, 2) # Округляем до 2 знаков после запятой
    else:
        print("DEBUG Analyzer: No videos with views found to calculate average ER.")
        return 0.0

def calculate_ranks(all_channels_data):
    if not all_channels_data: return []
    # ... (словарь metrics_to_rank остается прежним) ...
    metrics_to_rank = {
        'subscriber_count': True, 'observed_videos_count': True, 'avg_views': True,
        'max_views': True, 'min_views': True, 'avg_likes': True, 'max_likes': True,
        'min_likes': True, 'avg_duration_sec': True, 'max_duration_sec': True,
        'min_duration_sec': False, 'avg_duration_sec_30d': True,
        'avg_views_per_video_30d': True, 'videos_last_30d_count': True,
        'avg_engagement_rate': True, 'views_sum_last_30d': True,
        'view_trend_ratio': True,
    }
    ranked_data = [channel.copy() for channel in all_channels_data]

    print("DEBUG Analyzer Ranker: Starting rank calculation...") # Отладка
    for metric, reverse_sort in metrics_to_rank.items():
        rank_key = f'rank_{metric}'
        valid_channels = []
        print(f"DEBUG Analyzer Ranker: Processing metric '{metric}'") # Отладка
        for i, channel in enumerate(ranked_data):
            value = channel.get(metric)
            channel_id_debug = channel.get('channel_id', 'UNKNOWN_ID') # Отладка
            # print(f"DEBUG Analyzer Ranker: Channel {channel_id_debug}, Raw value for {metric}: {value} (type: {type(value)})") # Детальная Отладка (можно раскомментировать)

            # Попытка конвертации в числовой тип, если это ожидается
            numeric_value = None
            if value is not None:
                if metric == 'view_trend_ratio' and value == float('inf'):
                    numeric_value = float('inf')
                # Проверяем остальные метрики (кроме channel_name, date_added и т.п.)
                elif isinstance(value, (int, float)):
                    numeric_value = value
                elif isinstance(value, str): # Попытка конвертировать строку, если она пришла (например, для subs)
                    try:
                        numeric_value = int(value)
                    except ValueError:
                        try:
                            numeric_value = float(value)
                        except ValueError:
                            print(f"Warning Analyzer Ranker: Could not convert string value '{value}' for metric '{metric}' on channel {channel_id_debug}")
                            pass # Оставляем numeric_value = None

            if numeric_value is not None:
                 valid_channels.append({'index': i, 'value': numeric_value})
                 # print(f"DEBUG Analyzer Ranker: Channel {channel_id_debug}, Valid numeric value for {metric}: {numeric_value}") # Отладка
            else:
                 ranked_data[i][rank_key] = None # Устанавливаем ранг None, если значение не валидно

        valid_channels.sort(key=lambda x: x['value'], reverse=reverse_sort)
        print(f"DEBUG Analyzer Ranker: Sorted {len(valid_channels)} channels for metric '{metric}'") # Отладка

        # ... (логика присвоения рангов остается без изменений) ...
        current_rank = 0
        last_value = None
        tie_count = 0
        for i, item in enumerate(valid_channels):
            channel_index = item['index']
            current_value = item['value']
            if current_value != last_value:
                current_rank += (tie_count + 1)
                tie_count = 0
            else:
                tie_count += 1
            ranked_data[channel_index][rank_key] = current_rank
            last_value = current_value

    print("DEBUG Analyzer Ranker: Rank calculation finished.") # Отладка
    return ranked_data