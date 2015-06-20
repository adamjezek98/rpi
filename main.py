# -*- coding: utf-8 -*-
"""
hlavni skript pro ovladani chlazeni, logovani dat na server
a v budouci verzi i v hlidani ve funkci alarmu

TODO:
 - pridat alarm
 - pridat notifikacni diody
        jednu pro informaci, ze se odesila a kontroluje teplota, druhou
        jako chybovou pro pripad, ze neco selze
 - vypis chyb nekam... teoreticky zkusit pripojit mensi LCDcko s
 logovanim provozu?
 - webove rozhrani pres django

 

"""
import os
import RPi.GPIO as GPIO
import time
import datetime
import collections
from w1thermsensor import W1ThermSensor
from LCD import Adafruit_CharLCD
lcd = Adafruit_CharLCD()
true, false = True, False
#nastaveni GPIO
GPIO.cleanup()
GPIO.setmode(GPIO.BOARD)
#GPIO.setwarnings(False)

#nastaveni vetraku

fanpin = 37
GPIO.setup(fanpin, GPIO.OUT) 

#indikacni ledky
#planovano
progressled = 31
errled = 32
GPIO.setup(progressled, GPIO.OUT)
GPIO.setup(errled, GPIO.OUT)

def init():
        
        global chyby
        chyby = []
       
        try:
                global ds18b20pokoj
                ds18b20pokoj = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, "0000062616a0")
        except:
                chyby.append("ds18b20 room error")
                
        try:
                global ds18b20venku
                ds18b20venku = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, "0000062778ed")
        except:
                chyby.append("ds18b20 outside error")
                
        try:
                global ds18b20zdroj
                ds18b20zdroj = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, "000006282e71")
        except:
                chyby.append("ds18b20 power source error")
                
        try:
                #priprava slozky v run
                os.popen("sudo mkdir /run/send_data")
                os.popen("sudo touch /run/send_data/rec.txt")        
        except:
                chyby.append("folder error")

        try:
                lcd.__init__(19, 13, [5, 6, 21, 20], GPIO)
                lcd.begin(16,2)
        except:
                chyby.append("LCD error")
        os.chdir('/home/pi/Desktop')
        return chyby
        
        





#################CHLAZENI##################

def getcputemp(): #teplota cpu
	res = os.popen('vcgencmd measure_temp').readline()
	return float((res.replace("temp=","").replace("'C\n","")))

def getPStemp(): #teplota zdroje
        try:
                return ds18b20zdroj.get_temperature()
        except:
                return "none"



def getmaxtemp(): #vrati nejvyssi teplotu
        teploty = []
        teploty.append(getcputemp())
        teploty.append(getPStemp())
        teplota = 0
        for temp in teploty:
                if(temp > teplota):
                        teplota = temp
        return temp
     


def chlazeni(): #podle teploty prepne chlazeni
        teplota = getmaxtemp()
        if(teplota  >= 45): #pri vyssi teplote zapne chlazeni
                GPIO.output(fanpin, True)
        if(teplota <=35): #pri poklesu teploty vypne
                GPIO.output(fanpin,False)
        if(teplota >= 75):
                os.popen('halt') #pro pripad nouze pri vysoke teplote vypne RPi

def switchfan(state):
        if state:
              GPIO.output(fanpin, True)
        else:
              GPIO.output(fanpin, False)

def hlidejteplotu(interval=30): #pouze pri vyvoji, nepouzivat ve finalnim reseni
        while True:
                chlazeni()
                print getmaxtemp()
                time.sleep(interval)
#################SENSORY###################
def getroomtemp():
        try:
                return ds18b20pokoj.get_temperature()
        except:
                return "none"

def getoutsidetemp():
        try:
                return ds18b20venku.get_temperature()
        except:
                return "none"


##################ODESILANI NA WEB##################

vystup="/run/send_data/rec.txt" #prijata data ze serveru

def fanstate(): #vrati stav chlazeni
        GPIO.setup(37, GPIO.OUT)
        if GPIO.input(37) == 1:
            return "on"
        else:
            return "off"

def gettime():
        temp = str(datetime.datetime.now()).split(".")[0]
        datum = temp.split(" ")[0].split("-")
        datum = str(datum[2]) + "." + str(datum[1]) + "."+str(datum[0])
        cas = temp.split(" ")[1]
        cas = cas.split(".")[0]
        return str(cas) + " " + str(datum)
                                                               
def getdataready():    #pripravi data do pole k odeslani
        data = {}       #pole dat pro odeslani na server
        data = collections.OrderedDict()
        data["cputemp"] = str(getcputemp())
        data["cas"] = gettime()    
        data["fan"] = str(fanstate())
        data["pstemp"] = str(getPStemp())
        data["pokojovateplota"] = str(getroomtemp())
        data["venkovniteplota"] = str(getoutsidetemp())
        
        return data
    

 
   

