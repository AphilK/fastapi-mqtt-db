import mysql.connector
import os

HOST = os.getenv("HOST_DATABASE", "localhost")
USER = os.getenv("USER_DATABASE", "")
PASSWORD = os.getenv("PASSWORD_DATABASE", "")
DATABASE = os.getenv("DATABASE_NAME", "")

# Check if the database exists 
def check_if_database_exists(cursor, db_name):
    database_found = False
    cursor.execute("SHOW DATABASES")

    # Check the database by name
    for x in cursor:
        if x == db_name:
            database_found = True

    return database_found

def create_database(cursor, db_name):
    # Firstly it must ensure it does not exists before it creates
    database_found = check_if_database_exists(cursor= cursor, db_name= db_name)

    cursor.execute(f"CREATE DATABASE {db_name}") if database_found == False else "Database already exists"

def check_if_table_exists(cursor, table_name):
    table_exists = False
    cursor.execute("SHOW TABLES")

    # Check the table by name
    for x in cursor:
        if x == table_name:
            table_exists = True

    return table_exists

#TO-DO: Finish implementation
def create_table(cursor):
    table_name = input("Insert the table name: ")

try:
    mydb = mysql.connector.connect(
        host = HOST,
        user = USER,
        password = PASSWORD,
        database = DATABASE
    ) 
except:
    print("Invalid connector or database does not exist!")