import math
import os
import badger2040
from badger2040 import Badger2040, WIDTH, HEIGHT
from buttons import Buttons
import json
import time
from qrcode import QRCode
from App import App, AbstractScreen, NO_UPDATE

#Configurable constants
NAME = "Person Name"
LINK_BASE = "https://example.com"
USE_ADV_LINK = False #(warning, this is a work work in progress)
N_PRONOUNS = 3 #Maximum number of pronouns to display. Recommend 2 or 3
N_ABOUT_LINES = 3 #Maximum number of about lines to display. Recommend 3, but 6 is possible

#Constants
STATE_FILE = "badges/state.json"
AVATAR_SIZE = 128
FONT = "bitmap8"
LINE_HEIGHT = 9
TEXT_PADDING = 8
WHITE = 15
BLACK = 0
ICON_SIZE = 64
ICONS_ACROSS = 4
ICONS_PER_PAGE = 8

class QR():
    def __init__(self,app):
        self.app = app
        self.badger = app.badger
        self.code = QRCode()
        self._text = ""
    
    @property
    def text(self):
        return self._text
    
    @text.setter
    def text(self,value):
        self._text = value
        self.code.set_text(value)
    
    def measure(self,size):
        w,h = self.code.get_size()
        mSize = size//w
        return mSize*w, mSize
    
    def draw(self,ox,oy,origSize):
        size, mSize = self.measure(origSize)
        ox += (origSize-size)//2
        oy += (origSize-size)//2
        self.badger.pen(15)
        self.badger.rectangle(ox,oy,size,size)
        self.badger.pen(0)
        for x in range(size):
            for y in range(size):
                if self.code.get_module(x,y):
                    self.badger.rectangle(ox + x * mSize, oy + y * mSize, mSize, mSize)

