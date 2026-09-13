from machine import Pin
import time

led = Pin(15, Pin.OUT)
button = Pin(14, Pin.IN, Pin.PULL_UP)

while True:
    pressed = button.value() == 0
    led.value(1 if pressed else 0)
    print("Button:", "PRESSED" if pressed else "RELEASED", "| LED:", "ON" if pressed else "OFF")
    time.sleep_ms(50)
