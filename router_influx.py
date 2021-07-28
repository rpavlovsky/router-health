#!/opt/bin/python3
"""router_influx.py: Telemtry collection script for ASUS Merlin wifi routers"""
__author__ = "Richard Pavlovsky (pavlovsky@mac.com)"

import datetime
import re
import subprocess

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

        ping_ms = rstats.getPingMs( 'www.google.com' )
        print("ping_ms: ", ping_ms)
        used_mb, free_mb = rstats.getMemUsage()
        print("used_mb: ", used_mb, " free_mb: ", free_mb)
        e1assoc = rstats.getAssocList( rstats.interface24 )
        e2assoc = rstats.getAssocList( rstats.interface5 )
        totassoc = e1assoc + e2assoc
        print( "24assoc: ", e1assoc, " 5assoc: ", e2assoc, " totassoc: ", totassoc )
        eth0_rx_bytes, eth0_tx_bytes = rstats.getNetBytes( 'eth0' )
        print( "rx_bytes: ", eth0_rx_bytes, " tx_bytes: ", eth0_tx_bytes )
        cpu_temp = rstats.getCpuTemp( rstats.cputempfile )               
        print( "cpu_temp: ", cpu_temp ) 

        # format the data as a single measurement for influx
        body = [
            {                                     
                "measurement": self.measurement,
                "time": tstamp,       
                "fields": {         
                    "ping": ping_ms,
                    "used_mb": used_mb,
                    "free_mb": free_mb,
                    "eth1_assoc": e1assoc,
                    "eth2_assoc": e2assoc,
                    "tot_assoc": totassoc,
                    "eth0_rx_bytes": eth0_rx_bytes,
                    "eth0_tx_bytes": eth0_tx_bytes,
                    "cpu_temp": cpu_temp,
                    #"cpu_usr": cpu_usr,
                    #"cpu_sys": cpu_sys,
                    #"cpu_nic": cpu_nic,
                    #"cpu_idle": cpu_idle,
                    #"cpu_io": cpu_io,
                    #"cpu_irq": cpu_irq,
                    #"cpu_sirq": cpu_sirq,
                }                   
            }                       
        ]   

        # connect to influx         
        ifclient = InfluxDBClient(self.ifhost,self.ifport,self.ifuser,self.ifpass,self.ifdb)
                            
        # write the measurement     
        #ifclient.write_points(body)     

