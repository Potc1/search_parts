import pandas as pd
from modules.send_request import prices

st_accept = "text/html" # говорим веб-серверу, 
                        # что хотим получить html
# имитируем подключение через браузер Mozilla на macOS
st_useragent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15"
# формируем хеш заголовков
headers = {
    "Accept": st_accept,
    "User-Agent": st_useragent
}

def export(url: str, culture: str) -> dict:
    try:
        #wheat_prices = pd.read_csv(f'{culture}_цены.csv', delimiter=',')
        new_wheat_prices = prices(url, culture)
        #merge_wheat_prices = pd.concat([new_wheat_prices, wheat_prices])
        new_wheat_prices.to_csv(f'{culture}_цены.csv', index=False)
    except Exception as e:
        return {"status": "fail while exporting", "error": e, "result": False}
    return  {"status": "Ok", "error": None, "result": True}

def loadFile(culture: str) -> pd.DataFrame:
    try:
        prices = pd.read_csv(f'{culture}_цены.csv', delimiter=',')
    except Exception as e:
        return {"status": "fail while loading file", "error": e, "result": False}
    return  {"status": "Ok", "error": None, "result": prices}

#print(export('https://api.silkagro.ru/api/prices/calc/', 'Подсолнечник'))