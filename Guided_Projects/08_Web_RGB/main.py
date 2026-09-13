import network, socket, time
from machine import Pin

r = Pin(13, Pin.OUT, value=0); g = Pin(14, Pin.OUT, value=0); b = Pin(15, Pin.OUT, value=0)
colors = {"red":(1,0,0), "green":(0,1,0), "blue":(0,0,1), "off":(0,0,0)}
current = "off"
def set_color(name):
    global current
    rr,gg,bb = colors.get(name, colors["off"]); r.value(rr); g.value(gg); b.value(bb); current=name
wlan=network.WLAN(network.STA_IF); wlan.active(True); wlan.connect("Wokwi-GUEST", "")
while not wlan.isconnected(): time.sleep(0.1)
s=socket.socket(); s.bind(("0.0.0.0",80)); s.listen(1)
while True:
    client,addr=s.accept(); request=client.recv(1024).decode(); path=request.split(" ")[1] if " " in request else "/"
    for name in colors:
        if path.startswith("/"+name): set_color(name)
    html="<html><body><h1>RGB Web Control</h1><p>Current: {}</p><a href='/red'>RED</a> | <a href='/green'>GREEN</a> | <a href='/blue'>BLUE</a> | <a href='/off'>OFF</a></body></html>".format(current.upper())
    client.send("HTTP/1.1 200 OK\r\nContent-Type:text/html\r\nConnection:close\r\n\r\n"+html); client.close()
