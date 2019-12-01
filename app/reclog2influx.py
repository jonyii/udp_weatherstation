import socket
import sys
import logging
from influxdb import InfluxDBClient

logging.basicConfig(level=logging.INFO,
            format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            )

# influx connector
influx = InfluxDBClient(host='localhost', port=8086)
influx.switch_database('weather')

# dedup struct
senders = {}
stations= {1:"Donovaly - Nová Hoľa"}

with open(sys.argv[1]) as f:

    for data in f:
        if 'packetNo=' not in data:
            continue

        #2019-11-23 07:13:53.913 INFO udp_rec:  24 bytes from 46.34.226.154:03093 > b'packetNo=27,0,0,264,218;'
        sp = data.split(' ')
        dt= '%sT%sZ' %(sp[0], sp[1][:-4])
        fields = sp[-1][11:-3].split(',')
        address = sp[-3].split(":")
        logging.debug("decoded %s > %s %s", address, dt, fields)

        ########### same from here

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

        logging.info('{} weather update {}: WindAvg={}, WindMax={}, WindDir={}, Temp={}'.format(stationName, dt, WindAvg, WindMax, WindDir, Temperature))

        influx_measurements= [
                    {
                        "measurement": "meteoStation",
                        "tags": {
                            "station": stationName,
                            "stationNo": stationNo,
                            "packetId": packetId 
                        },
                        "time": dt,
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






