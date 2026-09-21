# ============================================================
# GREENHOUSE ENVIRONMENTAL MONITOR
# Raspberry Pi Pico W + BME280 + RGB LED + Blynk Cloud
# David Castillo Ramirez - IoT Module 5
# ============================================================

from machine import Pin, I2C
import network
import socket
import time
import ujson

WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""

# Paste the device token only in the private working copy.
BLYNK_AUTH_TOKEN = "YOUR_BLYNK_AUTH_TOKEN"
BLYNK_HOST = "ny3.blynk.cloud"
BLYNK_PORT = 1883

DS_TEMPERATURE = "Temperature"
DS_HUMIDITY = "Humidity"
DS_PRESSURE = "Air Pressure"
DS_ALERT = "Alert Level"

SAMPLE_INTERVAL_MS = 5000
RECONNECT_INTERVAL_MS = 5000

# BME280 custom Wokwi chip: SDA -> GP2, SCL -> GP3
i2c = I2C(1, sda=Pin(2), scl=Pin(3), freq=100000)
BME280_ADDRESS = 0x76
REG_CHIP_ID = 0xD0
REG_PRESSURE = 0xF7
REG_TEMPERATURE = 0xFA
REG_HUMIDITY = 0xFD

# Common-cathode RGB LED
red_led = Pin(13, Pin.OUT, value=0)
green_led = Pin(14, Pin.OUT, value=0)
blue_led = Pin(15, Pin.OUT, value=0)

NORMAL = 0
SUSPICIOUS = 1
ALERT = 2

STATUS_NAMES = {
    NORMAL: "NORMAL",
    SUSPICIOUS: "SUSPICIOUS",
    ALERT: "ALERT",
}

pressure_baseline = None


def set_rgb(status):
    if status == NORMAL:
        red_led.off()
        green_led.on()
        blue_led.off()
    elif status == SUSPICIOUS:
        red_led.on()
        green_led.on()
        blue_led.off()
    else:
        red_led.on()
        green_led.off()
        blue_led.off()


def temperature_status(temp):
    if 18.0 <= temp <= 28.0:
        return NORMAL
    if 15.0 <= temp < 18.0 or 28.0 < temp <= 32.0:
        return SUSPICIOUS
    return ALERT


def humidity_status(humidity):
    if 50.0 <= humidity <= 70.0:
        return NORMAL
    if 40.0 <= humidity < 50.0 or 70.0 < humidity <= 80.0:
        return SUSPICIOUS
    return ALERT


def pressure_status(pressure, baseline):
    deviation = abs(pressure - baseline)
    if deviation <= 8.0:
        return NORMAL
    if deviation <= 15.0:
        return SUSPICIOUS
    return ALERT


def read_register(register):
    i2c.writeto(BME280_ADDRESS, bytes([register]))
    return i2c.readfrom(BME280_ADDRESS, 1)[0]


def read_environment():
    temperature = float(read_register(REG_TEMPERATURE))
    humidity = float(read_register(REG_HUMIDITY))
    pressure = float(read_register(REG_PRESSURE) * 4)
    return temperature, humidity, pressure


def connect_wifi(wlan):
    if wlan.isconnected():
        return True

    try:
        wlan.active(True)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        start = time.ticks_ms()
        print("Connecting to Wi-Fi", end="")
        while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), start) < 15000:
            print(".", end="")
            time.sleep_ms(250)
        print()
    except Exception as exc:
        print("Wi-Fi connection error:", exc)

    if wlan.isconnected():
        print("Wi-Fi connected:", wlan.ifconfig()[0])
        return True

    print("Wi-Fi unavailable; local monitoring remains active.")
    return False


def mqtt_string(value):
    if isinstance(value, str):
        value = value.encode()
    return bytes([len(value) >> 8, len(value) & 0xFF]) + value


def encode_remaining_length(length):
    output = bytearray()
    while True:
        digit = length % 128
        length //= 128
        if length > 0:
            digit |= 0x80
        output.append(digit)
        if length == 0:
            break
    return bytes(output)


