# Final Project - Tank Monitoring and Filling System

This folder contains the Module 4 final IoT prototype for **IoT Masters**.

## Functions

- DHT22 temperature and relative-humidity acquisition.
- HC-SR04 distance acquisition to simulate tank liquid-level detection.
- RGB LED temperature indication: blue below 20 C, green from 20 through 30 C, and red above 30 C.
- Red tank-warning LED when the assignment-defined condition `distance < 10 cm` is true.
- Yellow pump-simulation LED controlled manually from the web dashboard.
- Embedded HTTP server with `/`, `/data`, `/pump/on`, and `/pump/off` routes.
- Browser data refresh every 5 seconds.
- DHT22 validation, ultrasonic timeout handling, and Wi-Fi/server recovery logic.

## Pin allocation

| Device | Signal | Pico W pin |
|---|---|---|
| DHT22 | DATA/SDA | GP2 |
| HC-SR04 | TRIG | GP3 |
| HC-SR04 | ECHO | GP4 |
| RGB LED | Red | GP13 |
| RGB LED | Green | GP14 |
| RGB LED | Blue | GP15 |
| Tank warning LED | Anode via 220 ohm | GP16 |
| Pump indicator LED | Anode via 220 ohm | GP17 |

The DHT22 data line includes a 10 kOhm pull-up to 3.3 V. RGB and indicator LED channels use 220 ohm current-limiting resistors.

## Physical-hardware note

This course submission is prepared as a **virtual functional prototype** because a physical Pico W is not currently available. In physical hardware, protect the Pico W input from the HC-SR04 5 V ECHO signal with a level shifter or resistor divider. A real water pump must never be powered directly from a GPIO.

## Geometry note

The assignment explicitly requests the red warning LED when **distance is less than 10 cm**, and the code implements that rule. In a conventional top-mounted ultrasonic tank sensor, smaller measured distance normally corresponds to a higher liquid level, so a production installation should calibrate tank geometry before translating distance into liquid level.
