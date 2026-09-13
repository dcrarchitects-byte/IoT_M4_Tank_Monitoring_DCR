from machine import Pin
import time

red = Pin(13, Pin.OUT)
yellow = Pin(14, Pin.OUT)
green = Pin(15, Pin.OUT)

def set_lights(r, y, g):
    red.value(r); yellow.value(y); green.value(g)

while True:
    set_lights(0, 0, 1); print("GREEN"); time.sleep(4)
    set_lights(0, 1, 0); print("YELLOW"); time.sleep(1)
    set_lights(1, 0, 0); print("RED"); time.sleep(4)
