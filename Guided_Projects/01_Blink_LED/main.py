from machine import Pin
import time

led = Pin("LED", Pin.OUT)

while True:
    led.toggle()
    print("Built-in LED:", "ON" if led.value() else "OFF")
    time.sleep(1)
