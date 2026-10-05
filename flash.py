
###IMPORTANT NOTE: FOR TFTP TO TRANSFER FILES OVER LOCALLY, AND GRAB FILES FROM YOUR COMPUTER, YOUR COMPUTER'S FIREWALL MUST ALLOW IT, OTHERWISE
###PACKAGES WILL BE SILENTLY DROPPED AFTER DHCP REQUEST

#for use, start tftpd server, verify desired firmware is located in the same folder as tftpd
import serial
import re  #similar to regex, used for searching through text for a specific pattern of characters instead of literal characters - use this for extracting the serial number
import hashlib
import time

#firmware = "ArubaInstant_Centaurus_8.6.0.25_90367"
#firmware = "ArubaInstant_Draco_8.10.0.23_95854"
#fimrware = "ArubaInstant_Hercules_8.10.0.22_95256"
firmware = "ArubaInstant_Lupus_8.10.0.22_95256"
#firmware = "ArubaInstant_Ursa_8.10.0.22_95256"
#firmware = "ArubaInstant_Lupus_8.6.0.25_90367"

tftpdServer = "192.168.10.210"
comPort = 4

ser = serial.Serial(f"COM{comPort}", baudrate=9600, timeout=4)
print("Port opened successfully:", ser.name)
count = 0
apSerialNum = ""
apHash =""
totalData = ""
commands = ["mfginfo", 
            f"proginv system ccode CCODE-US-{apHash}", 
            "invent -w", 
            "dhcp", 
            f"setenv serverip {tftpdServer}", 
            "clear os 0", 
            f"upgrade os 0 {firmware}", 
            "clear os 1", 
            "saveenv", 
            "boot"]

def getSerialNum():
    mfginfo = ser.read_until(b"Card 1").decode(errors="replace")
    print("MFGINFO LINE " + mfginfo)
    apSerialNumLine = re.search(r"Serial\s*:\s*(\S+)",mfginfo, re.IGNORECASE)
    if apSerialNumLine:
        num = apSerialNumLine.group(1)#group 1 is the first paranthesis match
        print("found serial num: " + num + " \n")
        return num
    else:
        print("no serial num found")
        return None

def getHash(serialNum):
    hashInput = f"US-{serialNum}"
    sha1_hash= hashlib.sha1(hashInput.encode()).hexdigest()#returns a hex value of the calculated sha, remember, we need to encode from the asci to bytes for this funciton
    print(sha1_hash)
    return sha1_hash

def commandEchoed(command, text):
    if (f"{commands[command]}" in text):
        print("\n command has been echoed\n")
        return True
    else:
        return False

try:
    while True:
        data = ser.read(ser.in_waiting or 1).decode(errors="replace") #read incoming bytes within the buffer and return to data, or if nothing in buffer, wait until youve read 1 byte and return to data. before retuning to data, decode to ascii and any garbled doody,  replace

        if data:#if there is anything in data
            totalData+=data
            print(data, end="")
#stop autoboot
            if "Hit <Enter> to stop autoboot:" in totalData:
                totalData = ""
                count = 0 #reset count in case the boot times out, this way it will continue working through all the commands when it reboots
                ser.write(b"\r\n")#the carriage return or enter command, b means send the literal bytes instead of the string \r\n 
#begin sending commands, first and second commands will be unique to each ap, all commands after that will be the same
            if "apboot>" in totalData: #we need to wait for apboot AND have seen our last command echoed 
                totalData = ""
                if count < len(commands):
                    ser.write(commands[count].encode() + b"\r\n")
                    print(f"\nSent command[{count}]: {commands[count]}\n")
                    time.sleep(1)
                    if count == len(commands) - 1: #last command resets, drop serial connection or else you will keep overwriting
                        print("just finished reset command, exiting script")
                        break
                    #for first command, find the serial code and sha value
                    if(count == 0):
                       #parse serial number from mfginfo
                       apSerialNum = getSerialNum()
                       if apSerialNum:
                           apHash = getHash(apSerialNum)
                           commands[1] = f"proginv system ccode CCODE-US-{apHash}" #updates commands 1
                       else:
                           print("No Serial number captured, exiting...")
                           break
                    count+=1
                    

except KeyboardInterrupt:
    print("\nyou pressed ctrl c, exited")
finally:
    ser.close()