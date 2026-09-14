from machine import Pin
import time

# Module 4 guided project: Blink external LED
# LED connected to GP15 through a 330-ohm resistor.
led = Pin(15, Pin.OUT)

while True:
    led.toggle()
    print("External LED:", "ON" if led.value() else "OFF")
    time.sleep(1)
