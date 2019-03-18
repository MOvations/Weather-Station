#!/usr/bin/python
"""
******************************************************************************
    Pi Temperature Station

    This is a Raspberry Pi project that measures weather data 
    (Current: temperature, humidity and pressure
    Future: Wind, rain) 
    
    It uses the Astro Pi Sense HAT, a DHT11, a DS18B20, and LDR sensors 
    
    it uploads the data to a various locations 
    (Current: Weather Underground weather PWS, a personal mySQL site, 
    Future: AWS, GCP)

    Future Work:
    Time-series forcasts 
    data comparitor
    Hard-reset via relay

******************************************************************************
"""
# might want to know why I need this... 
from __future__ import print_function

import datetime
import dht11
import glob
import os
import RPi.GPIO as GPIO
import sys
import time
import urllib2

from config import Config
from sense_hat import SenseHat
from urllib import urlencode

# ============================================================================
# For Reading the 7Q-Tek 18B20 Temperature sensor
# ============================================================================

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
 
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'
 
# ============================================================================
# CONSTANTS
# ============================================================================

# specifies how often to measure values from the Sense HAT (in minutes)
MEASUREMENT_INTERVAL = 1  # minutes
# Set to False when testing the code and/or hardware
# Set to True to enable upload of weather data to Weather Underground
WEATHER_UPLOAD = True
# the weather underground URL used to upload weather data
WU_URL = "http://weatherstation.wunderground.com/weatherstation/updateweatherstation.php"
# some string constants
SINGLE_HASH = "#"
HASHES = "################################################"
SLASH_N = "\n"

# constants used to display an up and down arrows plus bars
# modified from https://www.raspberrypi.org/learning/getting-started-with-the-sense-hat/worksheet/
# set up the colours (blue, red, empty)

# ============================================================================
# GPIO
# ============================================================================

# initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()

# read data using pin 26
instance = dht11.DHT11(pin=26)

# ============================================================================
# DEFINE DISPLAY VARIABLES
# ============================================================================

b = [0, 0, 255]     # blue
r = [255, 0, 0]     # red
g = [0, 255, 0]     # green
e = [0, 0, 0]       # empty
w = [255, 255, 255] # white

# DEFINE IMAGES

arrow_up = [
    e, e, e, g, g, e, e, e,
    e, e, g, g, g, g, e, e,
    e, g, g, g, g, g, g, e,
    g, g, e, g, g, e, g, g,
    g, e, e, g, g, e, e, g,
    e, e, e, g, g, e, e, e,
    e, e, e, g, g, e, e, e,
    e, e, e, g, g, e, e, e
]

arrow_down = [
    e, e, e, g, g, e, e, e,
    e, e, e, g, g, e, e, e,
    e, e, e, g, g, e, e, e,
    g, e, e, g, g, e, e, g,
    g, g, e, g, g, e, g, g,
    e, g, g, g, g, g, g, e,
    e, e, g, g, g, g, e, e,
    e, e, e, g, g, e, e, e
]

eq_bars = [
    e, e, e, e, e, e, e, e,
    e, w, w, w, w, w, w, e,
    e, w, w, w, w, w, w, e,    
    e, e, e, e, e, e, e, e,
    e, w, w, w, w, w, w, e,
    e, w, w, w, w, w, w, e,
    e, e, e, e, e, e, e, e,
    e, e, e, e, e, e, e, e
]

q_mark = [
    e, e, e, g, g, e, e, e,
    e, e, w, e, e, w, e, e,
    e, e, e, e, e, r, e, e,
    e, e, e, e, r, e, e, e,
    e, e, e, g, e, e, e, e,
    e, e, e, w, e, e, e, e,
    e, e, e, e, e, e, e, e,
    e, e, e, r, e, e, e, e
]

# ============================================================================
# FUNCTIONS
# ============================================================================

# Weather Station Upload / Download / log functions
def log_weather(temp_f, t_hum, t_press, pressure, humidity, t_cpu, t_dht, h_dht,
                        dew_pt_dht, t_tecf, dew_pt_tec):

    timestr = time.strftime("%Y%m%d")
    f_loc = "/home/pi/pi_weather_station/Logs/"
    f_name = f_loc + "log_weather-{}.log".format(timestr)

    with open(f_name, "a") as log:
        log.write("{}, {}, {}, {}, {}, {}%, {}, {}, {}%, {}, {}, {} \n".format(
            str(datetime.datetime.now()),temp_f, t_hum, t_press, pressure, 
            humidity, t_cpu, t_dht, h_dht, dew_pt_dht, t_tecf, dew_pt_tec)) 
      
    return


