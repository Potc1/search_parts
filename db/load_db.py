import sqlite3
import logging


def startDB() -> bool:  
    connection = sqlite3.connect('llmForParts_database.db')
    cursor = connection.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Chats (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username VARCHAR(40) NOT NULL, 
                   chat_name VARCHAR(40) NOT NULL,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   )
                   
                   """)
    
    connection.commit()
    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS Messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    username VARCHAR(40),
                    role VARCHAR(40),
                    message TEXT,
                    FOREIGN KEY (chat_id) REFERENCES Chats(id))
    """)
    cursor.close()
    connection.close()
    return True 

def FetchChatList(username: str) -> dict:
    connection = sqlite3.connect('llmForParts_database.db')
    cursor = connection.cursor()
    result = ""
    try:
        cursor.execute(f"""
        SELECT * FROM Chats
        WHERE username = ?;
                       """, (username,))
        result = cursor.fetchall()
    except Exception as e:
        cursor.close()
        print(f"fail while fetching list of chats is {e} {result}")
        connection.close()
        return {"status": f"fail while fetching list of chats", "error": e, "result": ""}
    
    cursor.close()
    connection.close()
    return {"status": "Ok", "result": result}


def CreateChat(chatName, username) -> dict:
    connection = sqlite3.connect('llmForParts_database.db')
    cursor = connection.cursor()
    chatId = ""
    try:
        cursor.execute("""
        INSERT INTO Chats (username, chat_name) VALUES(?, ?) RETURNING id;
                    """,  (username, chatName,))
        chatId = cursor.fetchall()[0]
        chatId = chatId[0]
        print(chatId)
    except Exception as e:
        cursor.close()
        connection.close()
        print(f"fail while creating new chat is {e}")
        return {"description": "fail while creating new chat ", "error": e, "result": -1}
    connection.commit()
    cursor.close()
    connection.close()
    return {"status": "Ok", "result": chatId}

def FetchFromChat(chatId: int) -> dict:
    connection = sqlite3.connect('llmForParts_database.db')
    cursor = connection.cursor()
    try:
        cursor.execute(f"""
        SELECT * FROM Messages WHERE chat_id = ?;
                       """, (chatId,))
        result = cursor.fetchall()
    except Exception as e:
        cursor.close()
        connection.close()
        return {"status": f"fail while fetching from chat {chatId}", "error": e, "result": []}
    
    cursor.close()
    connection.close()
    return {"status": "Ok", "result": result}

def InsertToChat(chatId: int, username: str, message: str, role: str) -> dict:
    connection = sqlite3.connect('llmForParts_database.db')
    cursor = connection.cursor()
    try:
        cursor.execute(f"""
        INSERT INTO Messages (chat_id, username, role,  message) 
        VALUES (?, ?, ?, ?)
                       """,  (chatId, username, role, message))
    except Exception as e:
        cursor.close()
        connection.close()
        return {"status": f"fail while inserting to chat {chatId}", "error": e}
    
    connection.commit()
    cursor.close()
    connection.close()
    return {"status": "Ok", "result": ""}

def Leave():
    #connection.close();
    return True

def deleteALL():
    connection = sqlite3.connect('llmForParts_database.db')
    cursor = connection.cursor()

    cursor.execute("""
                   SELECT id FROM Chats
                   ORDER BY id DESC
                   LIMIT 1 
                   """)
    res = cursor.fetchone()[0]
    cursor.execute("""SELECT * FROM Chats""")
    print(cursor.fetchall())
    
    print(res)
    for i in range(1, res+1):
        try:
            cursor.execute(f"""
                        SELECT * FROM ChatNumber_{i} 
                            """)
        except Exception as e:
            print(f"Error occupted {e}")
            continue
        w = cursor.fetchall()
        #cursor.execute(f"Drop table IF EXISTS ChatNumber_{i}")
        print(w)
    #cursor.execute("DELETE FROM  Chats")
    connection.commit()
    cursor.execute("SELECT * FROM chats WHERE username = 'vagiz'")
    print('vagiz chats')
    print(cursor.fetchall())
    cursor.close()
    connection.close()


###
# ======================================================================
# Начало другой базы
###
def startCulturesDB() -> bool:  
    connection = sqlite3.connect('culturesPrices.db')
    cursor = connection.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS WheatPrices (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   city VARCHAR(40) NOT NULL,
                   company VARCHAR(100) NOT NULL,
                   price DECIMAL(10, 2) NOT NULL,
                   specs TEXT,
                   date TEXT,
                   companyInfo TEXT
                   )
                   
                   """)
    connection.commit()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS BarleyPrices (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   city VARCHAR(40) NOT NULL,
                   company VARCHAR(100) NOT NULL,
                   price DECIMAL(10, 2) NOT NULL,
                   specs TEXT,
                   date TEXT,
                   companyInfo TEXT
                   )
                   
                   """)
    connection.commit()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS SunflowerPrices (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   city VARCHAR(40) NOT NULL,
                   company VARCHAR(100) NOT NULL,
                   price DECIMAL(10, 2) NOT NULL,
                   specs TEXT,
                   date TEXT,
                   companyInfo TEXT
                   )
                   
                   """)
    connection.commit()
    cursor.close()
    connection.close()
    return True 

def FetchCulturePrice(tablename: str) -> dict:
    connection = sqlite3.connect('culturesPrices.db')
    cursor = connection.cursor()
    try:
        cursor.execute(f"""
                        SELECT * FROM {tablename}
                        """)
        result = cursor.fetchall()
    except Exception as e:
        return {"status": f"fail while fetching from {tablename}", "error": e, "result": []}
    cursor.close()
    connection.close()
    return {"status": "Ok", "error": None, "result": result}

def UpdateCulturesTable(tablename: str, data: list[tuple]) -> dict:
    connection = sqlite3.connect('culturesPrices.db')
    cursor = connection.cursor()
    try:
        cursor.executemany(f"""
                        UPDATE {tablename}
                        SET city = ?,
                            company = ?,
                            price = ?,
                            specs = ?,
                            date = ?,
                            companyInfo = ?
                        Where id = ?
                       """,  data)
        connection.commit()
    except Exception as e:
        connection.rollback()
        connection.close()
        return {"status": f"fail while updating {tablename}", "error": e, "result": False}
    cursor.close()
    connection.close()
    return {"status": "Ok", "error": None, "result": True}

def InsertIntoCulturesTable(tablename: str, data: list[tuple]) -> dict:
    connection = sqlite3.connect('culturesPrices.db')
    cursor = connection.cursor()
    try:
        cursor.executemany(f"""
                            INSERT INTO {tablename} (city, company, price, specs, date, companyInfo)
                            VALUES(?, ?, ?, ?, ?, ?)
                           """, data)
        connection.commit()
    except Exception as e:
        connection.rollback()
        connection.close()
        return {"status": f"fail while inserting {tablename}", "error": e, "result": False}
    cursor.close()
    connection.close()

    return {"status": f"Ok", "error": None, "result": True}

def FetchDateFromCultureTables():
    connection = sqlite3.connect('culturesPrices.db')
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT date FROM WheatPrices WHERE id = 1")
        result = cursor.fetchone()
        if len(result) < 1:
            result = "" 
        else:
            result = result[0]
    except Exception as e:
        cursor.close()
        connection.close()
        return {"status": f"fail while fetching date", "error": e, "result": ""}
    cursor.close()
    connection.close()
    return {"status": f"Ok", "error": None, "result": result}