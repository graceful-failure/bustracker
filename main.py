import machine
import neopixel
import usocket as socket
import network
import re
import uasyncio as asyncio
import uaiohttpclient as aiohttp


station = network.WLAN(network.STA_IF)

#wifi data
ssid = "XXXX"
password = "XXXX"

url = "http://publicyork4.rslepi.co.uk/departureboards/mEPIDepartureBoard.aspx?ID=XXXX"#Departure board URL without HTTPS

relevant_routes = {'X', 'X', 'X'} #Set of routes we're interested in

#30 neopixels in the string numbers 0-29. Controlled on pin 17
np=neopixel.NeoPixel(machine.Pin(17), 30)
pixelcount = np.n
initialbrightness = 100
first_stop_offset = 9 #This is where the home stop will be. Any neopixels < than this aren't used.

#Defining busdata as a global variable
busdata = {}

async def clear(np):
    for i in range(pixelcount):
        np[i] = (0, 0, 0)
    np.write()

#Loops the scroll animation until busdata is returned
async def scroll(np):
    while bool(busdata) is not True:
        for i in range(pixelcount):
            if bool(busdata) is True: break
            np[i - 1] = (0, 0, 0)
            np[i] = (0, initialbrightness, 0)
            np.write()            
            await asyncio.sleep_ms(50)

def connect_internet():
    if station.isconnected() == False:
        station.active(True)
        station.connect(ssid, password)
        while station.isconnected() == False:
          pass
    
async def get_buses():
    
    #This dictionary will have a numerical key, then a sub key: value going Service_number, Direction, Time
    buses = {}
    
    response = await aiohttp.request("GET",url)
    
    bulkdata = await response.read()
          
    #Bin the header and footer
    bulkdata = re.search("<tbody>(.+?)</tbody>",bulkdata).group(1)
    
    #convert to string and bin whitespace
    bulkdata = str(bulkdata)
    bulkdata = bulkdata.replace(" ","")

    #bin anything in format (non-alphanumeric) then r or n
    bulkdata = re.sub("\W[rn]","",bulkdata)

    #bin <td> </td> <tr> </tr> Replace with a space
    bulkdata = re.sub("\W+[t][dr]\W"," ",bulkdata)
    #Get rid of some html
    bulkdata = bulkdata.replace('b <tdstyle="color:yellow">',"")
    #Get rid of remaining html
    bulkdata = bulkdata.replace('<tdstyle="color:yellow">',"")
    #Clear trailing character
    bulkdata = bulkdata.replace(" '","")
    #Clear the word mins or min from times
    bulkdata = bulkdata.replace("mins","")
    bulkdata = bulkdata.replace("min","")
    
    #Split at whitespace into a list
    bulkdata = bulkdata.split()
    #Set up hour and minute variables. These need to be reset every loop because time will change
    hour = None
    minute = None
    
    #Test for zero entries
    if len(bulkdata) < 3 : return None
        
    #Load into a dictionary
    for l in range(len(bulkdata)/3):
        buses[l] = {}
        buses[l]["service"]= bulkdata[l*3 + 0]
        buses[l]["destination"]= bulkdata[l*3 + 1]
        buses[l]["time"]= bulkdata[l*3 + 2]
        
        #Look for buses that are marked Due and set time to 0
        if buses[l]["time"] is "Due": buses[l]["time"] = "0" #Handle as a string for now. We convert to integers later
        
        #Look for estimated times in format hh:mm rather than tracked times in format mm
        if ":" in buses[l]["time"]:
            #Check if we've got hour and minute already
            if hour is None and minute is None:
                #Find the time online
                timeresponse = await aiohttp.request("GET","http://just-the-time.appspot.com")
                thetime = await timeresponse.read()
                #Extract hour and minute
                hour = int(re.search("(\d\d)[:]",thetime).group(1))
                minute = int(re.search("[:](\d\d)[:]",thetime).group(1))
                
            #Replace the estimated time
            buses[l]["time"] = 60 * (int(re.search("(\d\d)[:]",bulkdata[l*3 + 2]).group(1)) - hour)
            buses[l]["time"] = buses[l]["time"] + int(re.search("[:](\d\d)",bulkdata[l*3 + 2]).group(1)) - minute
                        
            #Make it show blue
            buses[l]["colour"] = (0, 0 , initialbrightness)
        else:
            #Make it show green
            buses[l]["colour"] = (0, initialbrightness , 0)
        
        #Convert times to integers
        buses[l]["time"] = int(buses[l]["time"])
        
        #Replace colour of buses that are within a few minutes with red
        if buses[l]["time"] < 5:
            buses[l]["colour"] = (initialbrightness, 0 , 0)
            
    global busdata
    busdata = buses
    
    

async def led_output():
    global busdata
    buses = busdata # Take a local copy of the global variable here, so in the loop it doesn't get updated if get_buses returns before this routine finishes
    
    for i in range(50): #Looping 50 times, dimming by a hundredth each loop. Ends up half bright by end of loop
        
        #Adding in the home stop. This should not be in busdata so it will not get faded. Making it flash also
        if i % 2 == 0:
            np[(first_stop_offset - 1)] = (75 , 0 , 75) #Purple
        else:
            np[(first_stop_offset - 1)] = (85 , 64 , 0) #Orange
        
        for bus in buses: #Filter out buses that are wrong number or too far away, then write the buses
            if (buses[bus]["time"] + first_stop_offset) < pixelcount and buses[bus]["service"] in relevant_routes:
                np[(buses[bus]["time"] + first_stop_offset)] = buses[bus]["colour"]
        np.write()
        
        #Fades by diminishing the colour intensity value every cycle
        for bus in buses:
            templist = []
            templist = list(buses[bus]["colour"])
            for i in range(len(templist)):
                if templist[i] != 0: templist[i] = int(templist[i] - (initialbrightness/100))
            buses[bus]["colour"] = tuple(templist)
            
        await asyncio.sleep_ms(400) #400 x 50 loops = 20 seconds. Equivalent to delay time in snore()

async def snore():
    await asyncio.sleep(20)#Make it cycle only once every 20 seconds

async def main():
    await asyncio.gather(scroll(np), get_buses())
        
    while True:
        await asyncio.create_task(clear(np))
        await asyncio.gather(led_output(), get_buses(), snore()) 
        
        
        
        
    
    
        

connect_internet()
asyncio.run(clear(np))
asyncio.run(main())
