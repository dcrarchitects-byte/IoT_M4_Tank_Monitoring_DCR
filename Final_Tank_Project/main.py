import time, socket, network, dht
from machine import Pin, time_pulse_us

DHT_PIN=2; TRIG_PIN=3; ECHO_PIN=4; RGB_R_PIN=13; RGB_G_PIN=14; RGB_B_PIN=15; TANK_ALERT_PIN=16; PUMP_LED_PIN=17
SAMPLE_INTERVAL_MS=5000; WIFI_RETRY_MS=15000
WIFI_SSID="Wokwi-GUEST"; WIFI_PASSWORD=""
COLD_LIMIT_C=20.0; HOT_LIMIT_C=30.0; TANK_WARNING_DISTANCE_CM=10.0

dht_sensor=dht.DHT22(Pin(DHT_PIN)); trig=Pin(TRIG_PIN,Pin.OUT,value=0); echo=Pin(ECHO_PIN,Pin.IN)
rgb_r=Pin(RGB_R_PIN,Pin.OUT,value=0); rgb_g=Pin(RGB_G_PIN,Pin.OUT,value=0); rgb_b=Pin(RGB_B_PIN,Pin.OUT,value=0)
tank_alert_led=Pin(TANK_ALERT_PIN,Pin.OUT,value=0); pump_led=Pin(PUMP_LED_PIN,Pin.OUT,value=0)
temperature_c=None; humidity_rh=None; distance_cm=None; rgb_status="UNKNOWN"; tank_status="UNKNOWN"; pump_on=False; sensor_fault="None"; wifi_online=False; ip_address="Not connected"; server_socket=None
last_sample_ms=time.ticks_add(time.ticks_ms(),-SAMPLE_INTERVAL_MS); last_wifi_attempt_ms=time.ticks_add(time.ticks_ms(),-WIFI_RETRY_MS)

def set_rgb(r,g,b):
    rgb_r.value(1 if r else 0); rgb_g.value(1 if g else 0); rgb_b.value(1 if b else 0)

def classify_temperature(temp):
    global rgb_status
    if temp is None: set_rgb(0,0,0); rgb_status="SENSOR ERROR"
    elif temp<COLD_LIMIT_C: set_rgb(0,0,1); rgb_status="COLD - BLUE"
    elif temp<=HOT_LIMIT_C: set_rgb(0,1,0); rgb_status="MODERATE - GREEN"
    else: set_rgb(1,0,0); rgb_status="HOT - RED"

def read_dht22():
    try:
        dht_sensor.measure(); temp=float(dht_sensor.temperature()); hum=float(dht_sensor.humidity())
        if temp<-40 or temp>80: raise ValueError("temperature outside expected DHT22 range")
        if hum<0 or hum>100: raise ValueError("humidity outside 0-100% range")
        return temp,hum,None
    except Exception as exc: return None,None,"DHT22: {}".format(exc)

def read_distance_cm():
    try:
        trig.value(0); time.sleep_us(2); trig.value(1); time.sleep_us(10); trig.value(0)
        pulse=time_pulse_us(echo,1,30000)
        if pulse<0: raise OSError("echo timeout")
        dist=pulse/58.0
        if dist<2 or dist>400: raise ValueError("distance outside 2-400 cm range")
        return round(dist,1),None
    except Exception as exc: return None,"HC-SR04: {}".format(exc)

def update_tank_warning(distance):
    global tank_status
    if distance is None: tank_alert_led.value(0); tank_status="SENSOR ERROR"
    elif distance<TANK_WARNING_DISTANCE_CM: tank_alert_led.value(1); tank_status="NEAR EMPTY - WARNING"
    else: tank_alert_led.value(0); tank_status="NORMAL"

def set_pump(state):
    global pump_on
    pump_on=bool(state); pump_led.value(1 if pump_on else 0); print("Pump","ON" if pump_on else "OFF")

def sample_sensors():
    global temperature_c,humidity_rh,distance_cm,sensor_fault
    temp,hum,e1=read_dht22(); dist,e2=read_distance_cm(); temperature_c=temp; humidity_rh=hum; distance_cm=dist
    classify_temperature(temp); update_tank_warning(dist); faults=[e for e in (e1,e2) if e]; sensor_fault=" | ".join(faults) if faults else "None"
    print("Temperature:",temperature_c,"C | Humidity:",humidity_rh,"% | Distance:",distance_cm,"cm | RGB:",rgb_status,"| Tank:",tank_status,"| Pump:","ON" if pump_on else "OFF")