def upload_weather(wu_station_id, wu_station_key, temp_f, dew_ptf, 
                    humidity, pressure):
    """ Upload Data to Weather Underground """
    # From http://wiki.wunderground.com/index.php/PWS_-_Upload_Protocol
    # link is broken, some bindings can be found here:
    # https://www.openhab.org/addons/bindings/weatherunderground/
    print("Uploading data to Weather Underground")
    # build a weather data object
    weather_data = {
        "action": "updateraw",
        "ID": wu_station_id,
        "PASSWORD": wu_station_key,
        "dateutc": "now",
        "tempf": str(temp_f),
        "dewPtF": str(dew_ptf),
        "humidity": str(humidity),
        "baromin": str(pressure),
    }
    try:
        upload_url = WU_URL + "?" + urlencode(weather_data)
        response = urllib2.urlopen(upload_url)
        html = response.read()
        print("Server response:", html)
        # do something
        response.close()  # best practice to close the file
    except:
        print("Exception:", sys.exc_info()[0], SLASH_N)
                    

# Display manipulations
def reset_pixels(pixelx):
    cell = []
    px = []
    for i in pixelx:
        for j in i:
            cell.append(int(j))
        px.append(cell[-3:])
    return(px)

def next_colour(pix):
    r = pix[0]
    g = pix[1]
    b = pix[2]

    # Simple adder, placehold for more complex operations
    if (r == 255):
        r = 0
    else:
        r += 1
    if (g == 255):
        g = 0
    else:
        g += 1
    if (b == 255):
        b = 0
    else:
        b += 1

    pix[0] = r
    pix[1] = g
    pix[2] = b

    return (pix)

def rot_display():
    time.sleep(1)
    sense.set_rotation(90)
    time.sleep(1)
    sense.set_rotation(180)
    time.sleep(1)
    sense.set_rotation(270)
    time.sleep(1)
    sense.set_rotation(0)
    return 

# Climate Calculations
def rht_to_dp(temp, rh):
    """ Takes Relative Humidity & Temperature then coverts to Dew Point """
    # from https://en.wikipedia.org/wiki/Dew_point
    dp = temp - (0.36 * (100 - rh))
    # Check Calc
    # print("Temp: {} RH: {} DP: {}".format(temp, rh, dp))
    return dp

def degc_to_degf(input_temp):
    """ Convert input temp from Celcius to Fahrenheit """
    return (input_temp * 1.8) + 32

def pa_to_inches(pressure_in_pa):
    """ Convert pressure in Pascal to mmHg """
    pressure_in_inches_of_m = pressure_in_pa * 0.02953
    return pressure_in_inches_of_m

def mm_to_inches(rainfall_in_mm):
    """ Convert rainfall in millimeters to Inches """
    rainfall_in_inches = rainfall_in_mm * 0.0393701
    return rainfall_in_inches

def khm_to_mph(speed_in_kph):
    """ Convert speed in kph to MPH  """
    # for wind speed, when I find a way to measure
    speed_in_mph = speed_in_kph * 0.621371
    return speed_in_mph

# Sensor Data Collection and Calculations

# One-wire connection, for 18B20 Temperature Sensor
def read_w1_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
 
def read_w1_temp():
    lines = read_w1_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_w1_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

def get_cpu_temp():
    # 'borrowed' from https://www.raspberrypi.org/forums/viewtopic.php?f=104&t=111457
    # executes a command at the OS to pull in the CPU temperature
    res = os.popen('vcgencmd measure_temp').readline()
    return float(res.replace("temp=", "").replace("'C\n", ""))


# use moving average to smooth readings
def get_smooth(x):
    # do we have the t object?
    if not hasattr(get_smooth, "t"):
        # then create it
        get_smooth.t = [x, x, x]
    # manage the rolling previous values
    # should be a way to do this part cleaner...
    get_smooth.t[2] = get_smooth.t[1]
    get_smooth.t[1] = get_smooth.t[0]
    get_smooth.t[0] = x
    # average the three last temperatures
    xs = (get_smooth.t[0] + get_smooth.t[1] + get_smooth.t[2]) / 3
    # print("3 temps to ave: {}, {}, {}".format(
    #     get_smooth.t[0], get_smooth.t[1], get_smooth.t[2]))
    # print("With result: {}".format(xs))
    return xs


