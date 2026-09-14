# IoT Module 4 - Tank Monitoring and Filling System

**Student:** David Castillo Ramirez  
**Course:** Internet of Things - Computer Systems Engineering  
**Module:** 4 - Ideation for Creative Solutions

This public repository contains the source code, Wokwi circuit definitions, diagrams, dashboard preview, and evidence index for the Module 4 assignment **Tank Monitoring and Filling System**.

The guided exercises and final integrated project were developed in MicroPython and tested in Wokwi. Each project folder contains the files needed to reproduce its circuit and program.

## Assignment deliverables

- Eight guided-project source/circuit folders.
- Final integrated MicroPython prototype.
- DHT22 temperature/humidity acquisition.
- HC-SR04 distance acquisition.
- RGB LED temperature status.
- Red tank-warning LED.
- Web-controlled pump indicator LED.
- Embedded Pico W web dashboard with 5-second data refresh.
- Error handling for unavailable sensor readings and server/network recovery.
- Annotated flowchart and block diagram.
- Evidence link index.

## Repository map

```text
IoT_M4_Tank_Monitoring_DCR/
├── README.md
├── Evidence_Links.md
├── Guided_Projects/
│   ├── 01_Blink_LED/
│   ├── 02_LED_Pushbutton/
│   ├── 03_Traffic_Light/
│   ├── 04_DHT22/
│   ├── 05_Ultrasonic/
│   ├── 06_Servo_Potentiometer/
│   ├── 07_Web_LED_Temperature/
│   └── 08_Web_RGB/
└── Final_Tank_Project/
    ├── README.md
    ├── main.py
    ├── diagram.json
    ├── circuit_layout.svg
    ├── flowchart.svg
    ├── block_diagram.svg
    └── dashboard_preview.html
```

## Final project behavior

| Function | Implementation |
|---|---|
| Temperature + humidity | DHT22 on GP2 |
| Tank distance | HC-SR04: TRIG GP3, ECHO GP4 |
| Cold status | RGB blue below 20 °C |
| Moderate status | RGB green from 20–30 °C |
| Hot status | RGB red above 30 °C |
| Tank warning | Red LED on GP16 when distance < 10 cm |
| Manual pump | Indicator LED on GP17 controlled from web server |
| Browser update | `/data` request every 5 seconds |
| Robustness | DHT22 validation, ultrasonic timeout, Wi-Fi/server retry |

## Evidence

See **[Evidence_Links.md](Evidence_Links.md)** for the guided-project links, final-project assets, and video evidence links.
