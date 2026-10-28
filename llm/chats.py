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

if 'local' not in st.session_state:
    st.session_state['local'] = None
if 'zap_name' not in st.session_state:
    st.session_state['zap_name'] = ''
if 'zap_model' not in st.session_state:
    st.session_state['zap_model'] = ''
if 'zap_article' not in st.session_state:
    st.session_state['zap_article'] = ''

ADD_TO_EXPERT_ANSWER = ""

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

part_model_names = {
    "MTZ-82": "./groups/GROUPS_MTZ82.json",
    "NOVA-340": "./groups/GROUPS_NOVA340.json"
}


def AddToExpertAnswer(text: str, is_out: bool):
    """
    Кладем в глобальную переменную то, что нашли в RAG
    """
    global ADD_TO_EXPERT_ANSWER
    if is_out == False:
        ADD_TO_EXPERT_ANSWER = text

def getAddedToExpertAnswerText():
    global ADD_TO_EXPERT_ANSWER
    for i in ADD_TO_EXPERT_ANSWER:
        yield i


def PrepareAnswer(query: str, chatHistory: list[dict]):
    st.session_state['local'] = checkInternet()
    # Промпт для Цензора (Проверка релевантности и RAG)
    censor_prompt = f"""

        Инструкция: Ты — диспетчер запросов для ИИ-эксперта по подбору запасных частей для тракторной и автомобильной техники.
        Твоя задача — проанализировать запрос пользователя и определить, относится ли он к теме запчастей.

        Правила:
        1. Если запрос касается подбора деталей, технических характеристик, совместимости запчастей или поиска каталогов — запрос БЕЗОПАСЕН (is_safe: true).
        2. Если запрос полностью не связан с темой техники и запчастей (например, просят написать стих, решить задачу по математике или дать совет по кулинарии) — запрос НЕБЕЗОПАСЕН (is_safe: false). В этом случае ничего не пиши, отправь пустой ответ (answer: "").
        3. Определи, нужен ли RAG (поиск по базе знаний). RAG нужен, если запрос содержит: конкретные артикулы, названия моделей техники, требования к ГОСТам или поиск конкретных цен. Если это общий вопрос о том, как работает деталь — RAG не нужен.
        4. Если запрос содержит конкретные артикулы или названия детали, добавь артикуль/деталь в json формат ("article" ) и/или названия модели техники добавь  в json формат (model: ...)
        
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
            "name": "найденная тобою название запасной части"
            "model": "найденная тобою модель трактора"
        }}
    """

    messages = [{'role': 'user', 'content': censor_prompt}]
    client = Client()

    model_names = models['cloud']
    if not st.session_state['local']:
        model_names = models["local"]
        client = Client('http://localhost:11434/')
        print("Running in local mode")

    mini_model = model_names['mini']
    big_model = model_names['big']

    try:
        response_from_censor = client.chat(mini_model, messages=messages)
        censor_answer_text = response_from_censor['message']['content']

        
        routing_model = json.loads(censor_answer_text)
        if routing_model.get("article", "") != "":
            st.session_state['zap_article'] = routing_model.get("article", "")
        if routing_model.get("name", "") != '':
            st.session_state['zap_name'] = routing_model.get("name", "") 
        if routing_model.get("model", "") != '':
            st.session_state['zap_model'] = routing_model.get("model", "")
        print(f"Answer from censor: {censor_answer_text} и переменные сессии модель: {st.session_state['zap_model']} название: {st.session_state['zap_name']} артикуль: {st.session_state['zap_article']} ")

    except Exception as e:
        print(f"Censor error: {e}")
        routing_model = {"is_safe": True, "needs_rag": False, "answer": ""}

    if not routing_model.get('is_safe', True):
        return routing_model.get('answer', "Извините, я могу помочь только с подбором запчастей.")

    context1 = ""
    context2 = ""
    parts_group_list = ""
    # поиск по индексу (name)
    if st.session_state['zap_name'] != "" and st.session_state['zap_name'] is not None:
        context1 = IndexQueryFinder(st.session_state['zap_model'], st.session_state['zap_name'], 'name')
        pass

    # поиск по индексу (article)
    if st.session_state['zap_article'] != "" and st.session_state['zap_article'] is not None:
        context2 = IndexQueryFinder(st.session_state['zap_model'], st.session_state['zap_article'], 'article')
        pass

    group_index = ""
    try:
        if st.session_state['zap_model'] != "" and st.session_state['zap_model'] is not None:
            filename = part_model_names[st.session_state['zap_model']]
            with open(filename, "r+", encoding="utf-8") as file:
                parts_group_list = json.load(file)
        parser_prompt = f"""
             Инструкция: Ты — диспетчер запросов для ИИ-эксперта по подбору запасных частей для тракторной и автомобильной техники.
                    Твоя задача — проанализировать запрос пользователя и определить по списку групп и предложенной информации, какая
                    это группа запасных частей.
            
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
        response_from_parser = client.chat(mini_model, messages=messages_parser)
        parser_answer_text = response_from_parser['message']['content']
        group_index = parser_answer_text
        print(f"Ответ парсера групп\n{parser_answer_text} {group_index}")
    except Exception as e:
        print(f"Group parser error: {e}")


    print("Поиск по индексам")
    print(context1)
    print(context2)

    context_for_compare = []
    # Логика RAG (заглушка, так как поиск еще не реализован)

    context3 = []
    ### Массив для семантики с условием
    #part_group = ""
    if group_index != "":
        print("поиск с условием")
        context3 = ConditionSearch(st.session_state['zap_model'], st.session_state['zap_model'], group_index)
    if routing_model.get('needs_rag') != "" and (not context2):
        # Здесь в будущем будет вызов векторной базы
        context_for_compare = QueryFinder(st.session_state['zap_name'], st.session_state['zap_model'])
        #part_group = raw_context['text'] + f"Модель: {raw_context['metadata']['Модель']}\n Подгруппа деталей: {raw_context['metadata']['Подгруппа']}"
        
        
    context_for_compare[0].append(context1[0])
    context_for_compare[1].append(context1[1])

    context_for_compare[1].append(context3[1])
    context_for_compare[0].append(context3[0])

    # Промпт для основного Эксперта
    expert_prompt = f"""
        Роль: Ты — ведущий эксперт по подбору запасных частей для тракторов и сельскохозяйственной техники.
        Твоя цель: помогать пользователям точно находить нужные детали, проверять совместимость и давать технические рекомендации.
        По запросу пользователя ты должен найти подходящую деталь самостоятельно и сравнить с подходящей 
        
        Правила:
        1. Опирайся на предоставленный контекст, если он есть.
        2. Если ты не уверен в совместимости детали, обязательно предупреди пользователя об этом.
        3. Не выдумывай несуществующие артикулы.
        4. Ответ обязан быть структурированным, вначале выбранная тобою наиболее подходящая деталь, далее 
           совместимость, после рекомендации

        Контекст из базы знаний:
        <CONTEXT_START>
            {context_for_compare[0]}
        <CONTEXT_END>
        Верни ответ в формате json, без md пометок об этом:
        {{
            "index": номер, найденной модели, отсчет с нуля,
            "article": найденный артикуль,
            "answer": совместимость->рекомендации
        }}
        Запрос пользователя {query}
    """

    print(f"Модель используется локально: {st.session_state['local']}")
    try:
        if not st.session_state['local']:
            client_qwen = OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')
        else:
            client_qwen = OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')

        chat_history_copy = chatHistory.copy()
        # Заменяем последний запрос на расширенный промпт эксперта
        chat_history_ = [{"role": "user", "content": expert_prompt}]

        response = client_qwen.chat.completions.create(
            model=big_model,
            messages=chat_history_,
            stream=False
        )
        print(response.choices[0].message.content)
        expert_answer = json.loads(response.choices[0].message.content) 
        
    except Exception as e:
        print(f"Expert model error: {e}")
        return f"Произошла ошибка при генерации ответа: {e}"
    
    raw_content = '';

    if expert_answer.get("index", False) != False:
        AddToExpertAnswer(context_for_compare[1][int(expert_answer['index'])], False)
        raw_content = expert_answer['answer']
    raw_content = f"""Сделай вывод о подходит ли запасная часть к технике: |{st.session_state['zap_model']}|\n
                      и запросу пользователя: {query}\n 
                      На основании этого:\n
                    """ + raw_content
    messages = [{"role": "user", "content": raw_content}]
    response_from_censor = client.chat(mini_model, messages=messages)
    print(context_for_compare)
    return response_from_censor['message']['content']

def concat_streams(query: str, chatHistory: list[dict]):
    yield from PrepareAnswer(query, chatHistory)
    yield from getAddedToExpertAnswerText()