def connect_wifi(timeout_s=15):
    global wifi_online,ip_address
    wlan=network.WLAN(network.STA_IF); wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID,WIFI_PASSWORD); start=time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(),start)>timeout_s*1000: wifi_online=False; return False,"Not connected"
            time.sleep(0.25)
    wifi_online=True; ip_address=wlan.ifconfig()[0]; print("Wi-Fi:",ip_address); return True,ip_address

def data_json():
    def j(v): return "null" if v is None else str(round(v,1))
    return '{"temperature":%s,"humidity":%s,"distance":%s,"rgb_status":"%s","tank_status":"%s","tank_alert":%s,"pump_on":%s,"wifi_online":%s,"ip":"%s","fault":"%s"}'%(j(temperature_c),j(humidity_rh),j(distance_cm),rgb_status,tank_status,"true" if tank_alert_led.value() else "false","true" if pump_on else "false","true" if wifi_online else "false",ip_address,sensor_fault.replace('"',"'"))

def dashboard_html():
    return '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Tank Monitoring</title><style>body{font-family:Arial;background:#eef4ef;color:#173b31;margin:0;padding:25px}.wrap{max-width:900px;margin:auto}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}.card{background:white;padding:20px;border-radius:15px}.v{font-size:34px;font-weight:800}button{padding:12px 18px;margin:6px;border:0;border-radius:9px;font-weight:700}.on{background:#1f6048;color:white}.off{background:#f4dfe0;color:#a8232a}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style></head><body><div class="wrap"><h1>Tank Monitoring & Filling System</h1><div class="grid"><div class="card"><b>TEMPERATURE</b><div class="v"><span id="t">--</span> C</div><p id="rgb">--</p></div><div class="card"><b>HUMIDITY</b><div class="v"><span id="h">--</span>%</div></div><div class="card"><b>TANK DISTANCE</b><div class="v"><span id="d">--</span> cm</div><p id="tank">--</p></div><div class="card" style="grid-column:1/-1"><h2>Pump: <span id="p">OFF</span></h2><button class="on" onclick="cmd('on')">TURN ON</button><button class="off" onclick="cmd('off')">TURN OFF</button><p>Values refresh every 5 seconds.</p></div></div></div><script>function f(v){return v==null?'--':Number(v).toFixed(1)}async function r(){let d=await(await fetch('/data')).json();t.textContent=f(d.temperature);h.textContent=f(d.humidity);document.getElementById('d').textContent=f(d.distance);rgb.textContent=d.rgb_status;tank.textContent=d.tank_status;p.textContent=d.pump_on?'ON':'OFF'}async function cmd(x){await fetch('/pump/'+x);r()}r();setInterval(r,5000)</script></body></html>'''

def send_response(c,status,ctype,body):
    c.send(("HTTP/1.1 %s\r\nContent-Type: %s\r\nCache-Control: no-store\r\nConnection: close\r\nContent-Length: %d\r\n\r\n%s"%(status,ctype,len(body),body)).encode())

def open_server():
    global server_socket
    try:
        addr=socket.getaddrinfo("0.0.0.0",80)[0][-1]; s=socket.socket(); s.bind(addr); s.listen(2); s.settimeout(0.25); server_socket=s; print("Server http://"+ip_address); return True
    except Exception as exc: print("Server error:",exc); server_socket=None; return False

def handle_client(c):
    try:
        req=c.recv(1024).decode(); parts=req.split("\r\n",1)[0].split(); path=parts[1] if len(parts)>=2 else "/"
        if path.startswith('/pump/on'): set_pump(True); send_response(c,'200 OK','application/json',data_json())
        elif path.startswith('/pump/off'): set_pump(False); send_response(c,'200 OK','application/json',data_json())
        elif path.startswith('/data'): send_response(c,'200 OK','application/json',data_json())
        else: send_response(c,'200 OK','text/html; charset=utf-8',dashboard_html())
    except Exception as exc: print('HTTP error:',exc)
    finally:
        try:c.close()
        except:pass

print('IoT Masters - Tank Monitoring and Filling System'); set_rgb(0,0,0); set_pump(False); sample_sensors()
if connect_wifi()[0]: open_server()
while True:
    now=time.ticks_ms()
    if time.ticks_diff(now,last_sample_ms)>=SAMPLE_INTERVAL_MS: last_sample_ms=now; sample_sensors()
    if server_socket is None:
        if time.ticks_diff(now,last_wifi_attempt_ms)>=WIFI_RETRY_MS:
            last_wifi_attempt_ms=now
            if connect_wifi()[0]: open_server()
        time.sleep_ms(50); continue
    try:
        client,address=server_socket.accept(); handle_client(client)
    except OSError: pass
    except Exception as exc:
        print('Server loop error:',exc)
        try: server_socket.close()
        except: pass
        server_socket=None
    time.sleep_ms(20)
