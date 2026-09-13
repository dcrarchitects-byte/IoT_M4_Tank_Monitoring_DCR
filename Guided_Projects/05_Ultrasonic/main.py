from machine import Pin, time_pulse_us
import time

trig = Pin(3, Pin.OUT, value=0)
echo = Pin(4, Pin.IN)

while True:
    try:
        trig.value(0); time.sleep_us(2)
        trig.value(1); time.sleep_us(10)
        trig.value(0)
        pulse = time_pulse_us(echo, 1, 30000)
        if pulse < 0:
            raise OSError("echo timeout")
        print("Distance: {:.1f} cm".format(pulse / 58.0))
    except Exception as exc:
        print("HC-SR04 error:", exc)
    time.sleep(1)
