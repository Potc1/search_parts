import streamlit as st
import logging

from db.load_db import FetchChatList
from db.load_db import CreateChat
from db.load_db import startDB

from server.main import get_current_user

logging.basicConfig(
    filename='appChats.log', 
    level=logging.DEBUG, 
    encoding='utf-8',
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def render_sidebar():
    startDB()
    if 'user' not in st.session_state:
        st.session_state['user'] = get_current_user(st.session_state['token'])
    if 'picked_chat' not in st.session_state:
        st.session_state['picked_chat'] = -1
    if 'recently_created_chat_name' not in st.session_state:
        st.session_state['recently_created_chat_name'] = ''
    
    logging.info(f"Пользователь {st.session_state['user']} зашел на страницу 'Чаты'")
    with st.sidebar:
        render_chat_list()

def render_chat_list():
    print(f"render chats from user {st.session_state['user']}")
    result = FetchChatList(st.session_state['user'])
   
    st.session_state['chats'] = result["result"]

    text_input = st.text_input("Введите название чата")
    st.session_state['recently_created_chat_name'] = text_input 
    
    
    if st.button("➕ Новый чат"):

        print(f"This is a text form an input {st.session_state['recently_created_chat_name']}")
        if text_input:
            logging.info(f"Пользователь {st.session_state['user']} создал новый чaт {text_input}'")
            new_chat_id = CreateChat(text_input, st.session_state['user'])["result"]
            result = FetchChatList(st.session_state['user'])
            #st.write(text_input)
            st.session_state['picked_chat'] = new_chat_id
            st.session_state['chats'] = result["result"]
            print(f"Picked chat: {st.session_state['picked_chat']}\nAll_chats {st.session_state['chats']}")
        show_chat_list()
        #st.rerun()

    show_chat_list()
    
def show_chat_list():
    if st.session_state['chats'] is not None and len(st.session_state['chats']) > 0:
        #chat_names = [chat[1] for chat in st.session_state['chats']]
        chat_names = {chat[2]: chat[0] for chat in st.session_state['chats']}
        current_chat_id = st.session_state['picked_chat']

        default_index = 0

        if current_chat_id is not None:
            for i, chat in enumerate(st.session_state['chats']):
                if chat[0] == current_chat_id:
                    default_index = i
                    break
        try:
            selected_index = st.radio(
                "Выберите чат:",
                options=chat_names.keys(),
                index=default_index,
                key="chat_selector",
            )
        except st.errors.StreamlitDuplicateElementKey as e:
            print(f"Error ocupted in LLM_ui as {e}")
        st.session_state['picked_chat'] = chat_names[selected_index]
        print(f"Radio is {selected_index}, picked chat is {chat_names[selected_index]}")

#render_sidebar()