class RouterStats:
    def __init__( self, router_model ):
        self.model  = router_model
        self.tstamp = datetime.datetime.utcnow()

        if router_model == 'ac88u':
            self.cputempfile = '/sys/class/thermal/thermal_zone0/temp'
            self.interface24 = 'eth6'
            self.interface5  = 'eth7'
        elif router_model == 'ac68u':
            self.cputempfile = '/proc/dmu/temperature'
            self.interface24 = 'eth1'
            self.interface5  = 'eth2'
        elif router_model == 'n66r':
            self.cputempfile = ''
            self.interface24 = 'eth1'
            self.interface5  = 'eth2'
        else:
            print('unknown router model')
               
    def getCpuStats():
        # router cpu                                                                                               
        p1 = subprocess.Popen(["top", "-bn1"], stdout=subprocess.PIPE)                                              
        p2 = subprocess.Popen(["head", "-3"], stdin=p1.stdout, stdout=subprocess.PIPE)                              
        p3 = subprocess.Popen(["awk", "/CPU/ { print $2,$4,$6,$8,$10,$12,$14 }"], stdin=p2.stdout, stdout=subprocess.PIPE)            
        p4 = subprocess.Popen(["sed", "s/%//g"], stdin=p3.stdout, stdout=subprocess.PIPE)                           
        p1.stdout.close()                                                                                           
        p2.stdout.close()                                                                                           
        p3.stdout.close()                                                                                           
        cpu_usr, cpu_sys, cpu_nic, cpu_idle, cpu_io, cpu_irq, cpu_sirq = p4.communicate()[0].decode('ascii').rstrip().split()                                     
        cpu_usr = float(cpu_usr)                                                                           
        cpu_sys = float(cpu_sys)    
        cpu_nic = float(cpu_nic)    
        cpu_idle = float(cpu_idle)  
        cpu_io = float(cpu_io)      
        cpu_irq = float(cpu_irq)  
        cpu_sirq = float(cpu_sirq)
        return cpu_usr 

    def getPingMs( self, uri='www.google.com' ):                  
        ''' ping test a uri and return avg results from 4 samples in ms, remember to save as floats!
        make this first or last since it runs the longest '''
        p = subprocess.Popen(["ping", "-c", "4", "www.google.com", ], stdout=subprocess.PIPE)
        m = re.search('round-trip min/avg/max = (\d+.\d+)/(\d+.\d+)/(\d+.\d+) ms', p.stdout.read().decode('utf-8'))
        return float(m.group(1))
                                               
    def getCpuTemp( self, cputempfile ):           
        ''' get the cpu temperature, return a float'''
        p = subprocess.Popen([ "cat", cputempfile ], stdout=subprocess.PIPE)
        m = re.search('CPU temperature\t: (\d+)*', p.stdout.read().decode('utf-8'))
        return float(m.group(1)) 
        #return float(p.stdout.read().decode('utf-8')) / 1024.0            

    def getWifiTemp( self, interface = 'eth1'):
        ''' Get the temperature of the Wifi CPU's, remember to save data as floats '''
        p1 = subprocess.Popen([ "wl", "-i", interface, "phy_tempsense" ], stdout=subprocess.PIPE)
        p2 = subprocess.Popen([ "awk", "{ print $1 * .5 + 20 }" ], stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()       
        return float(p2.communicate()[0].decode('ascii').rstrip())
                            
    def getMemUsage( self, ):
        ''' Get memory usage of the router in MBs '''          
        p1 = subprocess.Popen(["top", "-bn1"], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["head", "-3"], stdin=p1.stdout, stdout=subprocess.PIPE)
        p3 = subprocess.Popen(["awk", "/Mem/ { print $2,$4 }"], stdin=p2.stdout, stdout=subprocess.PIPE)
        p4 = subprocess.Popen(["sed", "s/K//g"], stdin=p3.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()           
        p2.stdout.close()           
        p3.stdout.close()           
        used_kb, free_kb = p4.communicate()[0].decode('ascii').rstrip().split()
        used_mb = float( used_kb ) / 1024.0
        free_mb = float( free_kb ) / 1024.0
        return( used_mb, free_mb ) 

    def getAssocList( self, interface='eth1' ):
        ''' Get the number of wifi connections per interface, return as a float'''
        p1 = subprocess.Popen(["wl", "-i", interface, "assoclist"], stdout=subprocess.PIPE)                       
        p2 = subprocess.Popen(["awk", "{ print $2 }"], stdin=p1.stdout, stdout=subprocess.PIPE) 
        p3 = subprocess.Popen(["wc", "-l"], stdin=p2.stdout, stdout=subprocess.PIPE)         
        p1.stdout.close()       
        p2.stdout.close()                                                                                
        return float(p3.communicate()[0].decode('ascii').rstrip())
                            
    def getNetBytes( self, interface='eth0' ):
        ''' Get read and write bytes per interface, return as floats '''                                                                                 
        for line in open('/proc/net/dev', 'r'):                                                                 
            if interface in line:                                                                               
                data = line.split('%s:' % interface)[1].split()                                                 
                rx_bytes, tx_bytes = (data[0], data[8])                                                         
                return (float(rx_bytes), float(tx_bytes))  
                            
def main():
    print( "Router Stats Collection Script for Asus Merlin!" )
    rstats = RouterStats( 'ac68u' )
    print(rstats.model)
    print(rstats.tstamp)
    robj = Record( 'asus_router' )
    robj.record( rstats.tstamp, rstats )

if __name__ == "__main__":
    main()



                     
                            





 

