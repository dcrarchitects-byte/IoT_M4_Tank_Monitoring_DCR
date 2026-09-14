import network
import socket
import time
import dht
from machine import Pin, time_pulse_us

WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""
MQTT_HOST = "broker.emqx.io"
MQTT_PORT = 1883
BASE_TOPIC = "dcr/iot-m4-tank-2026/final"
DATA_TOPIC = BASE_TOPIC + "/data"
PUMP_COMMAND_TOPIC = BASE_TOPIC + "/pump/set"

DHT_PIN = 2
TRIG_PIN = 3
ECHO_PIN = 4
RGB_R_PIN = 13
RGB_G_PIN = 14
RGB_B_PIN = 15
TANK_ALERT_PIN = 16
PUMP_LED_PIN = 17

COLD_LIMIT_C = 20.0
HOT_LIMIT_C = 30.0
TANK_WARNING_DISTANCE_CM = 10.0
SAMPLE_INTERVAL_MS = 5000

dht_sensor = dht.DHT22(Pin(DHT_PIN))
trig = Pin(TRIG_PIN, Pin.OUT, value=0)
echo = Pin(ECHO_PIN, Pin.IN)
rgb_r = Pin(RGB_R_PIN, Pin.OUT, value=0)
rgb_g = Pin(RGB_G_PIN, Pin.OUT, value=0)
rgb_b = Pin(RGB_B_PIN, Pin.OUT, value=0)
tank_alert_led = Pin(TANK_ALERT_PIN, Pin.OUT, value=0)
pump_led = Pin(PUMP_LED_PIN, Pin.OUT, value=0)

temperature_c = None
humidity_rh = None
distance_cm = None
rgb_status = "UNKNOWN"
tank_status = "UNKNOWN"
pump_on = False
sensor_fault = "None"

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

def set_rgb(r, g, b):
    rgb_r.value(1 if r else 0)
    rgb_g.value(1 if g else 0)
    rgb_b.value(1 if b else 0)

def classify_temperature(temp):
    global rgb_status
    if temp is None:
        set_rgb(0, 0, 0)
        rgb_status = "SENSOR ERROR"
    elif temp < COLD_LIMIT_C:
        set_rgb(0, 0, 1)
        rgb_status = "COLD - BLUE"
    elif temp <= HOT_LIMIT_C:
        set_rgb(0, 1, 0)
        rgb_status = "MODERATE - GREEN"
    else:
        set_rgb(1, 0, 0)
        rgb_status = "HOT - RED"

def read_dht22():
    try:
        dht_sensor.measure()
        temp = float(dht_sensor.temperature())
        hum = float(dht_sensor.humidity())
        if temp < -40 or temp > 80:
            raise ValueError("temperature outside DHT22 range")
        if hum < 0 or hum > 100:
            raise ValueError("humidity outside 0-100% range")
        return temp, hum, None
    except Exception as exc:
        return None, None, "DHT22: {}".format(exc)

def read_distance_cm():
    try:
        trig.value(0)
        time.sleep_us(2)
        trig.value(1)
        time.sleep_us(10)
        trig.value(0)
        pulse = time_pulse_us(echo, 1, 30000)
        if pulse < 0:
            raise OSError("echo timeout")
        dist = pulse / 58.0
        if dist < 2 or dist > 400:
            raise ValueError("distance outside 2-400 cm range")
        return round(dist, 1), None
    except Exception as exc:
        return None, "HC-SR04: {}".format(exc)

def update_tank_warning(distance):
    global tank_status
    if distance is None:
        tank_alert_led.off()
        tank_status = "SENSOR ERROR"
    elif distance < TANK_WARNING_DISTANCE_CM:
        tank_alert_led.on()
        tank_status = "NEAR EMPTY - WARNING"
    else:
        tank_alert_led.off()
        tank_status = "NORMAL"

def set_pump(state):
    global pump_on
    pump_on = bool(state)
    pump_led.value(1 if pump_on else 0)
    print("Pump:", "ON" if pump_on else "OFF")

def sample_sensors():
    global temperature_c, humidity_rh, distance_cm, sensor_fault
    temp, hum, dht_error = read_dht22()
    dist, distance_error = read_distance_cm()
    temperature_c = temp
    humidity_rh = hum
    distance_cm = dist
    classify_temperature(temp)
    update_tank_warning(dist)
    faults = [x for x in (dht_error, distance_error) if x]
    sensor_fault = " | ".join(faults) if faults else "None"
    print(
        "Temperature:", temperature_c, "C | Humidity:", humidity_rh,
        "% | Distance:", distance_cm, "cm | RGB:", rgb_status,
        "| Tank:", tank_status, "| Pump:", "ON" if pump_on else "OFF"
    )

def json_value(value):
    return "null" if value is None else str(round(value, 1))

def data_json():
    safe_fault = sensor_fault.replace('"', "'")
    return (
        '{"temperature":%s,"humidity":%s,"distance":%s,'
        '"rgb_status":"%s","tank_status":"%s","tank_alert":%s,'
        '"pump_on":%s,"fault":"%s"}'
        % (
            json_value(temperature_c),
            json_value(humidity_rh),
            json_value(distance_cm),
            rgb_status,
            tank_status,
            "true" if tank_alert_led.value() else "false",
            "true" if pump_on else "false",
            safe_fault,
        )
    )

def connect_mqtt():
    client_id = "dcr-final-" + str(time.ticks_ms() & 0xFFFF)
    mqtt = SimpleMQTT(MQTT_HOST, MQTT_PORT, client_id)
    mqtt.connect()
    mqtt.subscribe(PUMP_COMMAND_TOPIC)
    print("MQTT connected:", MQTT_HOST)
    print("Data topic:", DATA_TOPIC)
    print("Pump command topic:", PUMP_COMMAND_TOPIC)
    return mqtt

print("IoT Masters - Tank Monitoring and Filling System")
set_rgb(0, 0, 0)
set_pump(False)
connect_wifi()

mqtt = None
last_sample = time.ticks_add(time.ticks_ms(), -SAMPLE_INTERVAL_MS)

while True:
    try:
        if mqtt is None:
            mqtt = connect_mqtt()
            last_sample = time.ticks_add(time.ticks_ms(), -SAMPLE_INTERVAL_MS)

        topic, payload = mqtt.poll()
        if topic == PUMP_COMMAND_TOPIC:
            command = payload.decode().strip().upper()
            if command == "ON":
                set_pump(True)
            elif command == "OFF":
                set_pump(False)
            mqtt.publish(DATA_TOPIC, data_json(), retain=True)

        now = time.ticks_ms()
        if time.ticks_diff(now, last_sample) >= SAMPLE_INTERVAL_MS:
            last_sample = now
            sample_sensors()
            mqtt.publish(DATA_TOPIC, data_json(), retain=True)

        time.sleep_ms(50)

    except Exception as exc:
        print("Connection error:", exc)
        if mqtt is not None:
            mqtt.close()
        mqtt = None
        time.sleep(2)
