import badger2040
import time

__all__ = ["App","AbstractScreen","NO_UPDATE"]

""" Returned from OnSleep to indicate the screen does not need to update"""
NO_UPDATE = -1

WHITE = 15
BLACK = 0

class AbstractScreen():
    def __init__(self,app):
        self.app = app
        self.badger = app.badger

    def onSleep(self,wasVisible,willBeVisible):
        return NO_UPDATE

    def drawAll(self):
        pass

class App():
    """An App, a system for showing screens to the user and handling their button presses. Apps are
    designed to be driven by user input and not designed (yet) for running background tasks.
    """
    BUTTONS = {
        "a":badger2040.BUTTON_A,
        "b":badger2040.BUTTON_B,
        "c":badger2040.BUTTON_C,
        "up":badger2040.BUTTON_UP,
        "down":badger2040.BUTTON_DOWN,
        "user":badger2040.BUTTON_USER,
    }

    def __init__(self,badger,*,timeToSleep=30,ledOff=85,ledLow=170,ledHigh=255):
        """Create a new app, for more on apps see the help on the type.

        Args:
            badger (Badger2040): Badger instance to draw to
            timeToSleep (int, optional): Number of seconds after the last input before the badger sleeps. Defaults to 30.
            ledOff (int, optional): Brightness of the LED whilst sleeping, not on battery power the LED is off while sleeping. Defaults to 85.
            ledLow (int, optional): Brightness of the LED while the app is idle and can accept user input. Defaults to 170.
            ledHigh (int, optional): Brightness of the LED while the app is active and processing. Defaults to 255.
        """
        self.badger = badger
        self.timeToSleep = timeToSleep
        self.ledOff = ledOff
        self.ledLow = ledLow
        self.ledHigh = ledHigh
        
        self.badger.led(self.ledHigh)
        self.active = None
        self.nextUpdateSpeed = None
        self.nextUpdateAt = None
        self.sleepAt = time.time()+timeToSleep
        self.returnTo = None
    
    def queueUpdate(self, delay, speed):
        """Queues a screen update, the actual update is done after user inputs are handled in the
        main loop. If multiple updates are queued at once then the next update will be as as early
        as the earliest one asks for, and as slow as the slowest one asks for.
        This lets diffrent draw methods specify how fast/thoroughly they need an update done without
        affecting each other.

        Args:
            delay (float): delay, in seconds, until the screen updates
            speed (int): the speed at which the screen will update at
        """
        at = float(time.time()) + float(delay)
        if self.nextUpdateAt is None or at < self.nextUpdateAt:
            self.nextUpdateAt = at 
        if self.nextUpdateSpeed is None or speed < self.nextUpdateSpeed:
            self.nextUpdateSpeed = speed

    def getPressed(self):
        """Returns a series of key value pairs: the name of each button and if it is currently
        pressed down

        Returns:
            *(str,bool): A tuple of (str,bool)s
        """
        return (k for k,v in self.BUTTONS.items() if self.badger.pressed(v))

    def setScreen(self,screen,doUpdate = True):
        """Sets the current screen on the app, the current screen receives button press events. If
        the screen is already being shown nothing happens

        Args:
            screen (AbstractScreen): The screen to set to
            doUpdate (bool, optional): If the screen should be drawn immediately, the screen is only draw if it's not already being shown. Defaults to True.

        Returns:
            bool: True if the screen was set, False if it's already displayed
        """
        if self.active != screen:
            self.active = screen
            self.badger.pen(WHITE)
            self.badger.clear()
            self.badger.pen(BLACK)
            screen.drawAll()
            if doUpdate:
                self.queueUpdate(0,badger2040.UPDATE_NORMAL)
            return True
        return False

    def onSleep(self):
        """Called when the badger goes to sleep. Can be overridden to provide custom logic, by
        default it sets the screen back to self.returnTo (if it's set) and requests a screen update
        if needed.
        Note, you cannot queue up screen updates since we halt after this step, if you override this
        method and require the screen to be updated before sleeping, you need to return the update
        speed you need from it. If you don't need an update you must return NO_UPDATE (-1)

        Returns:
            int: The speed the screen should be updated at, or NO_UPDATE (-1) if none is needed
        """
        if self.returnTo is not None:
            prevScreen = self.active
            if self.setScreen(self.returnTo,doUpdate = False):
                self.active.onSleep(False,True)
                prevScreen.onSleep(True,False)
                return badger2040.UPDATE_NORMAL
            else:
                self.active.onSleep(True,True)
        return NO_UPDATE 

    def loop(self):
        """Runs a single instance of the processing loop, which does the following:
         1. Process user input, calling at most one of the `button_` methods on the active screen
         2. Update the screen, if needed
         3. Check to see if the badger should sleep, and do so if needed
        """
        buttons = tuple(self.getPressed())
        activated = False

        # Button Handling
        if self.active is not None:
            for b in buttons:
                f = getattr(self.active,f"button_{b}",None)
                if f is not None:
                    self.badger.led(self.ledHigh)
                    activated = True
                    f()
                    break
            if buttons:
                print("Loop action buttons",buttons)
                self.sleepAt = time.time()+self.timeToSleep
        
        # Screen Update handling
        if self.nextUpdateAt is not None and time.time() >= self.nextUpdateAt:
            print("Loop action update")
            self.badger.led(self.ledHigh)
            activated = True
            self.badger.update_speed(self.nextUpdateSpeed)
            self.badger.update()
            self.nextUpdateAt = None
            self.nextUpdateSpeed = None
        
        # If actioned, dim led
        if activated:
            print("Loop action clear")
            self.badger.led(self.ledLow)
            at = time.localtime(self.sleepAt)
            print(f"> Sleep will occur at {at[3]}:{at[4]}:{at[5]}")
            if self.nextUpdateAt is None:
                print(f"> No update is queued")
            else:
                at = time.localtime(self.nextUpdateAt)
                print(f"Update will occur at {at[3]}:{at[4]}:{at[5]}")

        # Put the badger to sleep and turn off the led,
        # if we are not waiting on an update, and it's been at least 30s
        if self.nextUpdateAt is None and time.time() >= self.sleepAt:
            print("Loop action sleep")
            preSleepUpdateSpeed = self.onSleep()
            if preSleepUpdateSpeed != NO_UPDATE:
                self.badger.update_speed(preSleepUpdateSpeed)
                self.badger.update()
            self.badger.led(self.ledOff)
            self.badger.halt()
            self.badger.led(self.ledLow)
    
    def runForever(self):
        """Runs the loop function forever, call this to start the App"""
        self.badger.led(self.ledLow)
        while True:
            self.loop()
            time.sleep(0.1)