import network
import socket
import time
import dht
from machine import Pin

WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""
MQTT_HOST = "broker.emqx.io"
MQTT_PORT = 1883
BASE_TOPIC = "dcr/iot-m4-tank-2026/project7"
STATUS_TOPIC = BASE_TOPIC + "/status"
COMMAND_TOPIC = BASE_TOPIC + "/led/set"

sensor = dht.DHT22(Pin(2))
led = Pin(15, Pin.OUT, value=0)

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
    return wlan

def read_sensor():
    sensor.measure()
    return float(sensor.temperature()), float(sensor.humidity())

def status_json(temp, hum):
    return (
        '{"temperature":%.1f,"humidity":%.1f,"led":"%s"}'
        % (temp, hum, "ON" if led.value() else "OFF")
    )

def connect_mqtt():
    client_id = "dcr-p7-" + str(time.ticks_ms() & 0xFFFF)
    mqtt = SimpleMQTT(MQTT_HOST, MQTT_PORT, client_id)
    mqtt.connect()
    mqtt.subscribe(COMMAND_TOPIC)
    print("MQTT connected:", MQTT_HOST)
    print("Status topic:", STATUS_TOPIC)
    print("Command topic:", COMMAND_TOPIC)
    return mqtt

connect_wifi()
mqtt = None
last_publish = time.ticks_add(time.ticks_ms(), -5000)
temperature = 0.0
humidity = 0.0

while True:
    try:
        if mqtt is None:
            mqtt = connect_mqtt()
            last_publish = time.ticks_add(time.ticks_ms(), -5000)

        topic, payload = mqtt.poll()
        if topic == COMMAND_TOPIC:
            command = payload.decode().strip().upper()
            if command == "ON":
                led.on()
            elif command == "OFF":
                led.off()
            print("Web command:", command, "| LED:", "ON" if led.value() else "OFF")
            mqtt.publish(STATUS_TOPIC, status_json(temperature, humidity), retain=True)

        now = time.ticks_ms()
        if time.ticks_diff(now, last_publish) >= 5000:
            last_publish = now
            try:
                temperature, humidity = read_sensor()
                message = status_json(temperature, humidity)
                mqtt.publish(STATUS_TOPIC, message, retain=True)
                print(
                    "Temperature: %.1f C | Humidity: %.1f %% | LED: %s"
                    % (temperature, humidity, "ON" if led.value() else "OFF")
                )
            except Exception as exc:
                print("DHT22 error:", exc)

        time.sleep_ms(50)

    except Exception as exc:
        print("Connection error:", exc)
        if mqtt is not None:
            mqtt.close()
        mqtt = None
        time.sleep(2)
