import streamlit as st
from llm.chats import PrepareAnswer, concat_streams
from db.load_db import FetchFromChat
from db.load_db import InsertToChat
from db.load_db import startDB
from ui.sidebar import render_sidebar

from server.main import get_current_user

st.set_page_config(
    page_title="ИИ",
    page_icon="🤖",
)

if 'token' not in st.session_state:
    st.switch_page("./app.py")
elif st.session_state['token'] == None:
    st.switch_page("./app.py")    




def show_chat():

    print(st.session_state['picked_chat'])
    messages = FetchFromChat(st.session_state['picked_chat'])['result']

    if len(messages) > 0:
        st.session_state.messages = []
        for message in messages:
            st.session_state['messages'].append({"role": message[3], "content": message[4]})
    else:
        st.session_state['messages'] = []
    st.title("LLM Модель")

    SUGGESTIONS = {
        ":blue[:material/local_library:] Линейка двигателей Nova": (
            "Объясни, какие двигателя стоят в комбайне Nova 340"
        ),
        ":green[:material/database:] Как поменять подшипник?": (
            "Развернутый план-инструкция 'Замена подшипника соломотряса на Nova 340' по шагам"
        ),
        ":orange[:material/multiline_chart:] Йоу": (
            "Выдай ссылку на RickRoll"
        ),
    }

    @st.dialog("Legal disclaimer")
    def show_disclaimer_dialog():
        st.caption("""
                Гиптоеза №1.
            """)
        
    has_message_history = (
        "messages" in st.session_state and len(st.session_state.messages) > 0
    )

    clicked_suggestion = (
        "selected_suggestion" in st.session_state and st.session_state.selected_suggestion
    )
    user_init_questions = (
        "initial_question" in st.session_state and st.session_state.initial_question
    )

    user_first_interaction = (
        user_init_questions or clicked_suggestion
    )
    if not has_message_history and not user_first_interaction:
        st.session_state.messages = []

        with st.container():
            st.chat_input("Ask a question...", key="initial_question")

            selected_suggestion = st.pills(
                label="Examples",
                label_visibility="collapsed",
                options=SUGGESTIONS.keys(),
                key="selected_suggestion",
            )

        st.button(
            "&nbsp;:small[:gray[:material/balance: Legal disclaimer]]",
            type="tertiary",
            on_click=show_disclaimer_dialog,
        )

        st.stop()



    promt = st.chat_input("Что?")

    if not promt:
        if clicked_suggestion:
            print("нажали подсказку", st.session_state.selected_suggestion)
            promt = SUGGESTIONS[st.session_state.selected_suggestion]
        if user_init_questions:
            promt = st.session_state.initial_question
        st.session_state.messages.append({"role": "user", "content": promt})

    ### Вывод всех прошлых сообщений
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                st.container()
            st.markdown(message["content"])

    if promt:   
        with st.chat_message("user"):
            if user_first_interaction:
                pass
            st.markdown(promt)
            st.session_state.messages.append({"role": "user", "content": promt})
            InsertToChat(st.session_state['picked_chat'], st.session_state['user'],  promt, "user")
        with st.chat_message("assistant"):
            chatHistory = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            #print(chatHistory)
            with st.spinner("Размышляю..."):
                stream = concat_streams(promt, chatHistory)
                try:
                    not_stream = False
                    response = st.write_stream(stream)
                except Exception as e:
                    print(f"Error occupted {e}")
                    not_stream = True
                    temp_res = stream
                    response = st.markdown(stream)
        st.session_state.messages.append({"role": "assistant", "content": response if not_stream == False else temp_res})
        print(InsertToChat(st.session_state['picked_chat'], st.session_state['user'], st.session_state.messages[-1]['content'], "assistant"))

render_sidebar()
show_chat()

