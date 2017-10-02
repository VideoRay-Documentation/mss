 
import serial
import struct
import sys
import operator
import argparse
import binascii

import time

#VRCSR protocol defines  
SYNC_REQUEST  =  0x5FF5
SYNC_RESPONSE =  0x0FF0
PROTOCOL_VRCSR_HEADER_SIZE = 6
PROTOCOL_VRCSR_XSUM_SIZE   = 4

#total number of LED banks on the hardware
LED_BANKS = 3

#CSR Address for the LED bank setpoints.  The setpoints are 3 consecutive 32bit floats
ADDR_LED_SETPOINT  = 0x0

#Flag for the standard thruster response which contains
# Bus Voltage
# Bus Current
# Temperature
# Fault Flag
RESPONSE_LED_STANDARD = 0x2
#standard response is the device type followed by 3 32-bit floats and 1 byte
RESPONSE_LED_STANDARD_LENGTH = 1 + 3*4 + 1

#set node ID to the actual node ID of the light to control 
NODE_ID    = 0x01

def main(): 

    #Parse command line arguments for portname, node id, motor id, and thrust values
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--com', help='Comm port to use.', default = '/dev/ttyUSB0', dest='portname')
    parser.add_argument('-i', '--id', help="Node id for the request packet.  The default is 0x01.", default = 0x01, dest='node_id')
    parser.add_argument('setpoint', type=float, nargs='*', help='Per bank power settings. Should be in the 0 to 1 range.' )
    args = parser.parse_args()


    #limit setpoints to 0 and 1
    if (len(args.setpoint) == 0):
        setpoint  = [0,0,0]
    else:
        setpoint = args.setpoint
    for s in setpoint:
        s = max(s, 0)
        s = min(s, 1)
   
    #lets always set all 3 banks for now
    if len(setpoint) == 1: #if just one param, set all banks to the same value
	setpoint = [setpoint[0],setpoint[0],setpoint[0]]
    if len(setpoint) < LED_BANKS: #zero pad missing banks
	setpoint = setpoint + [0] * (LED_BANKS-len(setpoint))
    if len(setpoint) > LED_BANKS: #trim to bank length
	setpoint = setpoint[:LED_BANKS]
    print setpoint
    #open the serial port
    try:        
        port = serial.Serial(args.portname,115200)
        port.timeout = 1
        port.flushInput();
    except IOError:
        print ("Error:  Could not open serial port: " + args.portname)     
        sys.exit()

        
    #Create the custom command packet for setting the power level to a group of thrusters
    #generate the header
    flag = RESPONSE_LED_STANDARD
    #set address to be address of bank 0 plus desired bank times sizeof(float)
    CSR_address = ADDR_LED_SETPOINT
    length = 4*3
    header = bytearray(struct.pack('HBBBB',SYNC_REQUEST,int(args.node_id),flag,CSR_address,length))
    header_checksum = bytearray(struct.pack('i', binascii.crc32(header))) 

    #generate the paylaod with consecutive setpoint values
    payload = bytearray(struct.pack('f',setpoint[0]))
    payload += bytearray(struct.pack('f',setpoint[1]))
    payload += bytearray(struct.pack('f',setpoint[2]))
    payload_checksum = bytearray(struct.pack('i', binascii.crc32(payload)))    

    #send the packet and wait for a response
    packet = header + header_checksum + payload + payload_checksum 

    #uncomment to dump the request payload
    #print (":".join("{:02x}".format(c) for c in packet))


    write_time = time.time()

    #put the packet on the wire
    port.write(bytes(packet))

    #get the response

    expected_response_length = PROTOCOL_VRCSR_HEADER_SIZE + PROTOCOL_VRCSR_XSUM_SIZE +  RESPONSE_LED_STANDARD_LENGTH +  PROTOCOL_VRCSR_XSUM_SIZE
    response_buf = port.read(expected_response_length)

    print ("Got response: %d bytes" % len(response_buf))
    print ("Turnaround time: %f mS" % ((time.time()-write_time) * 1000))

    #parse the response
    response = struct.unpack('=HBBBB I BfffB I', response_buf)

    #uncomment to dump the response buffer
    #print (":".join("{:02x}".format(ord(c)) for c in response_buf))
        
    #header data
    sync =              response[0]
    response_node_id =  response[1]
    flag =              response[2]
    CSR_address =       response[3]
    length =            response[4]
    header_checksum =   response[5]

    #response device type
    device_type      =   response[6];

    #custom response data payload
    bus_v = response[7]
    bus_i = response[8]
    temp = response[9]
    fault = response[10]

    payload_checksum = response[11]

    print ("\nResponse:")
    print ("\tSync:\t\t0x%04x" % sync)
    print ("\tId:\t\t%d" % response_node_id)
    print ("\tFlag:\t\t0x%x" % flag)
    print ("\tAddress:\t0x%x" % CSR_address)
    print ("\tLength:\t\t0x%x" % length)
    print ("\t\tChecksum: 0x%x" % header_checksum)

    print ("\n\tDevice Type:\t\t0x%x" % device_type)
    print ("\tBus Voltage (V):\t%f" % bus_v)
    print ("\tBus Current (A):\t%f" % bus_i)
    print ("\tTemp (C):\t\t%f" % temp)
    print ("\tFault:\t\t\t0x%x" % fault)

    print ("\t\tChecksum: 0x%x" % payload_checksum)



if __name__ == "__main__":
    main();
