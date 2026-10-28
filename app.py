import streamlit as st
import logging
import requests
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    filename='appAuth.log',
    level=logging.DEBUG,
    encoding='utf-8',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

st.set_page_config(
    page_title="Hello!",
    page_icon="👋",
)

st.sidebar.success("Select a demo above.")

# --- КОНФИГУРАЦИЯ ---
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Hello", page_icon="", layout="wide")

# --- ИНИЦИАЛИЗАЦИЯ СЕССИИ ---
if "token" not in st.session_state:
    st.session_state.token = None

# --- ФУНКЦИИ API ---
def register_user(username, password):
    """Регистрирует пользователя через бэкенд"""
    logging.info(f"Пользователь {username} регистрируется")
    try:
        # Бэкенд принимает JSON для регистрации
        response = requests.post(
            f"{API_URL}/register", 
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            logging.info(f"Пользователь {username} успешно зарегистрироволся")
            return True, response.json().get("message", "Успешно")
        else:
            logging.error(f"Пользователь {username} не зарегистрироволся")
            return False, response.json().get("detail", "Ошибка регистрации")
    except Exception as e:
        return False, f"Ошибка соединения: {e}"

def login_user(username, password):
    """Логинится и возвращает токен"""
    logging.info(f"Авторизация пользователя {username}")
    try:
        # Бэкенд принимает form-data для логина (OAuth2)
        response = requests.post(
            f"{API_URL}/login", 
            data={"username": username, "password": password}
        )
        if response.status_code == 200:
            if 'user' not in st.session_state:
                st.session_state['user'] = username
            st.session_state['user'] = username
            logging.info(f"Авторизация пользователя {username} завершена")
            return True, response.json()["access_token"]
        else:
            logging.error(f"Авторизация пользователя {username} завершилась провалом")
            return False, response.json().get("detail", "Ошибка входа")
    except Exception as e:
        return False, f"Ошибка соединения: {e}"

# --- ГЛАВНАЯ ЛОГИКА ---

# 1. ЭКРАН АВТОРИЗАЦИИ И РЕГИСТРАЦИИ
if st.session_state.token is None:
    st.title(" ПО")
    st.markdown("Войдите в систему или создайте новый аккаунт")
    
    # Создаем вкладки
    tab_login, tab_register = st.tabs(["Вход", "Регистрация"])
    
    # --- ВКЛАДКА ВХОДА ---
    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Логин", key="login_user")
            password = st.text_input("Пароль", type="password", key="login_pass")
            submitted = st.form_submit_button("Войти", use_container_width=True)
            
            if submitted:
                success, result = login_user(username, password)
                if success:
                    st.session_state.token = result
                    st.success("Успешный вход!")
                    st.rerun()
                else:
                    st.error(result)

    # --- ВКЛАДКА РЕГИСТРАЦИИ ---
    with tab_register:
        with st.form("register_form"):
            username = st.text_input("Придумайте логин", key="reg_user")
            password = st.text_input("Придумайте пароль", type="password", key="reg_pass")
            confirm_password = st.text_input("Повторите пароль", type="password", key="reg_pass_conf")
            
            submitted = st.form_submit_button("Зарегистрироваться", use_container_width=True)
            
            if submitted:
                # Валидация на фронтенде
                if not username or not password:
                    st.error("Заполните все поля")
                elif password != confirm_password:
                    st.error("Пароли не совпадают!")
                else:
                    success, message = register_user(username, password)
                    if success:
                        st.success(f"{message}. Выполняем автоматический вход...")
                        # Автоматически логиним пользователя после регистрации
                        login_success, token = login_user(username, password)
                        if login_success:
                            st.session_state.token = token
                            st.rerun()
                    else:
                        st.error(message)

# 2. ЭКРАН ЧАТА (ЕСЛИ АВТОРИЗОВАН)
else:
    if st.sidebar.button("🚪 Выйти"):
        st.session_state.token = None
        st.session_state.messages = []
        st.session_state['picked_chat'] = -1
        st.rerun()

    st.sidebar.title(" Профиль")
    # Чтобы узнать имя пользователя, можно декодировать JWT, но для простоты покажем заглушку

    st.sidebar.success(f"Добро пожаловать {st.session_state['user']}")
    


