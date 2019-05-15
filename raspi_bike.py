import pygame, os
import sqlite3
import RPi.GPIO as GPIO
from pygame.locals import *
from datetime import datetime

os.environ["SDL_FBDEV"] = "/dev/fb0"

WHITE = 255,255,255
GREEN = 0,255,0
BGREEN= 0,128,0
BLACK = 0,0,0
BLUE  = 0,0,255
RED   = 255,0,0

GPIO1 = 28

class App:
    def __init__(self):

        self.conn = sqlite3.connect("bike.db")
        self.cursor = self.conn.cursor()

        # SQL Fisrt run
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS trips(
            id INTEGER PRIMARY KEY,
            time INTEGER,
            date INTEGER,
            distance REAL,
            avgSpeed REAL,
            maxSpeed REAL,
            avgCadence REAL,
            maxCadence REAL)""")
        
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS Settings(
            id INTEGER PRIMARY KEY,
            wheelSize INTEGER,
            useCadence INTEGER,
            lastDate INTEGER)""")

        self.cursor.execute("""INSERT OR IGNORE INTO Settings VALUES(1, 2120, 0, julianday('2019-04-19'))""")

        #self.cursor.execute("""INSERT OR IGNORE INTO trips VALUES(1, 1234, 4567, 12.34, 0, 0, 0, 0)""")
        #self.cursor.execute("""INSERT OR IGNORE INTO trips VALUES(2, 7897, 4557, 22.34, 0, 0, 0, 0)""")
        #self.cursor.execute("""INSERT OR IGNORE INTO trips VALUES(3, 1448, 7887, 33.34, 0, 0, 0, 0)""")

        ###
        
        self._running = True
        self._mode = "MAIN"
        self._display_surf = None
        self.time = 0
        self.size = self.weight, self.height = 480, 320

        self.calib_x_gain = -0.132
        self.calib_x_offset = 520
        self.calib_y_gain = 0.2075
        self.calib_y_offset = -20

        # test zero calibration
        #self.calib_x_gain = 1
        #self.calib_x_offset = 0
        #self.calib_y_gain = 1
        #self.calib_y_offset = 0

        # GPIO for hall sensors
        GPIO.setmode(GPIO.BCM)

        # Set Switch GPIO as input
        # Pull high by default
        GPIO.setup(GPIO1 , GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(GPIO1, GPIO.BOTH, callback=self.sensorCallback, bouncetime=200)
        sensorCallback(GPIO1)

    def sensorCallback(self, channel):
      # Called if sensor output changes
      if GPIO.input(channel):
        self.GPIO1_state = 1
      else:
        # Magnet
        self.GPIO1_state = 0
        
    def test(self):
        print("TEST")

    def quit(self):
        self._running = False

    def on_init(self):
        pygame.init()
        self._display_surf = pygame.display.set_mode(self.size, pygame.HWSURFACE | pygame.DOUBLEBUF)
        self._running = True
        self.tripId = 1
        self.isStart = 0
        self.labelStartStop = "START"

        #fetch cadence settings
        sql = "SELECT useCadence FROM Settings where id = 1"
        self.cursor.execute(sql)
        self.useCadence = self.cursor.fetchone()

    def button(self,msg,sz,ic,ac,action=None):
        x,y,w,h = sz

        mouse = pygame.mouse.get_pos()
        my = mouse[1] * self.calib_y_gain + self.calib_y_offset
        mx = mouse[0] * self.calib_x_gain + self.calib_x_offset

        click = pygame.mouse.get_pressed()
        if x+w > mx > x and y+h > my > y:
            pygame.draw.rect(self._display_surf, ac,(x,y,w,h))
            if click[0] == 1 and action != None:
                action()         
        else:
            pygame.draw.rect(self._display_surf, ic,(x,y,w,h))

        font = pygame.font.Font(None,35)
        label = font.render(msg,1,WHITE)
        text_rect = label.get_rect(center=(x+(w/2), y+(h/2)))
        self._display_surf.blit(label, text_rect)
        
    def on_event(self, event):        
        if event.type == pygame.QUIT:
            self._running = False

        if event.type == pygame.USEREVENT:
            self.time = self.time + 1;
                
    def on_loop(self):
        pygame.time.delay(100)
        
    def changeMenu(self):
        if self._mode == "MAIN":
            self._mode = "LIST"
        else:  
            if self._mode == "LIST":
                self._mode = "MENU"
            else:    
                if self._mode == "MENU":
                    self._mode = "MAIN"

        rectTime = pygame.draw.rect(self._display_surf, BLACK, (0,0,480,320),0) #filled = 0

    def prevTrip(self):
        if self.tripId > 1:
            self.tripId = self.tripId-1

    def nextTrip(self):
        self.tripId = self.tripId+1

    def startStop(self):
        if self.isStart == 1:
            pygame.time.set_timer(USEREVENT, 0)
            self.isStart = 0

            self.cursor.execute("""INSERT INTO trips (time) VALUES(:time)""", {'time':self.time})

            self.time = 0
            self.labelStartStop = "START"
          
        else:
            pygame.time.set_timer(USEREVENT, 1000)
            self.isStart = 1
            self.labelStartStop = "STOP"

    def on_render(self):
        #Constant elements
        buttonX = self.button("X",(450,0,30,30),RED,RED,self.quit)
        buttonMenu = self.button("Menu",(400,290,80,30),GREEN,BGREEN,self.changeMenu)

        # MAIN
        if self._mode == "MAIN":
            buttonStart = self.button("TRIP",(0,0,80,40),BLACK,BLACK)
        
            labelTime = self.button("Time:",(103,10,78,40),BLACK,BLACK)
            valueTime = self.button(datetime.utcfromtimestamp(self.time).strftime("%H:%M:%S"),(181,10,132,40),BLACK,BLACK)

            labelDist = self.button("Dist:",(117,54,65,40),BLACK,BLACK)
            valueDist = self.button("000.00 km",(184,54,157,40),BLACK,BLACK)

            labelSpeed = self.button("Speed:",(81,105,101,40),BLACK,BLACK)
            valueSpeed = self.button(str(self.GPIO1_state),(204,105,167,40),BLACK,BLACK)
            #valueSpeed = self.button("000.00 km/h",(204,105,167,40),BLACK,BLACK)

            labelAvgSpeed = self.button("Avg. Speed:",(11,145,171,40),BLACK,BLACK)
            valueAvgSpeed = self.button("000.00 km/h",(204,146,167,40),BLACK,BLACK)

            if self.useCadence==1:
                labelCadence = self.button("Cad:",(113,195,67,40),BLACK,BLACK)
                valueCadence = self.button("000.00 rpm",(232,195,125,40),BLACK,BLACK)

                labelAvgCadence = self.button("Avg. Cad:",(43,235,137,40),BLACK,BLACK)
                valueAvgCadence = self.button("000.00 rpm",(232,235,125,40),BLACK,BLACK)

            #sql = "SELECT * FROM trips"
            #self.cursor.execute(sql)
            #labelSelect = font.render(str(self.cursor.fetchone()),1,WHITE)
            #self._display_surf.blit(labelSelect, (20, 60))

            buttonStart = self.button(self.labelStartStop,(0,290,80,30),GREEN,BGREEN,self.startStop)
            
        # LIST
        if self._mode == "LIST":            
            labelPage = self.button("LIST",(0,0,80,40),BLACK,BLACK)
            
            labelPage = self.button("PREV",(0,290,80,30),GREEN,BGREEN,self.prevTrip)
            labelPage = self.button("NEXT",(80,290,80,30),GREEN,BGREEN,self.nextTrip)

            labelId = self.button("#"+str(self.tripId),(120,0,80,40),BLACK,BLACK)

            sql = "SELECT time, date, avgSpeed, maxSpeed FROM trips where id=?"
            self.cursor.execute(sql, (self.tripId,))
            all_rows = self.cursor.fetchall()
            for row in all_rows:

                labelTime = self.button("Time:",(221,49,78,40),BLACK,BLACK)
                valueTime = self.button(datetime.utcfromtimestamp(row[0]).strftime("%H:%M:%S"),(309,49,132,40),BLACK,BLACK)
            
                labelTime = self.button("Dist:",(213,99,65,40),BLACK,BLACK)
                valueTime = self.button(str(row[1]),(288,99,157,40),BLACK,BLACK)

                labelTime = self.button("Avg. Speed:",(107,139,171,40),BLACK,BLACK)
                valueTime = self.button(str(row[2]),(288,139,167,40),BLACK,BLACK)

                labelTime = self.button("Avg. Cad:",(141,179,137,40),BLACK,BLACK)
                valueTime = self.button(str(row[3]),(288,179,125,40),BLACK,BLACK)
       # MENU
        if self._mode == "MENU":
            buttonStart = self.button("SETTINGS",(0,0,140,40),BLACK,BLACK)
      
        pygame.display.update() 
                
    def on_cleanup(self):
        pygame.quit()
        self.conn.close()
 
    def on_execute(self):
        if self.on_init() == False:
            self._running = False
        
        pygame.time.set_timer(USEREVENT, 0)

        font = pygame.font.Font(None, 35)

        #rectExit = pygame.draw.rect(self._display_surf, RED, (610,0,640,30),0) #filled = 0
        #buttonExit = font.render("X",1,WHITE)
        #self._display_surf.blit(buttonExit, (615,5))

        #rectExit = pygame.draw.rect(self._display_surf, GREEN, (540,360,640,400),0) #filled = 0
        #buttonMenu = font.render("Menu",1,WHITE)
        #self._display_surf.blit(buttonMenu, (550,370))

        while( self._running ):

            for event in pygame.event.get():
                self.on_event(event)
            self.on_loop()
            self.on_render()
        self.on_cleanup()

if __name__ == "__main__" :
    theApp = App()
    theApp.on_execute()
    
