# Final Project - Tank Monitoring and Filling System

This folder contains the Module 4 final IoT prototype for **IoT Masters**.

## Functions

- DHT22 temperature and relative-humidity acquisition.
- HC-SR04 distance acquisition to simulate tank liquid-level detection.
- RGB LED temperature indication: blue below 20 C, green from 20 through 30 C, and red above 30 C.
- Red tank-warning LED when `distance < 10 cm`.
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

## Electrical implementation considerations

The HC-SR04 ECHO signal is 5 V on the physical device, so a hardware implementation should protect the Pico W input with a suitable voltage divider or level shifter. A real water pump requires an external driver or relay stage and must not be powered directly from a GPIO pin.

## Tank-level calibration

The implemented warning threshold is `distance < 10 cm`, following the project requirement. In a real tank installation, the relationship between ultrasonic distance and liquid level should be calibrated to the tank geometry before converting the reading into a level percentage.
