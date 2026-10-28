import json
import time
import os
from dotenv import load_dotenv
import streamlit as st
from ollama import chat, ChatResponse, Client
from openai import OpenAI
from qdrant.findInQdrant import QueryFinder, IndexQueryFinder, ConditionSearch

load_dotenv()

from modules.check_internet import checkInternet

# ------------------------------------------------------------
# Инициализация состояния Streamlit
# ------------------------------------------------------------
if 'local' not in st.session_state:
    st.session_state['local'] = None
if 'zap_name' not in st.session_state:
    st.session_state['zap_name'] = ''
if 'zap_model' not in st.session_state:
    st.session_state['zap_model'] = ''
if 'zap_article' not in st.session_state:
    st.session_state['zap_article'] = ''

# ------------------------------------------------------------
# Глобальная переменная‑буфер для ответа эксперта
# ------------------------------------------------------------
ADD_TO_EXPERT_ANSWER = ""

# ------------------------------------------------------------
# Модели (локальные и облачные)
# ------------------------------------------------------------
models = {
    "local": {
        "mini": 'gemma4:e4b',
        "big": 'gemma4:e4b'
    },
    "cloud": {
        "mini": 'gemma4:31b-cloud',
        "big": 'gpt-oss:120b-cloud'
    }
}

# ------------------------------------------------------------
# Список файлов с группами запчастей
# ------------------------------------------------------------
part_model_names = {
    "MTZ-82": "./groups/GROUPS_MTZ82.json",
    "NOVA-340": "./groups/GROUPS_NOVA340.json"
}

# ------------------------------------------------------------
# Вспомогательные функции для буфера ответа
# ------------------------------------------------------------
def AddToExpertAnswer(text: str, is_out: bool):
    """Заполняет глобальный буфер `ADD_TO_EXPERT_ANSWER`.
    Если `is_out` == False – сохраняем полученный текст.
    """
    global ADD_TO_EXPERT_ANSWER
    if not is_out:
        ADD_TO_EXPERT_ANSWER = text

def getAddedToExpertAnswerText():
    """Генератор, отдающий содержимое буфера построчно."""
    global ADD_TO_EXPERT_ANSWER
    for i in ADD_TO_EXPERT_ANSWER:
        yield i

# ------------------------------------------------------------
# Внутренние помощники (все функции работают только внутри этого файла)
# ------------------------------------------------------------

def _run_censor(query: str, client: Client, mini_model: str) -> dict:
    """Запускает мини‑модель‑цензор и возвращает `routing_model`.
    Обновляет `st.session_state['zap_*']` при наличии данных.
    """
    censor_prompt = f"""
        Инструкция: Ты — диспетчер запросов для ИИ-эксперта по подбору запасных частей для тракторной и автомобильной техники.
        Твоя задача — проанализировать запрос пользователя и определить, относится ли он к теме запчастей.

        Правила:
        1. Если запрос касается подбора деталей, технических характеристик, совместимости запчастей или поиска каталогов — запрос БЕЗОПАСЕН (is_safe: true).
        2. Если запрос полностью не связан с темой техники и запчастей (например, стих, задача по математике, совет по кулинарии) — запрос НЕБЕЗОПАСЕН (is_safe: false). В этом случае ничего не пиши, отправь пустой ответ (answer: "").
        3. Определи, нужен ли RAG (поиск по базе знаний). RAG нужен, если запрос содержит: конкретные артикулы, названия моделей техники, требования к ГОСТам или поиск конкретных цен. Если это общий вопрос о том, как работает деталь — RAG не нужен.
        4. Если запрос содержит конкретные артикулы или названия детали, добавь артикуль/деталь в json формат ("article") и/или названия модели техники добавь в json формат (model: ...)

        Названия моделей перечислены снизу:
        Модели мтз-80 и мтз-82 = MTZ-82
        {{
            "models": ["MTZ-82", "NOVA-340"]
        }}

        Запрос: {query}

        Верни ТОЛЬКО JSON в формате, без markdown пометок об этом:
        {{
            "is_safe": true/false,
            "answer": "текст ответа если is_safe=false, иначе пустая строка",
            "needs_rag": true/false,
            "article": "найденнный тобою артикуль",
            "name": "найденная тобою название запасной части",
            "model": "найденная тобою модель трактора"
        }}
    """
    messages = [{'role': 'user', 'content': censor_prompt}]
    try:
        response = client.chat(mini_model, messages=messages)
        censor_answer_text = response['message']['content']
        routing_model = json.loads(censor_answer_text)
        # Обновляем session_state, если пришли данные
        if routing_model.get("article"):
            st.session_state['zap_article'] = routing_model["article"]
        if routing_model.get("name"):
            st.session_state['zap_name'] = routing_model["name"]
        if routing_model.get("model"):
            st.session_state['zap_model'] = routing_model["model"]
        print(f"Answer from censor: {censor_answer_text} и переменные сессии модель: {st.session_state['zap_model']} название: {st.session_state['zap_name']} артикуль: {st.session_state['zap_article']}")
    except Exception as e:
        print(f"Censor error: {e}")
        routing_model = {"is_safe": True, "needs_rag": False, "answer": ""}
    return routing_model


