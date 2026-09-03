import paho.mqtt.client as mqtt

TOPIC = "#"

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    print(f"{msg.topic}: {msg.payload.decode()}")

client = mqtt.Client()
# client.username_pw_set("username", "password")  # If using auth
client.on_connect = on_connect
client.on_message = on_message