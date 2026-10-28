import requests
import time
from dateutil import parser
import pandas as pd
from datetime import date
from bs4 import BeautifulSoup
import streamlit as st

from db.load_db import FetchCulturePrice
from db.load_db import InsertIntoCulturesTable
from db.load_db import UpdateCulturesTable
from db.load_db import FetchDateFromCultureTables

st_accept = "text/html" # говорим веб-серверу, 
                        # что хотим получить html
# имитируем подключение через браузер Mozilla на macOS
st_useragent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15"
# формируем хеш заголовков
headers = {
    "Accept": st_accept,
    "User-Agent": st_useragent
}

CultureTables = {
    'Пшеница': "WheatPrices",
    'Ячмень': "BarleyPrices",
    'Подсолнечник':"SunflowerPrices"
}


MAX_RETRY_ATTEMPTS = 5
RETRY_DELAY_SECONDS = 1
REQUEST_TIMEOUT_SECONDS = 30

def try_request(url, headers):
        attemp = 1
        while attemp < MAX_RETRY_ATTEMPTS:
            try:
                response = requests.get(url, headers)
                if response.status_code != 200:
                    attemp += 1
                    time.sleep(1)
                    continue
                return response
            except ConnectionError as e:
                print(f'Error {e}')
                attemp += 1
                time.sleep(RETRY_DELAY_SECONDS)
        return ""

def CompareDates() -> dict:
    today = date.today()

    result = FetchDateFromCultureTables()

    dateDB = result["result"] 
    if result['result'] == "":
         return {"status": "fail", "error": result['error'], "result": dateDB}
    dateDB = convert(dateDB)
    formatted_today = today.strftime("%Y-%m-%d")

    formatted_date = dateDB.strftime("%Y-%m-%d")

    return {"status": "Ok", "error": None, "result": formatted_today == formatted_date}


def convert(date_time):
    datetime_str = parser.parse(date_time)

    return datetime_str

@st.cache_data
def tariff(url: str, arg: str) -> pd.DataFrame:
        requests.packages.urllib3.disable_warnings()
        response = requests.get(f'{url}{arg}.xml', headers=headers, verify=False)
        tariff_xml = response.text
        tariff_attr = BeautifulSoup(tariff_xml, 'xml')
        tariff_data = [frag.text for frag in tariff_attr.find_all('para')]
        #tariff_data = tariff_data[3:-2]
        #print(tariff_data)
        if len(tariff_data) == 0:
            return pd.DataFrame()
        tariff_df = pd.DataFrame(columns=tariff_data[1:4], data={tariff_data[1]: [tariff_data[6], tariff_data[9], tariff_data[12]], tariff_data[2]: [tariff_data[7], tariff_data[10], tariff_data[13]], tariff_data[3]: [tariff_data[8], tariff_data[11], tariff_data[14]]})
        return tariff_df

def prices(url, params) -> pd.DataFrame:
        culture_url = url + f'?culture={params}&basis=CPT'
        culture_response = try_request(culture_url, headers)
        culture_df = pd.DataFrame(columns=['Город', 'Компания', 'Цена', 'Требования', 'О компании'])
        cityes = []
        addresses = []
        companysName = []
        specs = []
        inns = []
        prices = []
        dates = []
        for data in culture_response.json():
            #print(data)
            for elem in data.get("data", {}):
                #elem = json.loads(sentence)
                
                cityes.append(elem.get("warehouseObj", "").get("city", ""))
                addresses.append(elem.get("warehouseObj", "").get("address", ""))
                companysName.append(elem.get("company", "Company name not found"))
                inn = f"https://saby.ru/profile/{elem.get("companyInn", "7736050003")}"
                inns.append(inn)
                prices.append(elem.get("price", "price not found"))
                specs.append(elem.get("specs", "specs not found"))
                date = convert(elem.get("dateTime", "2000-01-01T15:07:28.473843"))
                dates.append(date)
               
        culture_df = pd.DataFrame(columns=['Город', 'Компания', 'Цена', 'Требования', 'Дата', 'О компании'], data=
                                {'Город': cityes, 'Компания': companysName, 'Цена': prices, 'Требования': specs, 'Дата': dates, 'О компании': inns})

        index = 0

        return culture_df

def pricesFromDb(params: str) -> pd.DataFrame:
    tableName = CultureTables[params]
    culture_df = pd.DataFrame(columns=['Город', 'Компания', 'Цена', 'Требования', 'Дата', 'О компании'])

    result = FetchCulturePrice(tablename=tableName)

    if result['status'] != 'Ok':
         return culture_df
    
    cityes = []
    addresses = []
    companysName = []
    specs = []
    inns = []
    prices = []
    dates = []    
    for sentence in result['result']:
        cityes.append(sentence[1])
        companysName.append(sentence[2])
        prices.append(int(sentence[3]))
        specs.append(sentence[4])
        dates.append(sentence[5])
        inns.append(sentence[6])
    culture_df = pd.DataFrame(columns=['Город', 'Компания', 'Цена', 'Требования', 'Дата', 'О компании'], data=
                                {'Город': cityes, 'Компания': companysName, 'Цена': prices, 'Требования': specs, 'Дата': dates, 'О компании': inns})

    index = 0

    return culture_df


def UpdateInsertCulturesDB(url: str, culture: str, updating: bool):
    tableName = CultureTables[culture]

    data = PrepareDataForCultureTables(url, culture, updating=updating)

    if updating == True:
        res = UpdateCulturesTable(tableName, data)
    else:
        res = InsertIntoCulturesTable(tableName, data)
    return res

def PrepareDataForCultureTables(url: str, params: str, updating: bool) -> list[tuple]:
        culture_url = url + f'?culture={params}&basis=CPT'
        culture_response = try_request(culture_url, headers)


        dataForUpdating = []

        for data in culture_response.json():
            #print(data)
            for i, elem in enumerate(data.get("data", {})):
                #elem = json.loads(sentence)
                
                city = elem.get("warehouseObj", "").get("city", "")
                #address = elem.get("warehouseObj", "").get("address", "")
                companysName = elem.get("company", "Company name not found")
                inn = f"https://saby.ru/profile/{elem.get("companyInn", "7736050003")}"
                price = elem.get("price", "price not found")
                spec = elem.get("specs", "specs not found")
                date = convert(elem.get("dateTime", "2000-01-01T15:07:28.473843"))
                if updating == True:
                    dataForUpdating.append((city, companysName, price, spec, date, inn, i))
                else:
                    dataForUpdating.append((city, companysName, price, spec, date, inn))
        return dataForUpdating

