import mysql.connector
import os
from mqtt import client
import db

HOST_DATABASE = os.getenv("HOST_DATABASE", "db")
USER = os.getenv("USER_DATABASE")
PASSWORD = os.getenv("PASSWORD_DATABASE")

HOST_MOSQUITTO = os.getenv("HOST_MOSQUITTO", "mosquitto")
PORT_MOSQUITTO = int(os.getenv("PORT_MOSQUITTO", 1883))

def main():
    try:
        mydb = mysql.connector.connect(
            host=HOST_DATABASE,
            user=USER,
            password=PASSWORD
        )
    except Exception as e:
        print(f"Error while connecting: {e}")
    else:
        cursor = mydb.cursor()
        print("CONEXÃO FEITA")

    try: 
        client.connect(HOST_MOSQUITTO, PORT_MOSQUITTO, 60)
        client.loop_forever()
    except Exception as e:
        print(f"Error with mqtt: {e}")
    


if __name__ == "__main__":
    main()