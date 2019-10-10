# TODO delete history function
# TODO export to xml/csv file

import pygame
import os
import sqlite3
import traceback
import platform
from pygame.locals import *
from datetime import datetime
import time

os.environ["SDL_FBDEV"] = "/dev/fb1"

WHITE = 255, 255, 255
GREEN = 0, 255, 0
BGREEN = 0, 128, 0
BLACK = 0, 0, 0
BLUE = 0, 0, 255
RED = 255, 0, 0

# D0 for Hall sensor
GPIO1 = 28


class App:
    def __init__(self):

        self.GPIO1_state = 0
        self.start = 0
        self.speed = 0
        self.avgSpeed = 0

        self.conn = sqlite3.connect("bike.db")
        self.cursor = self.conn.cursor()

        # SQL Fisrt run
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS trips(
            id INTEGER PRIMARY KEY,
            time INTEGER,
            date TEXT,
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
        self.conn.commit()
        # self.cursor.execute("""INSERT OR IGNORE INTO trips VALUES(1, 1234, 4567, 12.34, 0, 0, 0, 0)""")
        # self.cursor.execute("""INSERT OR IGNORE INTO trips VALUES(2, 7897, 4557, 22.34, 0, 0, 0, 0)""")
        # self.cursor.execute("""INSERT OR IGNORE INTO trips VALUES(3, 1448, 7887, 33.34, 0, 0, 0, 0)""")

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
        self.calib_x_gain = 1
        self.calib_x_offset = 0
        self.calib_y_gain = 1
        self.calib_y_offset = 0

        # GPIO for hall sensors
        if platform.system() == 'Linux':
            GPIO.setmode(GPIO.BCM)

            # Set Switch GPIO as input
            # Pull high by default
            GPIO.setup(GPIO1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(GPIO1, GPIO.BOTH, callback=self.sensorCallback, bouncetime=200)
            # sensorCallback(GPIO1)

    def sensorCallback(self, channel):
        # Called if sensor output changes
        if GPIO.input(channel):
            self.GPIO1_state = 1
        else:
            # Magnet
            self.getSpeed()

    def quit(self):
        self._running = False

    def on_init(self):
        pygame.init()
        self._display_surf = pygame.display.set_mode(self.size, pygame.HWSURFACE | pygame.DOUBLEBUF)
        self._running = True

        # Get max trip id to start with
        self.tripId = 1
        sql = "SELECT count(*) FROM trips"
        self.cursor.execute(sql)
        row = self.cursor.fetchone()
        self.tripId = row[0]

        self.isStart = 0
        self.labelStartStop = "START"
        self.GPIO1_state = 0

        # fetch cadence settings
        sql = "SELECT useCadence FROM Settings where id = 1"
        self.cursor.execute(sql)
        self.useCadence = self.cursor.fetchone()

        return True;

    def button(self, msg, sz, ic, ac, action=None, align='center'):
        x, y, w, h = sz

        mouse = pygame.mouse.get_pos()
        mx = round(mouse[0] * self.calib_x_gain + self.calib_x_offset)
        my = round(mouse[1] * self.calib_y_gain + self.calib_y_offset)

        # print(str(mx)+":"+str(mouse[0]))

        click = pygame.mouse.get_pressed()
        if x + w > mx > x and y + h > my > y:
            pygame.draw.rect(self._display_surf, ac, (x, y, w, h))
            if click[0] == 1 and action is not None:
                action()
        else:
            pygame.draw.rect(self._display_surf, ic, (x, y, w, h))

        font = pygame.font.Font(None, 35)
        label = font.render(msg, 1, WHITE)
        #text_rect = label.get_rect(center=(x + (w / 2), y + (h / 2)))
        if align=='center':
            text_rect = label.get_rect(center=(x + (w / 2), y + (h / 2)))
        elif align =='right':
            text_rect = label.get_rect(center=(x + 5, y + (h / 2)))
        else:
            text_rect = label.get_rect(center=(x + (w / 2), y + (h / 2)))

        self._display_surf.blit(label, text_rect)

    def on_event(self, event):
        if event.type == pygame.QUIT:
            self._running = False

        if event.type == pygame.USEREVENT:
            self.time = self.time + 1

        if event.type == pygame.KEYDOWN:
            pressed = pygame.key.get_pressed()

            # imitate sensor passing for test
            if pressed[pygame.K_LCTRL]:
                self.getSpeed()

            if pressed[pygame.K_SPACE]:
                self.changeMenu()

            if pressed[pygame.K_RCTRL]:
                if self._mode == "MAIN":
                    self.startStop()
                else:
                    if self._mode == "LIST":
                        self.nextTrip()

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

        rectTime = pygame.draw.rect(self._display_surf, BLACK, (0, 0, 480, 320), 0)  # filled = 0

    def prevTrip(self):
        self.tripId = self.tripId - 1
        if self.tripId == 0:
            sql = "SELECT count(*) FROM trips"
            self.cursor.execute(sql)
            self.tripId = self.cursor.fetchone()[0]

    def nextTrip(self):
        count = 0

        sql = "SELECT count(*) FROM trips"
        self.cursor.execute(sql)
        all_rows = self.cursor.fetchall()
        for row in all_rows:
            count = row[0]

        self.tripId = self.tripId + 1

        if self.tripId > count:
            self.tripId = 1

    def startStop(self):
        if self.isStart == 1:
            pygame.time.set_timer(USEREVENT, 0)
            self.isStart = 0

            self.cursor.execute("""INSERT INTO trips (time, date) VALUES(:time, :date)""", {'time': self.time, 'date': datetime.today()})
            self.conn.commit()

            self.time = 0
            self.labelStartStop = "START"

        else:
            pygame.time.set_timer(USEREVENT, 1000)
            self.isStart = 1
            self.labelStartStop = "STOP"

    def getSpeed(self):
        done = time.time()
        elapsed = (done - self.start)  # sec
        rpm = 1 / (elapsed / 60)  # rpm

        dist = rpm * 2070  # mm
        # mm per min
        self.speed = dist / elapsed
        self.speed = round(self.speed / 1000 / 1000 * 60, 2)

        self.avgSpeed = self.avgSpeed + self.speed

        self.start = done

    def on_render(self):
        # Constant elements
        self.button("X", (450, 0, 30, 30), RED, RED, self.quit)
        self.button("Menu", (400, 290, 80, 30), GREEN, BGREEN, self.changeMenu)

        # MAIN
        if self._mode == "MAIN":
            self.button("TRIP", (0, 0, 80, 40), BLACK, BLACK)

            self.button("Time:", (103, 10, 78, 40), BLACK, BLACK)
            self.button(datetime.utcfromtimestamp(self.time).strftime("%H:%M:%S"), (185, 10, 132, 40),
                        BLACK, BLACK)

            self.button("Dist:", (117, 54, 65, 40), BLACK, BLACK)
            self.button("000.00 km", (185, 54, 157, 40), BLACK, BLACK, 'right')

            self.button("Speed:", (81, 105, 101, 40), BLACK, BLACK)
            self.button(str(self.speed), (185, 105, 167, 40), BLACK, BLACK)
            # valueSpeed = self.button("000.00 km/h",(204,105,167,40),BLACK,BLACK)

            self.button("Avg. Speed:", (11, 145, 171, 40), BLACK, BLACK)
            self.button("000.00 km/h", (204, 146, 167, 40), BLACK, BLACK)

            if self.useCadence == 1:
                self.button("Cad:", (113, 195, 67, 40), BLACK, BLACK)
                self.button("000.00 rpm", (232, 195, 125, 40), BLACK, BLACK)

                self.button("Avg. Cad:", (43, 235, 137, 40), BLACK, BLACK)
                self.button("000.00 rpm", (232, 235, 125, 40), BLACK, BLACK)

            # sql = "SELECT * FROM trips"
            # self.cursor.execute(sql)
            # labelSelect = font.render(str(self.cursor.fetchone()),1,WHITE)
            # self._display_surf.blit(labelSelect, (20, 60))

            self.button(self.labelStartStop, (0, 290, 80, 30), GREEN, BGREEN, self.startStop)

        # LIST
        if self._mode == "LIST":
            self.button("LIST", (0, 0, 80, 40), BLACK, BLACK)

            self.button("PREV", (0, 290, 80, 30), GREEN, BGREEN, self.prevTrip)
            self.button("NEXT", (80, 290, 80, 30), GREEN, BGREEN, self.nextTrip)

            self.button("#" + str(self.tripId), (120, 0, 80, 40), BLACK, BLACK)


            self.cursor = self.conn.cursor()
            self.conn.commit()
            sql = "SELECT time, date, avgSpeed, maxSpeed FROM trips where id=? order by date desc"
            self.cursor.execute(sql, (self.tripId,))
            all_rows = self.cursor.fetchall()
            for row in all_rows:
                self.button("Date:", (161, 54, 78, 40), BLACK, BLACK)
                self.button(row[1][0:11], (249, 54, 140, 40),
                            BLACK, BLACK)

                self.button("Time:", (158, 94, 78, 40), BLACK, BLACK)
                self.button(datetime.utcfromtimestamp(row[0]).strftime("%H:%M:%S"), (246, 94, 132, 40),
                            BLACK, BLACK)

                self.button("Dist:", (158, 134, 65, 40), BLACK, BLACK)
                self.button(str(0), (248, 134, 157, 40), BLACK, BLACK)

                self.button("Avg. Speed:", (67, 174, 171, 40), BLACK, BLACK)
                self.button(str(row[2]), (248, 174, 167, 40), BLACK, BLACK)

                self.button("Avg. Cad:", (101, 214, 137, 40), BLACK, BLACK)
                self.button(str(row[3]), (248, 214, 125, 40), BLACK, BLACK)
        # MENU
        if self._mode == "MENU":
            self.button("SETTINGS", (0, 0, 140, 40), BLACK, BLACK)

        pygame.display.update()

    def on_cleanup(self):
        pygame.quit()
        self.conn.close()

    def on_execute(self):
        if not self.on_init():
            self._running = False

        while (self._running):

            for event in pygame.event.get():
                self.on_event(event)
            self.on_loop()
            self.on_render()
        self.on_cleanup()


try:
    if platform.system() == 'Linux':
        import RPi.GPIO as GPIO
except Exception as ex:
    import RPi_emu.GPIO as GPIO

    tb_lines = traceback.format_exception(ex.__class__, ex, ex.__traceback__)
    print(tb_lines)

if __name__ == "__main__":
    theApp = App()
    theApp.on_execute()
