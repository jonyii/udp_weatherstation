import socket
import sys, os
import logging
from influxdb import InfluxDBClient

logfile = os.getenv('LOGFILE', '/var/log/weather.log')

logging.basicConfig(filename=logfile, level=logging.INFO,
            format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            )

# .sprintf((char*)buff,"packetNo=%ld,%d,%d,%d,%ld,1;",packet_no,WindAvg,WindMax,WindDir,Temperature);

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the port
server_address = ('0.0.0.0', 7654)
logging.info('starting listener on {} port {}'.format(*server_address))
sock.bind(server_address)

# influx connector
influx_host = os.getenv('INFLUX_HOST', 'localhost')
influx_port = int(os.getenv('INFLUX_PORT', 8086))
influx = InfluxDBClient(host=influx_host, port=influx_port)
influx.switch_database('weather')

# dedup struct
senders = {}
stations= {1:"Donovaly - Nová Hoľa"}

while True:
    data, address = sock.recvfrom(4096)

    logging.info('{:3d} bytes from {}:{:05d} > {}'.format(len(data), address[0], address[1], data))

    if data.startswith(b'packetNo=') and data.endswith(b';'):
        fields = data[9:-1].decode('utf-8').split(',')
        if len(fields)!=6:
            logging.error('weather data does not contain 6 fields')
            continue

        packet_no = int(fields[0])
        WindAvg = float(fields[1])/10
        WindMax = float(fields[2])/10
        WindDir = int(fields[3])
        Temperature = float(fields[4])/100
        stationNo = int(fields[5])

        packetId = '{}:{}/{}'.format(address[0], address[1], packet_no)

        if stationNo not in senders:
            senders[stationNo] = None

        if senders[stationNo] == packetId:
            logging.error('{} duplicate detected, last packet_no={}, current packet_no={}'.format(address, senders[address], packet_no))
            continue
        senders[stationNo] = packetId
        stationName = stations.get(stationNo, 'Unknown')

        logging.info('{} weather update WindAvg={}, WindMax={}, WindDir={}, Temp={}'.format(stationName, WindAvg, WindMax, WindDir, Temperature))

        influx_measurements= [
                    {
                        "measurement": "meteoStation",
                        "tags": {
                            "station": stationName,
                            "stationNo": stationNo,
                            "packetId": packetId 
                        },
                        "fields": {
                            "WindAvg": WindAvg,
                            "WindMax": WindMax,
                            "WindDir": WindDir,
                            "Temperature": Temperature
                        }
                    }
                ]        

        #print(influx_measurements)
        influx.write_points(influx_measurements)






