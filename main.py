import asyncio
import json
import os
import threading
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

import paho.mqtt.client as mqtt
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates


MQTT_BROKER = os.getenv("HOST_MOSQUITTO", "mosquitto")
MQTT_PORT = int(os.getenv("PORT_MOSQUITTO", "1883"))
STATIONS = ("s1", "s2", "s3", "s4", "s5")
TEMPLATES = Jinja2Templates(directory=Path(__file__).parent / "templates")


def empty_station(station_id: str) -> dict[str, Any]:
    return {
        "asset_id": station_id,
        "status": "unknown",
        "power_consumption": 0,
        "cycle_time": None,
        "timestamp": None,
    }


state: dict[str, Any] = {
    "stations": {station_id: empty_station(station_id) for station_id in STATIONS},
    "latest_item": 0,
    "last_message": None,
    "mqtt_connected": False,
    "history": deque(maxlen=32),
}
state_lock = threading.Lock()
subscriber_queues: set[asyncio.Queue[str]] = set()
subscriber_lock = threading.Lock()
mqtt_client: mqtt.Client | None = None
event_loop: asyncio.AbstractEventLoop | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def snapshot() -> dict[str, Any]:
    with state_lock:
        return {
            "stations": list(state["stations"].values()),
            "latest_item": state["latest_item"],
            "last_message": state["last_message"],
            "mqtt_connected": state["mqtt_connected"],
            "history": list(state["history"]),
        }


def broadcast(payload: dict[str, Any]) -> None:
    if event_loop is None:
        return
    message = json.dumps(payload)
    with subscriber_lock:
        queues = tuple(subscriber_queues)
    for queue in queues:
        event_loop.call_soon_threadsafe(queue.put_nowait, message)


def on_connect(client: mqtt.Client, userdata: Any, flags: dict[str, Any], rc: int, properties: Any = None) -> None:
    connected = rc == 0
    with state_lock:
        state["mqtt_connected"] = connected
    if connected:
        client.subscribe("factory/stations/#")
        client.subscribe("factory/items")
    broadcast({"type": "connection", "connected": connected, "data": snapshot()})


def on_disconnect(client: mqtt.Client, userdata: Any, disconnect_flags: Any, rc: Any, properties: Any = None) -> None:
    with state_lock:
        state["mqtt_connected"] = False
    broadcast({"type": "connection", "connected": False, "data": snapshot()})


def on_message(client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
    try:
        payload = json.loads(message.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return

    received_at = utc_now()
    event_type = "station" if message.topic.startswith("factory/stations/") else "item"
    with state_lock:
        if event_type == "station":
            station_id = payload.get("asset_id") or message.topic.rsplit("/", 1)[-1]
            if station_id not in state["stations"]:
                return
            current = {**state["stations"][station_id], **payload, "received_at": received_at}
            state["stations"][station_id] = current
            state["history"].append({"type": "station", "station": station_id, "status": current.get("status"), "at": received_at})
        else:
            state["latest_item"] = payload.get("count", state["latest_item"])
            state["history"].append({"type": "item", "count": state["latest_item"], "at": received_at})
        state["last_message"] = received_at

    broadcast({"type": event_type, "data": snapshot()})


def start_mqtt() -> mqtt.Client:
    client = mqtt.Client(client_id="factory-dashboard", protocol=mqtt.MQTTv5)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()
    return client


def stop_mqtt() -> None:
    if mqtt_client is not None:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_loop, mqtt_client
    event_loop = asyncio.get_running_loop()
    mqtt_client = start_mqtt()
    yield
    stop_mqtt()


app = FastAPI(title="Factory Pulse", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request=request, name="index.html")


@app.get("/api/state")
async def api_state() -> dict[str, Any]:
    return snapshot()


async def event_stream() -> AsyncGenerator[str, None]:
    queue: asyncio.Queue[str] = asyncio.Queue()
    with subscriber_lock:
        subscriber_queues.add(queue)
    try:
        yield f"data: {json.dumps({'type': 'snapshot', 'data': snapshot()})}\n\n"
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=15)
                yield f"data: {message}\n\n"
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
    finally:
        with subscriber_lock:
            subscriber_queues.discard(queue)


@app.get("/events")
async def events() -> StreamingResponse:
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})