from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct, Document
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
'''
qdrant_client = QdrantClient(
    url="https://f12887d0-a392-4885-9acd-87c6e77aa7fe.us-east4-0.gcp.cloud.qdrant.io:6333", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6NTE5ODEwMWMtODBkOS00ZDg1LThkYWEtYWI0NWY3ZDgyZjcyIn0.jWurNS56At_7GSi7KzC73eZMxl69J9tED0V27Rz1cL4",
    cloud_inference=True
)

'''

load_dotenv()

'''
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"), 
    api_key=os.getenv("QDRANT_KEY"),
)
'''
qdrant_client = QdrantClient(
    url="http://localhost:6333"
)

COLLECTION = "MTZ-82"
#print(qdrant_client.get_collections())

#query_text = "Нужен мотор гидравлический"
model = SentenceTransformer("ai-forever/ru-en-RoSBERTa")
def QueryFinder(query: str, collection: str) -> list:
    """
    Ищет запрос в векторной БД
    
    ### Returns: list
    Возвращает массив массивов, где 0:
    {part, name, article, group}
    а 1: список деталей в группе
    """
    query_vector = model.encode(query)
    # search for similar menu items
    results = qdrant_client.query_points(
        collection_name=collection,
        query=query_vector,
        with_payload=True,
        limit=3
    )
    #res = [i for i in results]
    #print(res[0][1].payload)
    #print(res[0].payload)
    # print results
    res = []
    payload = ""
    parts = []
    groups = []
    print("\n🔍 Топ-3 результата:")
    for point in results.points:
        part = {
            "part": point.payload['part'],
            "name": point.payload['name'],
            "article": point.payload['article'],
            "group": point.payload['metadata']['Подгруппа'],
            "score": point.score
        }
        text = point.payload['text']
        parts.append(part)
        groups.append(text)
        print(f"Это найдено в векторной БД score: {point.score} деталь: {point.payload['part']}")
    res.append(parts)
    res.append(groups)
    return res
    # 1. Если это ScoredPoint
    '''
        if hasattr(point, 'payload'):
            payload = point.payload or {}
        # 2. Если это кортеж вида (id, score, payload) или (score, payload)
        elif isinstance(point, (tuple, list)):
            payload = point[0] if len(point) >= 1 else {}
        else:
            payload = {"text": "", "Part": "Ничего не найдено"}
        #return payload
    return payload
    '''

def IndexQueryFinder(collection: str , query: str, field: str):
    """
    Функция для поиска по индексу field (name, article)

    ### Returns

    Возвращает результат поиска по индекcу(field)
    в формате массива [{part, name, article, group}, "список деталей группы"]
    """
    #query_vector = model.encode(query if query else query_text)
    res = qdrant_client.scroll(
        collection,
        scroll_filter=models.Filter(
            must = [
                models.FieldCondition(
                key=field,
                match=models.MatchPhrase(phrase=query),
                )
            ]
        )
    )
    if res[0]:
        dict = {
            "part": res[0][0].payload['part'],
            "name": res[0][0].payload['name'],
            "article": res[0][0].payload['article'],
            "group": res[0][0].payload['metadata']['Подгруппа'],
            "score": 0.8
        }
        parts_of_group = res[0][0].payload['text']
        return [dict, parts_of_group]
    return [{"part": "по запросу ничего не найдено"} ,'']


def ConditionSearch(collection: str, query: str, condition: str):
    """
    Ищет запрос (query) в коллекции (collection) по условию (condition) - подразумевается подгруппа

    ### Returns: list
    Возвращает массив массивов, где 0:
    {part, name, article, group}
    а 1: список деталей в группе
    """
    query_vector = model.encode(query)
    search_result = qdrant_client.query_points(
        collection_name = collection,
        query=query_vector,
        query_filter=models.Filter(
            must = [
                models.FieldCondition(
                key="part",
                match=models.MatchPhrase(phrase=condition),
                )
            ]
        ),
        with_payload=True,
        limit=3,
    )
    
    #print("\n🔍 Топ-3 результата:")
    res = []
    parts = []
    groups = []
    for point in search_result.points:
        part = {
            "part": point.payload['part'],
            "name": point.payload['name'],
            "article": point.payload['article'],
            "group": point.payload['metadata']['Подгруппа'],
            "score": point.score
        }
        text = point.payload['text']
        parts.append(part)
        groups.append(text)
        print(f"Это найдено в векторной БД по условию score: {point.score} деталь: {point.payload['part']}")
    res.append(parts)
    res.append(groups)
    return res
#print(QueryFinder("Мотор гидравлический", "MTZ-82"))
#print(IndexQueryFinder('ступица ', 'name'))
#print(condition_search('MTZ-82', 'ступица переднего колеса', 'Подгруппа 1101. Бак топливный (для трактора «БЕЛАРУС-82П»)'))
