import paho.mqtt.client as mqtt
import random

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")

def on_message(client, userdata, msg):
    print(f"{msg.topic}: {msg.payload.decode()}")

client = mqtt.Client(client_id=f"subscriber-{random.randint(0, 1000)}")
# client.username_pw_set("username", "password")  # If using auth
client.on_connect = on_connect
client.on_message = on_message