class Badge(AbstractScreen):
    def __init__(self,app):
        super().__init__(app)
        
        self.code = QR(app)
        self.showQr = False
        
        self.image = bytearray(AVATAR_SIZE*AVATAR_SIZE//8)
        self.imageName = None
        self.lines = [None]*N_PRONOUNS
        self.pronouns = [None]*N_ABOUT_LINES
        
        self.loadState()
        
    def loadState(self):
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
                img = data.get("imageName",None)
                if img is not None:
                    self.setImage(img)
                self.lines = data.get("lines",self.lines)
                self.pronouns = data.get("pronouns",self.pronouns)
        except OSError:
            pass  
    
    def onSleep(self,wasVisible,willBeVisible):
        with open(STATE_FILE,"w") as f:
            data = json.dump({
                "imageName":self.imageName,
                "lines":self.lines,
                "pronouns":self.pronouns
            },f)
    
    def setImage(self,imageFile):
        self.imageName = imageFile
        with open(imageFile) as f:
            f.readinto(self.image)
    
    def drawText(self,textData,x,y):
        self.badger.font(FONT)
        for scale, line in textData:
            self.badger.text(line,x,y,scale)
            y+=scale*LINE_HEIGHT
        return y
    
    def drawAll(self):
        self.badger.pen(WHITE)
        self.badger.clear()
        self.badger.pen(BLACK)
        if self.showQr:
            self.code.draw(0,0,128)
        else:
            self.badger.image(self.image,AVATAR_SIZE,AVATAR_SIZE,0,0)
            
        self.badger.font(FONT)
        
        lines = [x for x in self.lines if x is not None]
        nFullSize = 6-len(lines)
        formatLines = [
            (2 if i<nFullSize else 1, "* "+x)
            for (i,x) in enumerate(lines)
        ]
        
        self.drawText(
            [
                (3,NAME),
                (2,"/".join(x for x in self.pronouns if x is not None)),
                (1,"")
            ] + formatLines,
            AVATAR_SIZE+TEXT_PADDING,TEXT_PADDING
        )
        
        # Artist Credit
        if self.imageName is None:
            n = "Press A to select image"
        else:
            artist,file = self.imageName.split("/")[-1][:-4].split("-",1)
            if artist == "_":
                n = "Unknown Artist"
            else:
                n = f"Art by: {artist}"
        w = self.badger.measure_text(n,1)
        self.badger.text(n,WIDTH-w-4,HEIGHT-10,1)
        
        self.app.queueUpdate(0,badger2040.UPDATE_NORMAL)
    
    def button_a(self):
        self.app.setScreen(self.iconSelector)
        
    def button_b(self):
        self.app.setScreen(self.pns)
    
    def button_c(self):
        self.app.setScreen(self.bls)
    
    def button_down(self):
        self.showQr = not self.showQr
        if self.showQr:
            if USE_ADV_LINK:
                a = self.imageName.split("/")[-1][:-4]
                p = '/'.join(p for p in self.pronouns if p is not None)
                l = ','.join(p for p in self.lines if p is not None)
                self.code.text = f"{LINK_BASE}#{a}|{p}|{l}"
            else:
                self.code.text = LINK_BASE
        self.drawAll()

class SelectorBase(AbstractScreen):
    def __init__(self,app,nOptions,options,selectedLines,useTicks):
        super().__init__(app)

        self.nOptions = nOptions
        self.bylines = options
        self.useTicks = useTicks
        
        #Set selected indices
        self.selTxts = [-1]*self.nOptions
        for i in range(self.nOptions):
            try:
                self.selTxts[i] = self.bylines.index(selectedLines[i])
            except (IndexError,ValueError) as e:
                pass

        #Set index
        if self.selTxts[0] != -1:
            self.index = self.selTxts[0]
        else:
            self.index = 0
        
        #Store selected lines incase of cancel
        self.selTxtsOld = self.selTxts[:]
        
        # Selector vars
        self.last = None
        self.putIn = 0
        self.deltaIndex(0) #Sets up putIn
        
    def update(self):
        self.badger.pen(WHITE)
        self.badger.clear()
        self.badger.pen(BLACK)
        self.badger.font(FONT)
        
        LINES_PER_SCREEN = 5
        
        for i in range(LINES_PER_SCREEN):
            j = (self.index-LINES_PER_SCREEN//2+i) % len(self.bylines)
            arr = "> " if i == LINES_PER_SCREEN//2 else "  "
            
            if self.useTicks:
                marks = "".join("*" if x == j else "-" for x in self.selTxts)
            else:
                try:
                    marks = str(self.selTxts.index(j)+1)
                except ValueError:
                    marks = "-"
            
            self.badger.text(arr+marks+" "+self.bylines[j],TEXT_PADDING,i*LINE_HEIGHT*2+TEXT_PADDING,2)
        
        for i,t in enumerate(self.getTexts()):
            if t is not None:
                w = self.badger.measure_text(t,2)
                self.badger.text(t,WIDTH-TEXT_PADDING-w,i*LINE_HEIGHT*2+LINE_HEIGHT+TEXT_PADDING,2)
            
        self.app.queueUpdate(0.5,badger2040.UPDATE_TURBO)
    
    def getTexts(self):
        return [
            (self.bylines[x] if x != -1 else None)
            for x in self.selTxts
        ]
    
    def deltaIndex(self,x):
        self.index = (self.index+x)%len(self.bylines)
        self.last = None
        try:
            self.putIn = self.selTxts.index(self.index)+1
        except ValueError:
            self.putIn = 0
    
    def button_up(self):
        self.deltaIndex(-1)
        self.update()
    
    def button_down(self):
        self.deltaIndex(1)
        self.update()
    
    def button_a(self):
        self.selTxts = self.selTxtsOld[:]
        self.deltaIndex(0)
        self.app.setScreen(self.badge)
    
    def button_b(self):
        self.selTtxtsOld = self.selTxts[:]
        self.app.setScreen(self.badge)
    
    def button_c(self):
        #Reset the last one as we move out
        if self.last is not None:
            self.selTxts[self.putIn-1] = self.last
        #Unset ourselves
        for i in range(self.nOptions):
            if self.selTxts[i] == self.index:
                self.selTxts[i] = -1
        
        if self.putIn == self.nOptions:
            self.putIn = 0 #Clear if at end
        else:
            # Otherwise, store the one we where just at
            # Then update our location
            self.last = self.selTxts[self.putIn]
            self.selTxts[self.putIn] = self.index
            self.putIn += 1
        self.update()
    
    def drawAll(self):
        self.update()
        self.app.queueUpdate(0,badger2040.UPDATE_NORMAL)

class ByLineSelector(SelectorBase):
    def __init__(self,app,selected):
        #Load bylines
        with open("badges/bylines.txt") as f:
            options = [x.strip() for x in f.readlines()]
        
        super().__init__(app,N_ABOUT_LINES,options,selected,N_ABOUT_LINES<=3)
        
    def button_b(self):
        self.badge.lines = self.getTexts()
        super().button_b()

class PronounSelector(SelectorBase):
    def __init__(self,app,selected):
        #Load pronouns
        with open("badges/pronouns.txt") as f:
            options = [x.strip() for x in f.readlines()]
        
        super().__init__(app,N_PRONOUNS,options,selected,True)
        
    def button_b(self):
        self.badge.pronouns = self.getTexts()
        super().button_b()

class IconSelector(AbstractScreen):
    def __init__(self,app,selectedImage):
        super().__init__(app)
        
        #Load files
        self.fileNames = [x for x in os.listdir("badges/images") if x.endswith(".bin")]    
    
        #Set selected index to current file
        try:
            self.index = self.fileNames.index(selectedImage.split("/")[-1])
        except (ValueError,AttributeError):
            self.index = 0
        self.page = self.index // ICONS_PER_PAGE
        
        #Set maxIndex and maxPages
        self.maxIndex = len(self.fileNames)
        self.maxPages = math.ceil(self.maxIndex / ICONS_PER_PAGE)
    
    def nextPage(self):
        i = (self.index+8)%(self.maxPages*8)
        if i >= self.maxIndex:
            i = self.maxIndex-1
        newPage = self.index // ICONS_PER_PAGE
        self.updatePos(i)
    
    def updateDelta(self,delta):
        i = (self.index+delta) % self.maxIndex
        self.updatePos(i)
    
    def updatePos(self,i):
        self.index = i
        newPage = self.index // ICONS_PER_PAGE
        
        if newPage != self.page:
            self.badger.pen(WHITE)
            self.badger.clear()
            self.page = newPage
            self.drawPage()
            
        self.drawIndex()
    
    def drawPage(self):
        self.badger.pen(BLACK)
        self.badger.line(WIDTH-8,0,WIDTH-8,HEIGHT)
        barTop = HEIGHT*self.page//self.maxPages
        barBottom = HEIGHT*(self.page+1)//self.maxPages
        self.badger.rectangle(WIDTH-8,barTop,8,barBottom-barTop)
        
        imgs = self.fileNames[self.page*ICONS_PER_PAGE:(1+self.page)*ICONS_PER_PAGE]
        for i,name in enumerate(imgs):
            img = bytearray(ICON_SIZE**2//8)
            y,x=divmod(i,ICONS_ACROSS)
            
            try:
                with open("badges/halfImages/"+name) as f:
                    f.readinto(img)
                self.badger.image(img,ICON_SIZE,ICON_SIZE,x*ICON_SIZE,y*ICON_SIZE)
            except OSError:
                self.badger.font(FONT)
                self.badger.pen(BLACK)
                self.badger.rectangle(x*ICON_SIZE,y*ICON_SIZE,ICON_SIZE,ICON_SIZE)
                self.badger.pen(WHITE)
                drawWrappedText(name[:-4],x*ICON_SIZE+2,y*ICON_SIZE+2,ICON_SIZE-4,2,16)

        self.app.queueUpdate(0,badger2040.UPDATE_FAST)
            
    def drawIndex(self):
        left = ICONS_ACROSS*ICON_SIZE+8
        size = 18
        
        self.badger.pen(BLACK)
        self.badger.rectangle(left, 8, size,size)
        self.badger.rectangle(left, 16+size,size,size)
        self.badger.pen(WHITE)
        self.badger.rectangle(left+1, 9, size-2, size-2)
        self.badger.rectangle(left+1, 17+size, size-2, size-2)
        
        ix = self.index%ICONS_PER_PAGE
        x1 = ix & 1
        y1 = (ix>>1) & 1
        y2 = (ix>>2) & 1
        
        s2 = size//2
        self.badger.pen(BLACK)
        self.badger.rectangle(left+x1*s2, 8+y1*s2+y2*(8+size), s2, s2)
        self.app.queueUpdate(0.5,badger2040.UPDATE_TURBO)
    
    def drawAll(self):
        self.drawPage()
        self.drawIndex()
        self.app.queueUpdate(0,badger2040.UPDATE_NORMAL)
    
    def button_a(self):
        self.app.setScreen(self.badge)
    
    def button_b(self):
        self.nextPage()
    
    def button_c(self):
        self.badge.setImage("badges/images/"+self.fileNames[self.index])
        self.app.setScreen(self.badge)
    
    def button_up(self):
        self.updateDelta(-1)
        
    def button_down(self):
        self.updateDelta(1)

def drawWrappedText(text,x,y,width,scale,lineHeight):
    while text:
        for i in range(len(text),0,-1):
            t = text[:i]
            w = badger.measure_text(t,scale)
            if w<=width:
                text = text[i:]
                badger.text(t,x,y,scale)
                y+=lineHeight

def main():
    try:
        badger = Badger2040()
        app = App(badger)

        # Setup the screens we will use
        badge = Badge(app)
        iconSelector = IconSelector(app,badge.imageName)
        bls = ByLineSelector(app,badge.lines)
        pns = PronounSelector(app,badge.pronouns)
        
        badge.iconSelector = iconSelector
        badge.bls = bls
        badge.pns = pns
        
        iconSelector.badge = badge
        bls.badge = badge
        pns.badge = badge
        
        app.returnTo = badge

        # If there is no image setup, default to the image selector
        if badge.imageName == None:
            app.setScreen(iconSelector)
        else:
            app.setScreen(badge)

        #Run loop
        app.runForever()

    except Exception as err:
        import sys,io
        badger.pen(BLACK)
        badger.clear()
        badger.pen(WHITE)
        badger.font(FONT)
        strio = io.StringIO(f"{err}\n")
        sys.print_exception(err,strio)
        badger.text(strio.getvalue(),1,1)
        badger.update_speed(badger2040.UPDATE_NORMAL)
        badger.update()
        if __name__ == "__main__":
            raise

main()
