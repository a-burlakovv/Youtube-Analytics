# YouTube Channel Analyzer

## Описание

Это консольное Python-приложение предназначено для анализа и сравнения ключевых показателей эффективности нескольких каналов YouTube. Приложение использует YouTube Data API v3 для сбора данных, сохраняет их в локальной базе данных SQLite и рассчитывает различные метрики, включая ранги каналов по этим метрикам.

## Основные возможности

*   **Сбор данных через YouTube Data API v3:**
    *   Получение основной информации о канале (название, ID плейлиста загрузок, количество подписчиков).
    *   Получение списка ID последних видео канала (с настраиваемым лимитом).
    *   Получение детальной статистики по видео (просмотры, лайки, комментарии, длительность, дата публикации) пакетами для экономии квоты API.
*   **Хранение данных:**
    *   Использование локальной базы данных SQLite (`youtube_analytics.db`) для хранения информации о каналах и их видео.
    *   Запись даты первого добавления канала (`date_added`).
    *   Обновление данных при повторном запуске.
*   **Анализ и расчет метрик:**
    *   **Базовые (общие):** Min/Max/Avg для просмотров, лайков, длительности видео по всем "наблюдаемым" видео канала в БД.
    *   **Недавние (за последние 30 дней):**
        *   Количество опубликованных видео (`videos_last_30d_count`).
        *   Средняя вовлеченность (ER = (лайки+комменты)/просмотры) для видео за 30 дней (`avg_engagement_rate`).
        *   Суммарное количество просмотров видео, опубликованных за 30 дней (`views_sum_last_30d`).
        *   Тренд просмотров (отношение просмотров видео за последние 30 дней к предыдущим 30 дням, `view_trend_ratio`).
        *   Средняя длительность видео, опубликованных за 30 дней (`avg_duration_sec_30d`).
        *   Среднее количество просмотров на одно видео, опубликованное за 30 дней (`avg_views_per_video_30d`).
    *   **Дополнительные:** Общее количество видео канала, хранящихся в БД (`observed_videos_count`), количество подписчиков (`subscriber_count`).
*   **Сравнение и ранжирование:**
    *   Обработка списка каналов из файла (`channels.txt`).
    *   Расчет ранга каждого канала по множеству метрик относительно других каналов в списке.
    *   Вывод итоговой таблицы в консоль с метриками и рангами (используется `tabulate` для форматирования, если установлен).
*   **Агрегированные показатели:**
    *   Расчет минимального, среднего и максимального значения для ключевых метрик по всей группе проанализированных каналов.
*   **Конфигурация:**
    *   Использование файла `config.ini` для гибкой настройки API ключей, имен файлов и параметров запуска.
*   **Безопасность:**
    *   Использование `.gitignore` для исключения файла конфигурации (`config.ini`), базы данных (`*.db`) и других нежелательных файлов из репозитория Git.

## Используемые технологии

*   Python 3.x
*   `google-api-python-client` (для взаимодействия с YouTube Data API)
*   `isodate` (для парсинга длительности видео ISO 8601)
*   `sqlite3` (встроенная библиотека Python для работы с SQLite)
*   `configparser` (встроенная библиотека Python для чтения INI-файлов)
*   `tabulate` (опционально, для красивого вывода таблиц в консоль)
*   `pandas` (пока не используется напрямую, но добавлен для будущих нужд UI)

## Установка

1.  **Клонируйте репозиторий:**
    ```bash
    git clone <URL вашего репозитория>
    cd <папка репозитория>
    ```
2.  **Убедитесь, что у вас установлен Python 3.x.**
3.  **Создайте виртуальное окружение (рекомендуется):**
    ```bash
    python -m venv venv
    # Активация:
    # Windows: .\venv\Scripts\activate
    # macOS/Linux: source venv/bin/activate
    ```
4.  **Установите зависимости:**
    Создайте файл `requirements.txt` со следующим содержимым:
    ```txt
    google-api-python-client
    isodate
    tabulate
    pandas
    # psycopg2-binary # Раскомментируйте, если будете использовать PostgreSQL
    # Flask # Раскомментируйте, если будете использовать Flask
    # Django # Раскомментируйте, если будете использовать Django
    ```
    Затем выполните:
    ```bash
    pip install -r requirements.txt
    ```

## Конфигурация

Перед первым запуском необходимо настроить конфигурацию:

1.  **Создайте файл `config.ini`** в корневой папке проекта, скопировав структуру из примера ниже.
2.  **Заполните API ключи:** В секции `[API]` укажите ваши YouTube Data API v3 ключи через запятую в параметре `KEYS`. **Никогда не публикуйте этот файл с вашими реальными ключами!** Файл `config.ini` уже добавлен в `.gitignore`.
    ```ini
    # config.ini

    [API]
    KEYS = YOUR_FIRST_API_KEY, YOUR_SECOND_API_KEY

    [FILES]
    DATABASE_NAME = youtube_analytics.db
    CHANNELS_FILE = channels.txt

    [SETTINGS]
    MAX_VIDEOS_TO_FETCH = 50
    FETCH_FROM_API = True
    ANALYZE_FROM_DB = True
    ```
    *   `KEYS`: Ваши API ключи через запятую.
    *   `DATABASE_NAME`: Имя файла базы данных SQLite.
    *   `CHANNELS_FILE`: Имя файла со списком ID каналов YouTube.
    *   `MAX_VIDEOS_TO_FETCH`: Максимальное кол-во видео для загрузки данных из API (<= 0 для загрузки всех).
    *   `FETCH_FROM_API`: Загружать ли свежие данные с API (`True`/`False`).
    *   `ANALYZE_FROM_DB`: Выполнять ли анализ и выводить результаты (`True`/`False`).

3.  **Создайте файл `channels.txt`** (или файл с именем, указанным в `CHANNELS_FILE` в `config.ini`). Добавьте в него ID каналов YouTube для анализа, каждый ID на новой строке.

## Использование

1.  **Активируйте виртуальное окружение** (если создавали).
2.  **Запустите скрипт из корневой папки проекта:**
    ```bash
    python main.py
    ```
3.  Скрипт выполнит шаги согласно настройкам в `config.ini` (загрузка данных из API, анализ, вывод результатов). Результаты (таблица с рангами и агрегаты по группе) будут выведены в консоль.

**Примечание:** При первом запуске будет создан файл базы данных SQLite (например, `youtube_analytics.db`). При последующих запусках с `FETCH_FROM_API = True` данные в БД будут обновляться. Если вы меняете структуру БД (например, добавляете новые поля в `database.py`), может потребоваться удалить старый файл БД перед запуском.

## Текущий статус и ограничения

*   Приложение является консольным.
*   Реализована основная логика сбора, хранения, анализа данных и ранжирования.
*   **Поддержка нескольких API ключей:** Логика для автоматического переключения ключей при исчерпании квоты **не реализована** (используется только первый ключ из списка в `config.ini`).
*   Визуализация данных отсутствует.

## Планы на будущее (Возможные)

*   Реализация поддержки нескольких API ключей с автоматическим переключением.
*   Создание веб-интерфейса (UI) с использованием Django (или Flask/Streamlit).
*   Добавление визуализации данных (графики, шкалы сравнения) в UI.
*   Реализация системы пользователей, аутентификации и прав доступа (особенно актуально для Django).
*   Внедрение асинхронных запросов к API для ускорения сбора данных.
*   Более детальное управление и мониторинг квот API.
*   Использование модуля `logging` вместо `print` для вывода сообщений.
