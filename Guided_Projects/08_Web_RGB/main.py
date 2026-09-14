import network
import socket
import time
from machine import Pin

WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""
MQTT_HOST = "broker.emqx.io"
MQTT_PORT = 1883
BASE_TOPIC = "dcr/iot-m4-tank-2026/project8"
STATE_TOPIC = BASE_TOPIC + "/state"
COMMAND_TOPIC = BASE_TOPIC + "/rgb/set"

red = Pin(13, Pin.OUT, value=0)
green = Pin(14, Pin.OUT, value=0)
blue = Pin(15, Pin.OUT, value=0)
current_color = "OFF"

def enc_len(value):
    out = bytearray()
    while True:
        digit = value % 128
        value //= 128
        if value:
            digit |= 0x80
        out.append(digit)
        if not value:
            return bytes(out)

def mqtt_str(value):
    data = value.encode() if isinstance(value, str) else value
    return bytes((len(data) >> 8, len(data) & 0xFF)) + data

class SimpleMQTT:
    def __init__(self, host, port, client_id):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.sock = None
        self.packet_id = 1

    def _send_all(self, data):
        sent = 0
        while sent < len(data):
            n = self.sock.send(data[sent:])
            if not n:
                raise OSError("MQTT send failed")
            sent += n

    def _read_exact(self, count):
        data = b""
        while len(data) < count:
            chunk = self.sock.recv(count - len(data))
            if not chunk:
                raise OSError("MQTT connection closed")
            data += chunk
        return data

    def _read_remaining_length(self):
        multiplier = 1
        value = 0
        while True:
            digit = self._read_exact(1)[0]
            value += (digit & 127) * multiplier
            if (digit & 128) == 0:
                return value
            multiplier *= 128
            if multiplier > 128 * 128 * 128:
                raise OSError("Invalid MQTT packet")

    def connect(self):
        addr = socket.getaddrinfo(self.host, self.port)[0][-1]
        self.sock = socket.socket()
        self.sock.settimeout(5)
        self.sock.connect(addr)
        vh = mqtt_str("MQTT") + bytes((4, 2, 0, 30))
        payload = mqtt_str(self.client_id)
        packet = bytes((0x10,)) + enc_len(len(vh) + len(payload)) + vh + payload
        self._send_all(packet)
        if self._read_exact(4) != b"\x20\x02\x00\x00":
            raise OSError("MQTT connection rejected")
        self.sock.settimeout(0.05)

    def subscribe(self, topic):
        self.packet_id = (self.packet_id % 65535) + 1
        payload = mqtt_str(topic) + b"\x00"
        body = bytes((self.packet_id >> 8, self.packet_id & 0xFF)) + payload
        self._send_all(bytes((0x82,)) + enc_len(len(body)) + body)

    def publish(self, topic, payload, retain=False):
        body = mqtt_str(topic) + (payload.encode() if isinstance(payload, str) else payload)
        header = 0x31 if retain else 0x30
        self._send_all(bytes((header,)) + enc_len(len(body)) + body)

    def poll(self):
        try:
            first = self.sock.recv(1)
            if not first:
                raise OSError("MQTT connection closed")
        except OSError:
            return None, None
        packet_type = first[0] >> 4
        remaining = self._read_remaining_length()
        body = self._read_exact(remaining)
        if packet_type == 3:
            topic_len = (body[0] << 8) | body[1]
            topic = body[2:2 + topic_len].decode()
            payload = body[2 + topic_len:]
            return topic, payload
        return None, None

    def close(self):
        try:
            self.sock.close()
        except:
            pass

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        print("Connecting to Wi-Fi", end="")
        for _ in range(60):
            if wlan.isconnected():
                break
            print(".", end="")
            time.sleep(0.25)
    if not wlan.isconnected():
        raise OSError("Wi-Fi connection failed")
    print("\nWi-Fi connected:", wlan.ifconfig()[0])

def set_color(name):
    global current_color
    name = name.upper()
    values = {
        "RED": (1, 0, 0),
        "GREEN": (0, 1, 0),
        "BLUE": (0, 0, 1),
        "OFF": (0, 0, 0),
    }
    r, g, b = values.get(name, values["OFF"])
    red.value(r)
    green.value(g)
    blue.value(b)
    current_color = name if name in values else "OFF"
    print("RGB:", current_color)

def connect_mqtt():
    client_id = "dcr-p8-" + str(time.ticks_ms() & 0xFFFF)
    mqtt = SimpleMQTT(MQTT_HOST, MQTT_PORT, client_id)
    mqtt.connect()
    mqtt.subscribe(COMMAND_TOPIC)
    print("MQTT connected:", MQTT_HOST)
    print("State topic:", STATE_TOPIC)
    print("Command topic:", COMMAND_TOPIC)
    mqtt.publish(STATE_TOPIC, current_color, retain=True)
    return mqtt

connect_wifi()
set_color("OFF")
mqtt = None
last_heartbeat = time.ticks_ms()

while True:
    try:
        if mqtt is None:
            mqtt = connect_mqtt()
            last_heartbeat = time.ticks_ms()

        topic, payload = mqtt.poll()
        if topic == COMMAND_TOPIC:
            set_color(payload.decode().strip())
            mqtt.publish(STATE_TOPIC, current_color, retain=True)

        if time.ticks_diff(time.ticks_ms(), last_heartbeat) >= 10000:
            last_heartbeat = time.ticks_ms()
            mqtt.publish(STATE_TOPIC, current_color, retain=True)

        time.sleep_ms(50)

    except Exception as exc:
        print("Connection error:", exc)
        if mqtt is not None:
            mqtt.close()
        mqtt = None
        time.sleep(2)
