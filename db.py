# Check if the database exists 
def check_if_database_exists(cursor, db_name):
    database_found = False

    try:
        cursor.execute("SHOW DATABASES")
    except Exception as e:
        return f"Error while checking if the database exists ({e})"
    else:
        # Check the database by name
        for x in cursor:
            if x == db_name:
                database_found = True

        return database_found

def create_database(cursor, db_name):
    # Firstly it must ensure it does not exists before it creates
    database_found = check_if_database_exists(cursor= cursor, db_name= db_name)

    if type(database_found) == bool:            
        try:
            cursor.execute(f"CREATE DATABASE {db_name}") if database_found == False else "Database already exists"
        except Exception as e:
            return f"Error while creating the database ({e})"
        else:
            return f"Database {db_name} created succesfully!"
    else:
        print(database_found)

def check_if_table_exists(cursor, table_name):
    table_exists = False

    try:
        cursor.execute("SHOW TABLES")
    except Exception as e:
        return f"Error while checking tables: {e}"
    else:
        # Check the table by name
        for x in cursor:
            if x == table_name:
                table_exists = True

        return table_exists

def create_table(cursor, table_name, variables):
    table_exists = check_if_table_exists(cursor, table_name)
    command_string = f"CREATE TABLE {table_name} ({variables})"

    if type(table_exists) == bool:
        try:
            cursor.execute(command_string)
        except Exception as e:
            return f"Table {table_name} not created, error: {e}"
        else:
            return f"Table {table_name} created succesfully!"
    else:
        print(table_exists)
    