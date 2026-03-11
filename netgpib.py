import sys
import math
import socket
import time
import pdb
import select
import struct
import termstatus

class netGPIB:
    def __init__(self,ip,gpibAddr,eot='\004',debug=0, auto=False):

        #End of Transmission character
        self.eot=eot
        # EOT character number in the ASCII table
        self.eotNum=struct.unpack('B',eot.encode())[0]
       

        #Debug flag
        self.debug = debug

        #Auto mode
        self.auto = auto

        self.ip = ip
        self.gpibAddr=gpibAddr
        self.timeout = 100
        #Connect to the GPIB-Ethernet converter
        netAddr=(ip, 1234)
        self.netSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.netSock.settimeout(100)
        self.netSock.connect(netAddr)
        #print(self.netSock.connect(netAddr))
        #quit()
        


        #Initialize the GPIB-Ethernet converter
        self.netSock.setblocking(0)
        self.netSock.send("++addr ".encode()+str(self.gpibAddr).encode()+b"\n")
        time.sleep(0.1)
        self.netSock.send("++eos 3\n".encode())
        time.sleep(0.1)
        self.netSock.send("++mode 1\n".encode())
        time.sleep(0.1)
        if self.auto:
            self.netSock.send("++auto 1\n".encode())
        else:
            self.netSock.send("++auto 0\n".encode())
        time.sleep(0.1)
        self.netSock.send("++ifc\n".encode())
        time.sleep(0.1)
        self.netSock.send("++read_tmo_ms 3000\n".encode())
        time.sleep(0.1)
        self.netSock.send("++eot_char ".encode()+str(self.eotNum).encode()+b"\n")
        self.netSock.send("++eot_enable 1\n".encode())
        self.netSock.send("++addr ".encode()+str(self.gpibAddr).encode()+b"\n")
        
    def refresh(self):
        self.netSock.send("++addr ".encode()+str(self.gpibAddr).encode()+b"\n")
        time.sleep(0.1)
        self.netSock.send("++eos 3\n".encode())
        time.sleep(0.1)
        self.netSock.send("++mode 1\n".encode())
        time.sleep(0.1)
        if self.auto:
            self.netSock.send("++auto 1\n".encode())
        else:
            self.netSock.send("++auto 0\n".encode())
        time.sleep(0.1)
        self.netSock.send("++ifc\n".encode())
        time.sleep(0.1)
        self.netSock.send("++read_tmo_ms 3000\n".encode())
        time.sleep(0.1)
        self.netSock.send("++eot_char".encode()+str(self.eotNum).encode()+b"\n")
        self.netSock.send("++eot_enable 1\n".encode())
        self.netSock.send("++addr ".encode()+str(self.gpibAddr).encode()+b"\n")


    def getData(self, buf, sleep=0.1):
        data=""
        dlen=0
        if self.debug == True:
            progressInfo=termstatus.statusTxt("0 bytes received")
        while 1: # Repeat reading data until eot is found
            while 1:  # Read some data
                readSock, writeSock, errSock = select.select([self.netSock],[],[],self.timeout)
               
                if len(readSock) == 1:
                    data1 = readSock[0].recv(buf).decode('latin-1')
                    if self.debug == True:
                        dlen=dlen+len(data1)
                        progressInfo.update(str(dlen)+' bytes received')
                    break
                

            if data1[-1] == self.eot: #if eot is found at the end
                data = data + data1[:-1] #remove eot
                break
            else:
                data = data + data1
                time.sleep(0.1)

        if self.debug == True:
            progressInfo.end()
        return data
            
    def query(self,string,buf=100,sleep=0):
        """Send a query to the device and return the result."""
        self.netSock.send(string.encode()+b"\n")
        if not self.auto:
            time.sleep(sleep)
            self.netSock.send("++read eoi\n".encode()) #Change to listening mode
        return self.getData(buf)
    
    def command(self,string,sleep=0):
        """Send a command to the device."""
        self.netSock.send(string.encode()+b"\n")
        time.sleep(sleep)

    def spoll(self):
        """Perform a serial polling and return the result."""
        self.netSock.send("++spoll\n".encode())
        while 1:  # Read some data
            readSock, writeSock, errSock = select.select([self.netSock],[],[],3)
            if len(readSock) == 1:
                data = readSock[0].recv(100)
                break

        return data[:-2]
    
    def close(self):
        self.netSock.close()
        
    def setDebugMode(self, debugFlag):
        if debugFlag:
            self.debug=1
        else:
            self.debug=0


def gpibGetData(netSock, buf, eot, debug=0):
    data=""
    while 1: # Repeat reading data until eot is found
        while 1:  # Read some data
            readSock, writeSock, errSock = select.select([netSock],[],[],3)
            if len(readSock) == 1:
                data1 = readSock[0].recv(buf)
                if debug == True:
                    print(str(len(data1))+' bytes received')
                break
                

        if data1[len(data1)-1] == eot: #if eot is found at the end
            data = data + data1[0:len(data1)-1] #remove eot
            break
        else:
            data = data + data1
            time.sleep(1)

    return data