def senddata(): #prevede pole dat na url a posle je na server
        #a stahne prikazy a ulozi do souboru v promenne vystup
        data = getdataready()
        global url
        url = "parman.moxo.cz/datarec.php?" #url stranky pro prijem dat
        for key in data:
                url += str(key) +"=" + str(data[key]) + "\&"

        url = url.replace(" ", "%20")
        url = url.replace("\\\\&", "\\&")
        global prikaz
        prikaz = "wget --output-document=" + vystup + " "+ url
        print os.popen(prikaz).readline()
        return True




################################POVIDANI######################
def speak(text=""):
        com = "espeak  \"" + text + "\" 2>/dev/null"
        os.popen(com)

def saytemp(tep="out"):
        temp = ""
        if tep == "out":
                temp = "Outside temperature is "+  str(getoutsidetemp())
                temp += " degrees Celsius"
        elif tep == "cpu":
                temp = "Central processor unit temperature is" + str(getcputemp())
                temp += " degrees Celsius"
        elif tep == "ps":
                temp = "Power source temperature is" + str( getPStemp())
                temp += " degrees Celsius"
        elif tep == "in":
                temp = "Room temperature is" + str(getroomtemp())
                temp += " degrees Celsius"
                
        
        speak(temp)
        
        
def voicediag():
        datatrans = {"cputemp":"processor temperature read error", \
             "cas":"time", "fan":"get cooling state error", \
             "pstemp":"ds18b20 power source temperature sensor error", \
             "pokojovateplota":"ds18b20 room temperature sensor error", \
             "venkovniteplota":"ds18b20 outside temperature sensor error"}


        sensors = ["in", "out", "cpu", "ps"]        
        speak("Running voicediag");
        speak("Now is "+time.strftime("%H")+ " hours "+ time.strftime("%M") \
        + " minutes")
        
        speak("Temperatures")
        for sens in sensors:
                saytemp(sens)
        if fanstate() == "on":
                speak("Cooling is on")
        else:
                speak("Cooling is off")
                speak("Cooling isn't required now.")
        
        speak("Running internal scan. This could take a while. Please wait.")
        data = getdataready()
        if any( "none" in data[a] for a in data):
                speak("I found some errors. I will try to fix them. Please wait")
                init()
                speak("Trying to reinitialize nonfunctional sensors")
                data = getdataready()
                
                if any( "none" in data[a] for a in data):
                        errors = []
                        for err in chyby:
                                errors.append( str(err) + " ")
                        for a in data:
                                if data[a] == "none":
                                        errors.append( datatrans[a])
                        speak("I can't fix them. Founded errors are ")
                        for err in errors:
                                os.popen("espeak -g 15 -s 120 \" " + err + "\"")
                        speak("please, look at them")
                else:
                        speak("Successfully fixed")
        else:
                speak("No errors found.")
                              
                
              
              
        
        speak("Done. Have a nice day")


######################### LCD #######################

def jezdicizpravaL(text, rychlost=0.5, line=1, orez=0):
        text = (" "*16) + text
        lcd.setCursor(0,line)
        lcd.message(" "*16)
        for i in range(len(text)-orez):
                lcd.setCursor(0,line)
                lcd.message(" "*16)
                lcd.setCursor(0,line)
                lcd.message(text[i:i+16:])
                time.sleep(rychlost)
        lcd.setCursor(0,line)
        lcd.message(" "*16)

def loadbar(text, opak=5, rychlost=0.1, line=1, delka=16):
        lcd.setCursor(0,line)
        lcd.message(" "*16)
        lcd.setCursor(0,line)
        for i in range(opak):
                for col in range(delka):
                        lcd.setCursor(col, line)
                        lcd.message(text)
                        time.sleep(rychlost)
                        lcd.setCursor(col-1,line)
                        lcd.message(" ")
                for col in range(delka):
                        lcd.setCursor(delka-col, line)
                        lcd.message(text)
                        time.sleep(rychlost)
                        lcd.setCursor(delka-col,line)
                        lcd.message(" ")

def progbar(text, opak=5, rychlost=0.1, line=1, delka=16):
        lcd.setCursor(0,line)
        lcd.message(" "*16)
        lcd.setCursor(0,line)
        for i in range(opak):
                for col in range(delka):
                        lcd.setCursor(col, line)
                        lcd.message(text)
                        time.sleep(rychlost)
                for col in range(delka):
                        lcd.setCursor(delka-col, line)
                        lcd.message(" ")
                        time.sleep(rychlost)
                            
def lcdinfo(rychl=0.2):
        lcd.setCursor(0,1)
        lcd.message("Nacitam data...")
        data = getdataready()
        preklady = {"cputemp":"Teplota procesoru je", \
             "cas":"Aktualni cas je", "fan":"Chlazeni je", \
             "pstemp":"Teplota zdroje je ", \
             "pokojovateplota":"Pokojova teplota je", \
             "venkovniteplota":"Venkovni teplota je"}
        text = ""
        for dat in data:
                if dat in preklady:
                        text += preklady[dat] +" "+ data[dat] +" "
                else:
                        text += dat +" "+ data[dat] +" "
        jezdicizpravaL(text, rychlost=rychl, line=1)


print init()
GPIO.setmode(GPIO.BOARD)
