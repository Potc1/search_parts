import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logging

from db.load_db import startCulturesDB
from modules.send_request import prices
from archive.archive import export

from modules.send_request import CompareDates
from modules.send_request import UpdateInsertCulturesDB
from modules.send_request import pricesFromDb
from modules.send_request import convert
from modules.send_request import tariff


from server.main import get_current_user


logging.basicConfig(
    filename='appPrice.log', 
    level=logging.DEBUG, 
    encoding='utf-8',
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def chart(name_file):
    chart_df = pd.read_csv(name_file, sep=',')
    chart_df['Дата'] = chart_df['Дата'].apply(convert)
    chart_df = chart_df.groupby(chart_df['Дата'].dt.month)['Цена'].agg(['min', 'max', 'mean'])
    return chart_df

st.set_page_config(
    page_title="Цены",
    page_icon="💰",
)

if 'token' not in st.session_state:
    st.switch_page("./app.py")
elif st.session_state['token'] == None:
    st.switch_page("./app.py")  

if 'picked_culture' not in st.session_state:
    st.session_state['picked_culture'] = ''

if 'need_update' not in st.session_state:
    st.session_state['need_update'] = False


with open('./app/urls.json', 'rb+') as file:
    URL = json.load(file)

URL_tariff = URL['URL_tariff']
URL = URL['price']
print(URL, type(URL))

startCulturesDB()

print(get_current_user(st.session_state['token']))

need_update = CompareDates()

### Если статус не Ok, значит таблицы пустые, вставляем в них значения
if need_update['status'] == "fail":
    UpdateInsertCulturesDB(URL, 'Пшеница', False)
    UpdateInsertCulturesDB(URL, 'Ячмень', False)
    UpdateInsertCulturesDB(URL, 'Подсолнечник', False)
### результат False, сменилось число, обновляем все цены в БД
elif need_update['result'] == False:
    UpdateInsertCulturesDB(URL, 'Пшеница', True)
    UpdateInsertCulturesDB(URL, 'Ячмень', True)
    UpdateInsertCulturesDB(URL, 'Подсолнечник', True)



st.header("Цены")


#st.markdown("Выберрите культуру: ")
option = st.selectbox(
    "Выберрите культуру",
    ("Пшеница", 'Ячмень', 'Подсолнечник'),
)

st.session_state['picked_culture'] = option

logging.info(f"Пользователь {st.session_state['user']} зашел на страницу 'Цены'")
logging.info(f"Пользователь {st.session_state['user']} выбрал {st.session_state['picked_culture']}")

st.markdown(f"## {st.session_state['picked_culture']}")
st.markdown("___")


df_data = pricesFromDb(st.session_state['picked_culture'])
try:
    tariffs = tariff(URL_tariff, 'zerno')
    col_prises_dollar, col_tariff = st.columns(2)
    col_prises_dollar.metric("Индикативные цены, $", tariffs['Индикативные цены, долл. США'].iloc[0], "")
    col_tariff.metric("Пошлина, ₽", tariffs.iloc[0].iloc[2], "")
except Exception as e:
    print(f"Error while getting prices {e}")
chart_df = chart(f'{st.session_state['picked_culture']}_цены.csv')
fig = go.Figure()
fig = fig.add_trace(go.Scatter(x=chart_df.index.to_list(), y=chart_df['min']))
fig.add_trace(go.Scatter(x=chart_df.index.to_list(), y=chart_df['max']))
fig.add_trace(go.Scatter(x=chart_df.index.to_list(), y=chart_df['mean']))
st.plotly_chart(fig, theme="streamlit")

st.data_editor(
    df_data,
    column_config={
        "О компании": st.column_config.LinkColumn(
            "О компании",
            display_text=r"Проверить"
        )
    },
    hide_index=True,
    )



