from db.load_db import deleteALL
from db.load_db import FetchCulturePrice
import sqlite3

def startDB() -> bool:  
    connection = sqlite3.connect('qa_temp.db')
    cursor = connection.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    body TEXT,
                    userId INTEGER
                );
                   
                   """)
    
    connection.commit()
    connection.close()

def insert_rows(data, tablename):
    connection = sqlite3.connect('qa_temp.db')
    cursor = connection.cursor()
    cursor.execute("""
        INSERT  INTO posts (id, title, body, userId)
        VALUES(1, “Лекция 1.3”, “Git + Python”, 1)
    """)

    connection.commit()
    connection.close()

#print(FetchCulturePrice('WheatPrices'))