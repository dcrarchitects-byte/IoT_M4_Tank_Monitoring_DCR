from machine import Pin
import dht
import time

sensor = dht.DHT22(Pin(2))

while True:
    try:
        sensor.measure()
        print("Temperature: {:.1f} C | Humidity: {:.1f} %".format(sensor.temperature(), sensor.humidity()))
    except Exception as exc:
        print("DHT22 error:", exc)
    time.sleep(2)
