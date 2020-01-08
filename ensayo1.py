"""Publishes multiple messages to a Pub/Sub topic with an error handler."""
import time
import smbus2
import bme280
import serial
import string
import pynmea2
from google.cloud import pubsub_v1

project_id = "ensayo-bme"
topic_name = "events"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)

futures = dict()

def get_callback(f, data):
    def callback(f):
        try:
            print(f.result())
            futures.pop(data)
        except:  
            print("Please handle {} for {}.".format(f.exception(), data))

    return callback

def get_string(port=1, address=0x77, info="temperatura"):
    bus = smbus2.SMBus(port)
    calibration_params = bme280.load_calibration_params(bus, address)
    data = bme280.sample(bus, address, calibration_params)

    print(str(data))
    if info == "temperatura":
        rpta = data.temperature
    elif info == "presion":
        rpta = data.pressure
    elif info == "humedad":
        rpta = data.humidity
    else:
        rpta=-999999
        
    return str(rpta)

def get_coordenadas(ser):
    dataout = pynmea2.NMEAStreamReader()
    data=ser.readline()
    newdata = data.decode()
    while newdata[0:6] != "$GPRMC":
        data=ser.readline()
        newdata = data.decode()
    newmsg=pynmea2.parse(newdata)
    lat=newmsg.latitude
    lng=newmsg.longitude

    return (lat,lng)

port="/dev/ttyS0"
ser=serial.Serial(port, baudrate=9600, timeout=0.5)
for i in range(10):
    data = get_string(1,0x77, "temperatura")
    coordenadas = get_coordenadas(ser)
    futures.update({data: None})
    # When you publish a message, the client returns a future.
    future = publisher.publish(
        topic_path, data=data.encode("utf-8"), coordinates=str(coordenadas)  # data must be a bytestring.
    )
    futures[data] = future
    # Publish failures shall be handled in the callback function.
    future.add_done_callback(get_callback(future, data))
    time.sleep(10)

# Wait for all the publish futures to resolve before exiting.
while futures:
    time.sleep(5)

print("Published message with error handler.")
ser.close()
print("puerto cerrado")
