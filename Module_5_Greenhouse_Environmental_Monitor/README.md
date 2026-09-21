# IoT Module 5 - Environmental Monitoring and Alert System

**Student:** David Castillo Ramirez  
**Course:** Internet of Things - Computer Systems Engineering  
**Module:** 5 - Agile Implementation and Development of Solutions

This project implements a greenhouse environmental monitoring and real-time alert system with a Raspberry Pi Pico W, a BME280 environmental sensor, an RGB status indicator, Wi-Fi connectivity, and a Blynk Cloud dashboard.

## Functions

- Measures temperature, relative humidity, and barometric pressure.
- Classifies each measurement as NORMAL, SUSPICIOUS, or ALERT.
- Applies worst-case priority to determine the overall greenhouse condition.
- Drives a common-cathode RGB LED: green, yellow, or red.
- Publishes live measurements and the alert level to Blynk Cloud every 5 seconds.
- Keeps local sensing and RGB alerts active if cloud connectivity is temporarily unavailable.

## Blynk datastreams

| Virtual Pin | Datastream | Type |
|---|---|---|
| V0 | Temperature | Double |
| V1 | Humidity | Double |
| V2 | Air Pressure | Double |
| V3 | Alert Level | Enum |

Alert Level mapping: `0 = NORMAL`, `1 = SUSPICIOUS`, `2 = ALERT`.

## Alert ranges

| Variable | NORMAL | SUSPICIOUS | ALERT |
|---|---|---|---|
| Temperature | 18-28 °C | 15-17.9 °C or 28.1-32 °C | <15 °C or >32 °C |
| Humidity | 50-70% RH | 40-49% RH or 71-80% RH | <40% RH or >80% RH |
| Pressure | baseline ±8 hPa | >8 to 15 hPa from baseline | >15 hPa from baseline |

Pressure is evaluated relative to the initial local atmospheric reading so the prototype is not tied to a single altitude.

## Circuit

- BME280 SDA -> GP2
- BME280 SCL -> GP3
- BME280 VCC -> VBUS
- BME280 GND -> GND
- RGB Red -> GP13 through 220 ohms
- RGB Green -> GP14 through 220 ohms
- RGB Blue -> GP15 through 220 ohms
- RGB common cathode -> GND

## Files

- `main.py` - complete MicroPython control and Blynk communication program.
- `diagram.json` - Wokwi circuit definition.
- `greenhouse-bme280.chip.json` - interactive BME280 custom-chip controls.
- `greenhouse-bme280.chip.c` - custom-chip I2C implementation.
- `flowchart.svg` - annotated program flow diagram.
- `block_diagram.svg` - annotated system block diagram.
- `VIDEO_LINK.md` - final demonstration video index.

## Security note

The public source intentionally contains `YOUR_BLYNK_AUTH_TOKEN` instead of a live credential. The working device token belongs only in the private execution copy.
