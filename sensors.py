from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json
import time
import random
import threading
import paho.mqtt.client as mqtt

MQTT_BROKER = os.getenv("HOST_MOSQUITTO", "mosquitto")
MQTT_PORT = os.getenv("PORT_MOSQUITTO", 1883)
MQTT_USERNAME = ""
MQTT_PASSWORD = ""
CLIENT_ID = f"sensors-{random.randint(0, 100)}"
TOPIC_BASE = "factory/stations"
TOPIC_ITEM = "factory/items"

connected = False

CYCLE_TIME_RANGES = {
    "s1": (5, 15),
    "s2": (5, 15),
    "s3": (5, 15),
    "s4": (5, 15),
    "s5": (5, 15)
}

STATIONS = ["s1", "s2", "s3", "s4", "s5"]

MAX_CONCURRENT_ITEMS = 3
ITEM_LAUNCH_INTERVAL = [20, 30]

station_locks = {station: threading.Lock() for station in STATIONS}

def on_connect(client, userdata, flags, rc, properties=None):
    global connected
    if rc == 0:
        print(f"Connected to the Broker MQTT: {MQTT_BROKER} (ClientID: {CLIENT_ID})")
        connected = True
    else:
        print(f"Fail to connect, rc: {rc}")
        connected = False

def on_disconnect(client, userdata, rc, properties=None):
    global connected
    print("Disconnected")
    connected = False

def publish_event(client, station_id, status, cycle_time):
    if status == "working":
        # Approximate consumption in seconds of 700W/h e 1100W/h (700 / 60 / 60 = 0.19, same for 1100)
        power_consumption = random.uniform(0.19, 0.30) * cycle_time
    else:
        # Approximate consumption in seconds of 100W/h, just to keep the machine functioning
        power_consumption = 0.03 #* time_idle

    data = {
        'asset_id': station_id,
        'status': status,
        'power_consumption': round(power_consumption, 5),
        'timestamp': datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat()
    }

    if status == "idle":
        data['cycle_time'] = 999.9
    elif cycle_time is not None:
        data['cycle_time'] = round(cycle_time, 2)


    topic = f"{TOPIC_BASE}/{station_id}"
    payload = json.dumps(data)
    result = client.publish(topic, payload)
    pub_status = result[0]

    if pub_status == 0:
        print(f"[{station_id}] -> {status}" + f" (cycle: {cycle_time:.2f})" if cycle_time else "")
    else:
        print(f"[{station_id}] Error when publishing")

def publish_item(client, count):
    data = {
        'count': count,
        'timestamp': datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat()
    }

    payload = json.dumps(data)
    result = client.publish(TOPIC_ITEM, payload)
    status = result[0]

    if status == 0:
        print(f"Published in {TOPIC_ITEM}: count: {count}")
    else:
        print(f"Failed to publish in {TOPIC_ITEM}")

def process_item(client, item_number):
    for station_id in STATIONS:
        with station_locks[station_id]:
            while not connected:
                time.sleep(1)

            min_time, max_time = CYCLE_TIME_RANGES[station_id]
            cycle_time = random.uniform(min_time, max_time)

            publish_event(client, station_id, "working", cycle_time)

            sleep_start = time.time()

            while (time.time() - sleep_start) < cycle_time:
                if not connected:
                    time.sleep(1)
                time.sleep(0.5)

            publish_event(client, station_id, "idle", None)

    print(f"<<< Item #{item_number} left the line")

def run_simulation():
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv5)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    try:
        client.connect(MQTT_BROKER, int(MQTT_PORT), keepalive=60)
    except Exception as e:
        print(f"Error while connecting to the broker {MQTT_BROKER}: {e}")
        return

    client.loop_start()

    print("Waiting connection to the MQTT Broker...")
    timeout_counter = 0
    while not connected and timeout_counter < 30:
        time.sleep(1)
        timeout_counter += 1

    if not connected:
        print("Failed to connect after 30s. Turning off...")
        client.loop_stop()
        return

    item_counter = 1
    active_threads = []

    print("Factory is open now! Publishing 'idle' for each station.")
    for station in STATIONS:
        publish_event(client, station, "idle", None)

    time.sleep(5)

    publish_item(client, 0)

    try:
        print(f"=== MAX CONCURRENT ITEMS: {MAX_CONCURRENT_ITEMS} ===")

        time.sleep(10)
        print("Starting production...")

        while True:

            while not connected:
                print("Pausing production... Waiting MQTT connection...")
                time.sleep(2)

            active_threads = [t for t in active_threads if t.is_alive()]

            if len(active_threads) < MAX_CONCURRENT_ITEMS:
                current_item = item_counter
                item_counter += 1

                publish_item(client, current_item)

                item_thread = threading.Thread(
                    target= process_item,
                    args=(client, current_item),
                    daemon=True,
                    name=f"Item-{current_item}"
                )
                item_thread.start()
                active_threads.append(item_thread)

                print(f"Item #{current_item} in line. (Active: {len(active_threads)})\n")

                launch_interval = random.uniform(ITEM_LAUNCH_INTERVAL[0], ITEM_LAUNCH_INTERVAL[1])
                print(f"Next launch in {launch_interval:.1f}s")
                time.sleep(launch_interval)
            else:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
        print(f"Waiting {len(active_threads)} item(s) active(s) to finish...")
        for thread in active_threads:
            thread.join(timeout=5)
    finally:
        print("Factory closing...")
        client.loop_stop()
        client.disconnect()
        print("Factory closed.")