class BlynkMQTT:
    def __init__(self, host, port, token):
        self.host = host
        self.port = port
        self.token = token
        self.sock = None

    def send_all(self, data):
        sent = 0
        while sent < len(data):
            count = self.sock.send(data[sent:])
            if not count:
                raise OSError("MQTT send failed")
            sent += count

    def connect(self):
        address = socket.getaddrinfo(self.host, self.port)[0][-1]
        self.sock = socket.socket()
        self.sock.settimeout(10)
        self.sock.connect(address)

        variable_header = (
            mqtt_string("MQTT")
            + bytes([4])
            + bytes([0xC2])
            + bytes([0x00, 0x2D])
        )

        client_id = "greenhouse-pico-" + str(time.ticks_ms() & 0xFFFF)
        payload = (
            mqtt_string(client_id)
            + mqtt_string("device")
            + mqtt_string(self.token)
        )

        packet = (
            bytes([0x10])
            + encode_remaining_length(len(variable_header) + len(payload))
            + variable_header
            + payload
        )

        self.send_all(packet)
        response = self.sock.recv(4)

        if len(response) < 4 or response[3] != 0:
            code = response[3] if len(response) >= 4 else -1
            raise OSError("Blynk MQTT connection rejected: " + str(code))

        print("Blynk Cloud connected.")

    def publish(self, topic, payload):
        if isinstance(payload, str):
            payload = payload.encode()

        body = mqtt_string(topic) + payload
        packet = bytes([0x30]) + encode_remaining_length(len(body)) + body
        self.send_all(packet)

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None


def send_to_blynk(client, temperature, humidity, pressure, alert_level):
    payload = ujson.dumps({
        DS_TEMPERATURE: round(temperature, 1),
        DS_HUMIDITY: round(humidity, 1),
        DS_PRESSURE: round(pressure, 1),
        DS_ALERT: alert_level,
    })

    client.publish("batch_ds", payload)
    print("Blynk update:", payload)


print("GREENHOUSE ENVIRONMENTAL MONITOR")
print("================================")

try:
    chip_id = read_register(REG_CHIP_ID)
    print("BME280 Chip ID:", hex(chip_id))
except Exception as exc:
    print("BME280 startup error:", exc)

wlan = network.WLAN(network.STA_IF)
connect_wifi(wlan)

blynk = None
last_sample = time.ticks_add(time.ticks_ms(), -SAMPLE_INTERVAL_MS)
last_reconnect = time.ticks_add(time.ticks_ms(), -RECONNECT_INTERVAL_MS)

while True:
    now = time.ticks_ms()

    # Local sensing is independent of cloud availability.
    if time.ticks_diff(now, last_sample) >= SAMPLE_INTERVAL_MS:
        last_sample = now

        try:
            temperature, humidity, pressure = read_environment()

            if pressure_baseline is None:
                pressure_baseline = pressure
                print("Pressure baseline:", round(pressure_baseline, 1), "hPa")

            temp_level = temperature_status(temperature)
            humidity_level = humidity_status(humidity)
            pressure_level = pressure_status(pressure, pressure_baseline)
            overall_status = max(temp_level, humidity_level, pressure_level)

            set_rgb(overall_status)

            print("--------------------------------")
            print("Temperature:", round(temperature, 1), "C")
            print("Humidity:", round(humidity, 1), "%")
            print("Pressure:", round(pressure, 1), "hPa")
            print("Temperature status:", STATUS_NAMES[temp_level])
            print("Humidity status:", STATUS_NAMES[humidity_level])
            print("Pressure status:", STATUS_NAMES[pressure_level])
            print("OVERALL STATUS:", STATUS_NAMES[overall_status])

            if blynk is not None:
                try:
                    send_to_blynk(
                        blynk,
                        temperature,
                        humidity,
                        pressure,
                        overall_status,
                    )
                except Exception as exc:
                    print("Blynk publish error:", exc)
                    blynk.close()
                    blynk = None

        except Exception as exc:
            set_rgb(ALERT)
            print("BME280 SENSOR ERROR:", exc)
            print("OVERALL STATUS: ALERT")

    # Reconnect network/cloud without interrupting local monitoring.
    if time.ticks_diff(now, last_reconnect) >= RECONNECT_INTERVAL_MS:
        last_reconnect = now

        if not wlan.isconnected():
            connect_wifi(wlan)
            if blynk is not None:
                blynk.close()
                blynk = None

        if wlan.isconnected() and blynk is None and BLYNK_AUTH_TOKEN != "YOUR_BLYNK_AUTH_TOKEN":
            try:
                blynk = BlynkMQTT(BLYNK_HOST, BLYNK_PORT, BLYNK_AUTH_TOKEN)
                blynk.connect()
            except Exception as exc:
                print("Blynk connection error:", exc)
                if blynk is not None:
                    blynk.close()
                blynk = None

    time.sleep_ms(100)
