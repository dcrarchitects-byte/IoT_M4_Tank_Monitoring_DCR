from machine import Pin, PWM, ADC
import time

pot = ADC(26)
servo = PWM(Pin(15))
servo.freq(50)
MIN_DUTY = 1638
MAX_DUTY = 8192

while True:
    raw = pot.read_u16()
    duty = MIN_DUTY + (raw * (MAX_DUTY - MIN_DUTY) // 65535)
    servo.duty_u16(duty)
    print("Potentiometer:", raw, "| Servo angle:", raw * 180 // 65535)
    time.sleep_ms(100)