def _search_by_index() -> tuple:
    """Ищет детали по имени и артикулу в Qdrant‑индексе.
    Возвращает кортеж (context1, context2).
    """
    context1 = ""
    context2 = ""
    # Поиск по индексу (name)
    if st.session_state['zap_name']:
        context1 = IndexQueryFinder(st.session_state['zap_model'], st.session_state['zap_name'], 'name')
    # Поиск по индексу (article)
    if st.session_state['zap_article']:
        context2 = IndexQueryFinder(st.session_state['zap_model'], st.session_state['zap_article'], 'article')
    return context1, context2


def _load_parts_group(model_name: str):
    """Читает JSON‑файл с группами запчастей для указанной модели.
    Возвращает список/структуру, либо пустой объект при ошибке.
    """
    if not model_name:
        return []
    filename = part_model_names.get(model_name)
    if not filename:
        return []
    try:
        with open(filename, "r+", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading parts group file {filename}: {e}")
        return []


def _parse_group(routing_model: dict, parts_group_list, client: Client, mini_model: str) -> str:
    """Определяет группу запчастей с помощью мини‑модели‑парсера.
    Возвращает строку `group_index` (пустая строка при ошибке).
    """
    parser_prompt = f"""
        Инструкция: Ты — диспетчер запросов для ИИ-эксперта по подбору запасных частей для тракторной и автомобильной техники.
        Твоя задача — проанализировать запрос пользователя и определить по списку групп и предложенной информации, какая это группа запасных частей.

        Правила:
        1. Ни в коем случае нельзя ВЫДУМЫВАТЬ группы
        2. Выбирать группы необходимо из предложенного списка
        3. Верни только ту группу, которая наиболее соответствует предоставленной информации
        4. Если ничего не нашлос, верни пустую строку

        <CONTEXT_START>
            Учитывая  информацию о запросе:
            {routing_model}
            Выбери из списка групп наиболее подходящую:
            {parts_group_list}
        <CONTEXT_END>
    """
    messages_parser = [{'role': 'user', 'content': parser_prompt}]
    try:
        response = client.chat(mini_model, messages=messages_parser)
        parser_answer_text = response['message']['content']
        print(f"Ответ парсера групп\n{parser_answer_text}")
        return parser_answer_text
    except Exception as e:
        print(f"Group parser error: {e}")
        return ""


def _build_context_for_compare(routing_model: dict, context1, context2, group_index: str):
    """Формирует список `context_for_compare`, который будет передан в экспертный промпт.
    Логика максимально приближена к оригинальному коду.
    """
    # Если нужен RAG (и нет контекста по артикулу) – получаем контекст из векторного поиска
    context_for_compare = []
    if routing_model.get('needs_rag') and not context2:
        # Вызов векторного поиска – возвращает список списков
        context_for_compare = QueryFinder(st.session_state['zap_name'], st.session_state['zap_model'])
    # Поиск с условием (группа)
    context3 = []
    if group_index:
        print("поиск с условием")
        context3 = ConditionSearch(st.session_state['zap_model'], st.session_state['zap_model'], group_index)
    # Добавляем найденные куски в первый подсписок (если он существует)
    if isinstance(context_for_compare, list) and len(context_for_compare) > 0:
        # context1 и context2 – могут быть либо пустой строкой, либо списком из двух элементов
        if isinstance(context1, (list, tuple)) and len(context1) >= 2:
            context_for_compare[0].append(context1[0])
            context_for_compare[0].append(context1[1])
        if isinstance(context3, (list, tuple)) and len(context3) > 0:
            context_for_compare[0].append(context3[0])
    return context_for_compare


def _build_expert_prompt(query: str, context_for_compare) -> str:
    """Собирает окончательный промпт для большой модели‑эксперта."""
    expert_prompt = f"""
        Роль: Ты — ведущий эксперт по подбору запасных частей для тракторов и сельскохозяйственной техники.
        Твоя цель: помогать пользователям точно находить нужные детали, проверять совместимость и давать технические рекомендации.
        По запросу пользователя ты должен найти подходящую деталь самостоятельно и сравнить с подходящей

        Правила:
        1. Опирайся на предоставленный контекст, если он есть.
        2. Если ты не уверен в совместимости детали, обязательно предупреди пользователя об этом.
        3. Не выдумывай несуществующие артикулы.
        4. Ответ обязан быть структурированным, вначале выбранная тобою наиболее подходящая деталь, далее совместимость, после рекомендации

        Контекст из базы знаний:
        <CONTEXT_START>
            {context_for_compare}
        <CONTEXT_END>

        Запрос пользователя {query}
    """
    return expert_prompt


def _call_expert_model(chatHistory: list[dict], expert_prompt: str, big_model: str, local_flag: bool):
    """Отправляет запрос большой модели и возвращает потоковый ответ."""
    try:
        if not local_flag:
            client_qwen = OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')
        else:
            client_qwen = OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')
        chat_history_copy = chatHistory.copy()
        # заменяем последний запрос на наш расширенный экспертный промпт
        chat_history_copy[-1] = {"role": "user", "content": expert_prompt}
        response = client_qwen.chat.completions.create(
            model=big_model,
            messages=chat_history_copy,
            stream=True
        )
        return response
    except Exception as e:
        print(f"Expert model error: {e}")
        return f"Произошла ошибка при генерации ответа: {e}"

# ------------------------------------------------------------
# Основная функция, которая вызывается из UI
# ------------------------------------------------------------
def PrepareAnswer(query: str, chatHistory: list[dict]):
    """Точка входа – получает запрос пользователя, собирает весь контекст и возвращает ответ модели."""
    st.session_state['local'] = checkInternet()
    # Выбор клиента и модели в зависимости от наличия интернета
    client = Client()
    model_names = models['cloud']
    if not st.session_state['local']:
        model_names = models["local"]
        client = Client('http://localhost:11434/')
        print("Running in local mode")
    mini_model = model_names['mini']
    big_model = model_names['big']

    # 1. Цензор
    routing_model = _run_censor(query, client, mini_model)
    if not routing_model.get('is_safe', True):
        return routing_model.get('answer', "Извините, я могу помочь только с подбором запчастей.")

    # 2. Поиск по индексам
    context1, context2 = _search_by_index()

    # 3. Загрузка списка групп и определение группы
    parts_group_list = _load_parts_group(st.session_state['zap_model'])
    group_index = _parse_group(routing_model, parts_group_list, client, mini_model)

    # 4. Формирование контекста для сравнения
    context_for_compare = _build_context_for_compare(routing_model, context1, context2, group_index)

    # 5. Формирование экспертного промпта
    expert_prompt = _build_expert_prompt(query, context_for_compare)

    # 6. Запрос к большой модели
    response = _call_expert_model(chatHistory, expert_prompt, big_model, st.session_state['local'])
    return response

# ------------------------------------------------------------
# Функция-генератор, объединяющая ответ модели и буфер эксперта
# ------------------------------------------------------------
def concat_streams(query: str, chatHistory: list[dict]):
    yield from PrepareAnswer(query, chatHistory)
    yield from getAddedToExpertAnswerText()