def get_sense_temp():
    # ====================================================================
    # Unfortunately, getting an accurate temperature reading from the
    # Sense HAT is improbable, see here:
    # https://www.raspberrypi.org/forums/viewtopic.php?f=104&t=111457
    # so we'll have to do some approximation of the actual temp
    # taking CPU temp into account. The Pi foundation recommended
    # using the following:
    # http://yaab-arduino.blogspot.co.uk/2016/08/accurate-temperature-reading-sensehat.html
    # ====================================================================
    # First, get temp readings from both sensors
    t1 = sense.get_temperature_from_humidity()
    t2 = sense.get_temperature_from_pressure()
    # t becomes the average of the temperatures from both sensors
    
    #currently t humidity doesn't work, thus:
    t = t2
    #t = (t1 + t2) / 2
    # Now, grab the CPU temperature
    t_cpu = get_cpu_temp()
    # Calculate the 'real' temperature compensating for CPU heating
    t_corr = t - ((t_cpu - t) / 1.5)
    # Finally, average out that value across the last three readings
    t_corr = get_smooth(t_corr)
    # convoluted, right?
    # Return the calculated temperature

    return t_corr

def get_ext_sensor_data():

    return TBD 

def main():

    # Global needed???    
    global last_temp

    # Initialize some variables (in case of error):
    t_dht = []
    h_dht = []
    dew_pt_dht = []
    dew_pt_tec = []
    current_minute = datetime.datetime.now().minute

    # initialize the lastMinute variable to the current time to start
    last_minute = datetime.datetime.now().minute
    # on startup, just use the previous minute as lastMinute
    last_minute -= 1
    if last_minute == 0:
        last_minute = 59

    # infinite loop to continuously check weather values
    while 1:
        # The temp measurement smoothing algorithm's accuracy is based
        # on frequent measurements, so we'll take measurements every 5 seconds
        # but only upload on measurement_interval
        current_second = datetime.datetime.now().second

        # restrict measurement frequency to 5sec, should be good for all connected devices
        # are we at the top of the minute or at a 5 second interval?
        if (current_second == 0) or ((current_second % 5) == 0):
            # ========================================================
            # read values from the Sense HAT
            # ========================================================
            # Calculate the temperature. The get_sense_temp function 'adjusts' the recorded temperature adjusted for the
            # current processor temp in order to accommodate any temperature leakage from the processor to
            # the Sense HAT's sensor. This happens when the Sense HAT is mounted on the Pi in a case.
            # If you've mounted the Sense HAT outside of the Raspberry Pi case, then you don't need that
            # calculation. So, when the Sense HAT is external, replace the following line (comment it out  with a #)
            # calc_temp = get_sense_temp()
            # with the following line (uncomment it, remove the # at the line start)
            # calc_temp = sense.get_sense_temperature_from_pressure()
            # or the following line (each will work)
            # calc_temp = sense.get_sense_temperature_from_humidity()
            # ========================================================
            # At this point, we should have an accurate temperature, so lets use the recorded (or calculated)
            
            # Sense HAT temps, pressure, humidity
            t_hum = degc_to_degf(sense.get_temperature_from_humidity())
            t_press = degc_to_degf(sense.get_temperature_from_pressure()) 
            calc_temp = get_sense_temp()
            temp_c = round(calc_temp, 1)
            temp_f = round(degc_to_degf(calc_temp), 1)
            humidity = sense.get_humidity()
            t_cpu = degc_to_degf(get_cpu_temp())

            # Tek 18B20 Temp:    
            t_tecf = degc_to_degf(read_w1_temp())

            # DHT11 Temp & Humidity:
            result = instance.read()
            if result.is_valid():
                t_dht = degc_to_degf(result.temperature)
                h_dht = result.humidity
                dew_pt_dht = rht_to_dp(t_dht, h_dht)
                dew_pt_tec = rht_to_dp(t_tecf, h_dht)
                
            # convert pressure from millibars to inHg before posting
            pressure = round(sense.get_pressure() * 0.0295300, 1)
            print("Measurement Time:      {}".format(str(datetime.datetime.now())))
            print("Sense Temp (calc):     {} ".format(temp_f)) 
            print("Sense Temp (hum):      {} ".format(t_hum))
            print("Sense Temp (press):    {} ".format(t_press))   
            print("Sense Pressure (inHg): {} ".format(pressure)) 
            print("Sense Humidity:        {} % ".format(humidity))
            print("CPU Temp:              {} ".format(t_cpu))
            print("DHT11 Temp:            {} ".format(t_dht))
            print("DHT11 Humidity:        {} % ".format(h_dht))
            print("DHT11 Dew Point:       {} ".format(dew_pt_dht))
            print("Tek38B10 Temp:         {} ".format(t_tecf))
            print("Tek38B10 Dew Point:    {} ".format(dew_pt_tec))

            sense.low_light = True
            if ((current_minute % 2) == 0):
                sense.show_message("%sF" %round(((t_tecf+temp_f)/2),1), text_colour=r)
                sense.show_message("%s%%" %h_dht, text_colour=g)
                time.sleep(5)
            
            else:
                sense.show_message("%sF" %round(((t_tecf+temp_f)/2),1), text_colour=w)
                sense.show_message("%s%%" %h_dht, text_colour=g)
                time.sleep(5)

            # Assine the bew dew point calculation for upload
            dew_ptf = dew_pt_tec
            # get the current minute
            current_minute = datetime.datetime.now().minute
            # is it the same minute as the last time we checked?
            if current_minute != last_minute:
                # reset last_minute to the current_minute
                last_minute = current_minute
                # is minute zero, or divisible by 10?
                # we're only going to take measurements every MEASUREMENT_INTERVAL minutes
                if (current_minute == 0) or ((current_minute % MEASUREMENT_INTERVAL) == 0):
                    # get the reading timestamp
                    now = datetime.datetime.now()
                    print("\n%d minute mark (%d @ %s)" % (MEASUREMENT_INTERVAL, current_minute, str(now)))
                    
                    # did the temperature go up or down?
                    # Better to compare floats with a tolerances
                    tolerance = 0.2
                    if abs(last_temp - t_tecf) >= tolerance:
                        if (last_temp - t_tecf) < 0:
                            # display a down arrow
                            sense.set_pixels(arrow_down)			    
                            # rot_display() 
                            
                            #time.sleep(5)
			                #sense.show_message("%sF" %t_tecf, text_colour=b)
                            

                        else:
                            # display a up arrow
			                #sense.show_message("%sF" %t_tecf, text_colour=r)
                            # time.sleep(5)
                            sense.set_pixels(arrow_up)
                            # rot_display() 
			                

                    else:
                        # temperature stayed the same
                        # display red and blue bars
                        #sense.show_message("%sF" %t_tecf, text_colour=w)
                        # time.sleep(5)
                        sense.set_pixels(eq_bars)
                        rot_display()
                        # rot_display()

                    # set last_temp to the current temperature before we measure again
                    last_temp = t_tecf

                    # is weather upload enabled (True)?
                    if WEATHER_UPLOAD:
                        upload_weather(wu_station_id, 
                                        wu_station_key, 
                                        temp_f, dew_ptf, 
                                        h_dht, pressure)
                               
                        log_weather(temp_f, t_hum, t_press, pressure, humidity, 
                                    t_cpu, t_dht, h_dht, dew_pt_dht, t_tecf, dew_pt_tec)

                    else:
                        print("Skipping Weather Underground upload")

        # wait a second then check again
        # You can always increase the sleep value below to check less often
        time.sleep(1)  # this should never happen since the above is an infinite loop

    print("Leaving main()")


