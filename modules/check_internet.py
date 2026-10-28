import requests
import json
import time
from modules.send_request import headers

def checkInternet() -> bool:
    """
    Проверяет интернет соединение, если интернет есть тогда true, иначе false
    """
    with open('./app/urls.json', 'rb+') as file:
        url = json.load(file)
    url = url['URL_for_internet']
    attemp = 1
    while attemp < 5:
        try:
            response = requests.get(url, headers)
            if response.status_code != 200:
                attemp += 1
                time.sleep(1)
                continue
            return True
        except Exception as e:
            print(f'Error {e}')
            attemp += 1
            time.sleep(1)
    return False

#print(checkInternet())