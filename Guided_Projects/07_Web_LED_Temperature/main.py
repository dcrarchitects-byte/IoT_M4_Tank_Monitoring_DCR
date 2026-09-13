import network, socket, time, dht
from machine import Pin

sensor = dht.DHT22(Pin(2))
led = Pin(15, Pin.OUT, value=0)
wlan = network.WLAN(network.STA_IF); wlan.active(True); wlan.connect("Wokwi-GUEST", "")
while not wlan.isconnected(): time.sleep(0.1)
print("IP:", wlan.ifconfig()[0])
s = socket.socket(); s.bind(("0.0.0.0", 80)); s.listen(1)
while True:
    client, addr = s.accept(); request = client.recv(1024).decode(); path = request.split(" ")[1] if " " in request else "/"
    if path.startswith("/on"): led.on()
    if path.startswith("/off"): led.off()
    try: sensor.measure(); temp=sensor.temperature(); hum=sensor.humidity()
    except Exception: temp=None; hum=None
    html = "<html><head><meta http-equiv='refresh' content='5'></head><body><h1>Pico W Temperature Monitor</h1><p>Temperature: {} C</p><p>Humidity: {} %</p><p>LED: {}</p><a href='/on'>LED ON</a> | <a href='/off'>LED OFF</a></body></html>".format(temp, hum, "ON" if led.value() else "OFF")
    client.send("HTTP/1.1 200 OK\r\nContent-Type:text/html\r\nConnection:close\r\n\r\n" + html); client.close()