# ============================================================================
# here's where we start checking stuff
# ============================================================================
print(SLASH_N + HASHES)
print(SINGLE_HASH, "Pi Weather Station                          ", SINGLE_HASH)
print(SINGLE_HASH, "with Sense HAT, DHT11, and 18B20 sensors    ", SINGLE_HASH)
print(SINGLE_HASH, "By Mark H Oliver                            ", SINGLE_HASH)
print(HASHES)

# make sure we don't have a MEASUREMENT_INTERVAL > 60
if (MEASUREMENT_INTERVAL is None) or (MEASUREMENT_INTERVAL > 60):
    print("The application's 'MEASUREMENT_INTERVAL' cannot be empty or greater than 60")
    sys.exit(1)

# ============================================================================
#  Read Weather Underground Configuration Parameters
# ============================================================================
print("\nInitializing Weather Underground configuration")
wu_station_id = Config.STATION_ID
wu_station_key = Config.STATION_KEY
if (wu_station_id is None) or (wu_station_key is None):
    print("Missing values from the Weather Underground configuration file\n")
    sys.exit(1)

# we made it this far, so it must have worked...
print("Successfully read Weather Underground configuration values")
print("Station ID:", wu_station_id)
# print("Station key:", wu_station_key)

# ============================================================================
# initialize the Sense HAT object
# ============================================================================
try:
    print("Initializing the Sense HAT client")
    sense = SenseHat()
    # sense.set_rotation(180)
    # then write some text to the Sense HAT's 'screen'
    sense.show_message("Init", text_colour=[255, 255, 0], back_colour=[0, 0, 127])
    # clear the screen
    sense.clear()
    # get the current temp to use when checking the previous measurement
    last_temp = round(degc_to_degf(read_w1_temp()), 1)
    print("Current temperature reading:", last_temp)
except:
    print("Unable to initialize the Sense HAT library:", sys.exc_info()[0])
    sys.exit(1)

print("Initialization complete!")

# Now see what we're supposed to do next
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting application\n")
        sys.exit(0)
