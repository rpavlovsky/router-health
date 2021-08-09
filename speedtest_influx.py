#!/opt/bin/python3
"""speedtest_influx.py: Telemtry collection script for Speedtest.net results"""
__author__ = "Richard Pavlovsky (pavlovsky@mac.com)"

import argparse
import datetime
import re
import subprocess
import time
import speedtest

from influxdb import InfluxDBClient  # pip install influxdb

class Record:
    """ noun (rekard) a thing constituting a piece of evidence from the past """
    def __init__( self, measurement_name ):
        """ constructor, also grabs some details on how to connect to influx """
        self.measurement = measurement_name

        # read influx user and pass from filesystem file called .passwd
        f=open(".passwd","r")
        lines=f.readlines()
        self.ifuser=lines[0].strip()
        self.ifpass=lines[1].strip()
        f.close()

        # influx configuration - edit these
        self.ifdb   = "grafana"
        self.ifhost = "192.168.1.151"
        self.ifport = 8086
    
    def record( self, tstamp, rstats ):
        """ verb (rekord) set down in writing or some other form for later reference """
        
        # to-do: add a debug or dryrun option to print these out, else no output
        ping_ms = rstats.getPingMs()
        print("ping_ms: ", ping_ms)
        download = rstats.getDownload()
        print("download: ", download )
        upload = rstats.getUpload()
        print("upload: ", upload)

        # format the data as a single measurement for influx, remember all must be floats
        # if they are strings or non-float values it'll look like it'll work but grafana
        # won't be able to graph the data.  Save yourself heartache and ensure they are 
        # floats
        body = [
            {                                     
                "measurement": self.measurement,
                "time": tstamp,       
                "fields": {
                    "download": download,
                    "upload": upload,         
                    "ping": ping_ms,
                }                   
            }                       
        ]   

        # connect to influx         
        ifclient = InfluxDBClient(self.ifhost,self.ifport,self.ifuser,self.ifpass,self.ifdb)
                            
        # write the measurement     
        ifclient.write_points(body)     

class SpeedtestStats:
    def __init__( self, ):
        self.tstamp = datetime.datetime.utcnow()
        self.results_dict = self.runTest()

    def runTest( self ):
        ''' run a speedtest.net test '''
        s = speedtest.Speedtest()
        s.get_best_server()
        s.download(threads=1)
        s.upload(threads=1)
        return s.results.dict()
               
    def getPingMs( self, ):                  
        ''' return ping time from results dictionary '''
        return float(self.results_dict['ping'])

    def getDownload( self, ):
        ''' return download speed as a float '''
        return float(self.results_dict['download'])

    def getUpload( self, ):
        ''' return upload speed as a float '''
        return float(self.results_dict['upload'])
                                               


def main():
    parser = argparse.ArgumentParser(description='Speedtest Stats Collection Script for Network Perf Monitoring')
    parser.add_argument('-m', '--measurement', required=True,
                    help='the measurement name in influxdb to record the stats')

    args = vars(parser.parse_args())

    sstats = SpeedtestStats()
    print(sstats.tstamp)
    robj = Record( args['measurement'] )
    robj.record( sstats.tstamp, sstats )

if __name__ == "__main__":
    main()