#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# pyugt - Python Universal Game Translator
#
# Copyright (c) 2020 Stephen Larroque <LRQ3000@gmail.com>
#
# Licensed under MTI Public License

# User need to download Tesseract v5, the compiled binaries from UB Mannheim are an easy way: https://github.com/UB-Mannheim/tesseract/wiki


### Imports

## Native python imports
# To store and parse lists from configparser
import ast
# To write UTF8 characters in log files
import codecs
# To parse config file
import configparser
# To use as IDs for each entry in OCR and translation log files
import datetime
# For path handling
import glob
import os
# for commandline arguments handling
import optparse
# To display screenshots
import sys
# For the waiting loop
import time
# To display Tkinter windows in a thread (and be non-blocking so that shortcuts still work)
import threading
# To display screenshots and select a region
if sys.version_info[0] == 2:  # the tkinter library changed it's name from Python 2 to 3.
    import Tkinter
    tkinter = Tkinter #I decided to use a library reference to avoid potential naming conflicts with people's programs.
else:
    import tkinter
from PIL import Image, ImageTk
# To show error message boxes
from tkinter import messagebox
# To show textboxes with scrollbars
import tkinter.scrolledtext

## Internal auxiliary scripts
from _version import __version__

## External modules
# For global hotkeys (TODO: find another library to support MacOSX)
import keyboard
# For (cross-platform) screenshots
import mss
# For Optical Character Recognition
import pytesseract

## External modules - importing subpackage
# For translation - TODO: try to find a Japanese -> English offline translator, not good to be relying on an unofficial Google API, can change at any time
from googletrans import Translator


### Auxiliary functions

global prev_tk
prev_tk = None
class showPILandSelect(object):
    """Display a screenshot in fullscreen and allow to select a rectangle region inside"""
    def __init__(self, pilImage, quitOnSelect=False):
        # Prepare Tkinter fullscreen image/screenshot display
        global prev_tk

        # Create ONE SINGLE root Tk(), else it will fail on subsequent displays
        if prev_tk is None:
            prev_tk = tkinter.Tk()
            prev_tk.overrideredirect(1)
            prev_tk.withdraw()

        # Create a Toplevel() dialog window, we can create multiple ones
        root = tkinter.Toplevel()  # use Toplevel() instead of Tk() to reopen the same dialog multiple times, see also: https://github.com/dangillet/PythonFaqFr/blob/master/doc/tkinter.md and https://stackoverflow.com/questions/39458318/how-to-allow-a-tkinter-window-to-be-opened-multiple-times
        self.root = root
        # hide root dialog, useless
        
        root.overrideredirect(1)
        # Get screen size
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry("%dx%d+0+0" % (w, h))
        root.focus_set()  # set window on foreground
        root.bind("<Escape>", lambda e: (e.widget.withdraw(), e.widget.quit()))
        canvas = tkinter.Canvas(root,width=w,height=h)
        canvas.pack()
        canvas.configure(background='black')
        imgWidth, imgHeight = pilImage.size
        if imgWidth > w or imgHeight > h:
            ratio = min(w/imgWidth, h/imgHeight)
            imgWidth = int(imgWidth*ratio)
            imgHeight = int(imgHeight*ratio)
            pilImage = pilImage.resize((imgWidth,imgHeight), Image.ANTIALIAS)
        image = ImageTk.PhotoImage(pilImage)
        imagesprite = canvas.create_image(w/2,h/2,image=image)
        
        # Prepare the rectangle drawing
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.x = self.y = 0
        self.canvas = canvas
        canvas.bind("<ButtonPress-1>", self.on_button_press)
        canvas.bind("<B1-Motion>", self.on_move_press)

        canvas.create_text(w/2,h/2,fill="red",font="Times 20 italic bold",
                        text="Please select the region to capture text to translate\n(use mouse left click).%s" ("\nPress ESCAPE when done." if not quitOnSelect else ""))

        # Quit directly after selecting?
        if quitOnSelect:
            root.bind("<ButtonRelease-1>", lambda e: (root.withdraw(), root.quit()))
        else:
            canvas.bind("<ButtonRelease-1>", self.on_button_release)

        root.mainloop()

    def on_button_press(self, event):
        # save mouse drag start position
        self.start_x = event.x
        self.start_y = event.y

        # Delete rectangle if already exists and the user wants to redraw another one
        if self.rect:
            self.canvas.delete(self.rect)
        # Start to draw a rectangle
        self.rect = self.canvas.create_rectangle(self.x, self.y, 1, 1, fill="", outline="red", width=5)

    def on_move_press(self, event):
        curX, curY = (event.x, event.y)

        # expand rectangle as you drag the mouse
        self.canvas.coords(self.rect, self.start_x, self.start_y, curX, curY)    

    def on_button_release(self, event):
        pass

    def get_rect_coords(self):
        """Returns the coordinates of the rectangle drawn by the user, by fitting a bounding box over it"""
        # Solution from: https://stackoverflow.com/a/29852898/1121352
        if self.rect is None:
            return None
        else:
            return self.canvas.bbox(self.rect)

    def destroy(self):
        self.root.destroy()

def showPIL(pilImage):
    # Inspired by code by Neil from https://stackoverflow.com/a/47317411/1121352
    root = tkinter.Tk()
    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.overrideredirect(1)
    root.geometry("%dx%d+0+0" % (w, h))
    root.focus_set()    
    root.bind("<Escape>", lambda e: (e.widget.withdraw(), e.widget.quit()))
    canvas = tkinter.Canvas(root,width=w,height=h)
    canvas.pack()
    canvas.configure(background='black')
    imgWidth, imgHeight = pilImage.size
    if imgWidth > w or imgHeight > h:
        ratio = min(w/imgWidth, h/imgHeight)
        imgWidth = int(imgWidth*ratio)
        imgHeight = int(imgHeight*ratio)
        pilImage = pilImage.resize((imgWidth,imgHeight), Image.ANTIALIAS)
    image = ImageTk.PhotoImage(pilImage)
    imagesprite = canvas.create_image(w/2,h/2,image=image)
    root.mainloop()

def selectRegion(sct, config, configFile, quitOnSelect=False):
    """Region-based selection: take a whole desktop screenshot and allow the user to select the region from where to take further screenshots (easier than manipulating the OS window manager to draw rectangles on the REAL screen).
    The result is saved in the config file directly."""

    if config['DEFAULT']['debug'] == 'True':
        print('selectRegion triggered')

    # Grab whole desktop screenshot
    # Grab screenshot
    sct_img = sct.grab(sct.monitors[int(config['DEFAULT']['monitor'])])
    # Convert to a PIL Image (else we can't show it on screen)
    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    if config['DEFAULT']['debug'] == 'True':
        # Get path to temporary image file (need to save to a file to pass onto Tesseract, there's no other way to directly pipe)
        imgtemppath = 'debugselect.png'
        # Save to the picture file
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=imgtemppath)

    # Display screenshot and allow user to select a region
    appregionselect = showPILandSelect(img, quitOnSelect=quitOnSelect)
    # Get the selected rectangle's coordinates
    rectcoords = appregionselect.get_rect_coords()
    # Need to manually destroy Tk root window, else if we try to display it twice it will fail with a weird exception
    #appregionselect.destroy()
    # Save in config
    if rectcoords is not None:
        if not 'INTERNAL' in config:
            config['INTERNAL'] = {}
        config['INTERNAL']['region'] = repr(rectcoords)  # convert to a string to be parseable by configParser
        with open(configFile, 'w') as cfg:
            config.write(cfg)

global prev_root
prev_root = None
def translateRegion(sct, config, configFile):
    class TranslationBox(threading.Thread):
        def __init__(self, ocrtext, transtext):
            threading.Thread.__init__(self)
            self.ocrtext = ocrtext
            self.transtext = transtext
            self.config = config
            self.configFile = configFile
            self.start()
        
        def closeWindow(self):
            self.root.withdraw()
            self.root.quit()

        def save_geometry(self, event):
            """Save size and position of window when moved around to reopen later at the same position"""
            # Inspired by https://stackoverflow.com/a/43160322/1121352
            if not 'INTERNAL' in self.config:
                self.config['INTERNAL'] = {}
            self.config['INTERNAL']['translationbox_position'] = self.root.geometry()
            with open(self.configFile, 'w') as cfg:
                self.config.write(cfg)

        def load_geometry(self):
            """Load size and position of window from config file"""
            if 'INTERNAL' in self.config and 'translationbox_position' in self.config['INTERNAL']:
                self.root.geometry(self.config['INTERNAL']['translationbox_position'])

        def run(self):
            root = tkinter.Tk()
            self.root = root
            # Clean up window on close
            root.protocol("WM_DELETE_WINDOW", self.closeWindow)
            # Load position if one is saved in config file
            self.load_geometry()
            # Save size and position in config on move
            root.bind("<Configure>", self.save_geometry)
            # Title and default window size
            root.title("pyugt translation")
            root.geometry('300x500')
            # Make content resizable + give same weight for both textboxes so they have the same size
            root.grid_columnconfigure(0, weight=1)
            root.grid_columnconfigure(1, weight=1)
            root.grid_rowconfigure(0, weight=1)
            root.grid_rowconfigure(1, weight=1)
            root.resizable(True, True)
            # Create the textboxes (with scrollbars)
            txtsrc = tkinter.scrolledtext.ScrolledText(root)
            txtout = tkinter.scrolledtext.ScrolledText(root)
            # Place the textboxes vertically
            txtsrc.grid(row=0)
            txtout.grid(row=1)
            # Insert the text (translation and original)
            txtsrc.insert('1.0', self.ocrtext)  # original OCR'ed text in the 1st textbox
            txtout.insert('1.0', self.transtext)  # translated text in the 2nd textbox
            # Set window on foreground
            root.focus_set()
            # Show window
            root.mainloop()

    global prev_root  # allow to check if a previous root window is still open, and close it down

    if config['DEFAULT']['debug'] == 'True':
        print('translateRegion triggered')
    # First check a region was set, else raise an error
    if 'INTERNAL' not in config or 'region' not in config['INTERNAL'] or ast.literal_eval(config['INTERNAL']['region']) is None:
        show_errorbox("Error: please first select a region to capture from (use hotkey %s)" % config['DEFAULT']['hotkey_set_region_capture'])
        return
    # Load config file into memory variables
    langsource_ocr = config['DEFAULT']['lang_source_ocr']
    langsource_trans = config['DEFAULT']['lang_source_trans']
    langtarget = config['DEFAULT']['lang_target']
    # Grab whole desktop screenshot
    # Grab screenshot
    x0,y0,x1,y1 = ast.literal_eval(config['INTERNAL']['region'])
    screenregion = {'top': y0, 'left': x0, 'width': x1-x0, 'height': y1-y0}
    sct_img = sct.grab(screenregion)
    # Convert to a PIL Image (else we can't show it on screen)
    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    if config['DEFAULT']['debug'] == 'True':
        # Get path to temporary image file (need to save to a file to pass onto Tesseract, there's no other way to directly pipe)
        imgtemppath = 'debugtranslate.png'
        # Save to the picture file
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=imgtemppath)

    # Tesseract OCR to extract text, directly from a PIL image object thanks to the pytesseract wrapper
    ocrtext = pytesseract.image_to_string(img, lang=langsource_ocr, nice=1)
    # TODO: use image_to_boxes or image_to_osd or image_to_data to get position of strings and place them back in place on a screenshot, similarly to what Universal Game Translator does
    if not ocrtext.strip():
        show_errorbox('No text found by OCR! Make sure your capture region is properly set!')
        return
    if config['DEFAULT']['debug'] == 'True':
        print('OCR\'ed text:')
        print(ocrtext)
    #os.system('tesseract -l {imgpath} {srclang} {outputtxt}'.format(imgpath=os.path.abspath(imgtemppath), srclang=langsource, outputtxt='test'))  # alternative way to generate the OCR, by commandline call directly

    # Translate using Google Translate through the googletrans (unofficial) wrapper module
    translator = Translator()
    transobj = translator.translate(ocrtext, src=langsource_trans, dest=langtarget)
    transtext = transobj.text

    if config['DEFAULT']['debug'] == 'True':
        print('Translated text:')
        print(transtext)

    # Save OCR'ed text and translation in logs if specified. The same datetime will be written for both, so that they can be matched externally.
    curdatetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if config['DEFAULT']['log_ocr'] != 'None':
        with codecs.open(config['DEFAULT']['log_ocr'], 'a', 'utf-8-sig') as f:
            f.write("-> OCR at %s:\n" % curdatetime)
            f.write(ocrtext)
            f.write("\n---------------------\n")
    if config['DEFAULT']['log_translation'] != 'None':
        with codecs.open(config['DEFAULT']['log_translation'], 'a', 'utf-8-sig') as f:
            f.write("-> Translation at %s:\n" % curdatetime)
            f.write(transtext)
            f.write("\n---------------------\n")

    # Show the translation box
    if prev_root is not None:
        # Close previous window if still open
        # TODO: instead of closing, reinsert text (so we keep window position)
        prev_root.closeWindow()
    twindow = TranslationBox(ocrtext, transtext)
    prev_root = twindow


def selectAndTranslateRegion(sct, config, configFile):
    """Wrapper to select a region and translate it directly after, this streamlines the process"""
    selectRegion(sct, config, configFile, quitOnSelect=True)
    translateRegion(sct, config, configFile)

def show_errorbox(msg):
    """Show an error box"""
    root = tkinter.Toplevel()
    root.withdraw()
    messagebox.showerror("Error", msg)
    root.destroy()  # need to manually destroy the main window, else tk shows an empty window alongside the messagebox... Solution from: https://stackoverflow.com/a/57523108/1121352

def show_errorbox_exception(msg):
    """Show both an error box and raise an Exception"""
    show_errorbox(msg)
    raise Exception(msg)


### Main program
def main():
    # Commandline arguments
    parser = optparse.OptionParser()
    parser.add_option("-c", "--config", dest="config", default=None,
                        help="Path to the config file (default: config.ini)", metavar="FILE")
    (options, args) = parser.parse_args()
    configFileArg = options.config

    # Print description message on startup
    print('pyugt - Python Universal Game Translator v%s - started' % __version__)
    # Path to current script (to find the config file)
    curpath = os.path.dirname(os.path.abspath(__file__))
    # Load config file
    config = configparser.ConfigParser()
    if configFileArg:
        # Specified by user
        configFile = os.path.abspath(configFileArg)
    else:
        # Default path
        configFile = os.path.join(curpath, 'config.ini')
    # Check the path exists
    if not os.path.exists(configFile):
        show_errorbox_exception('Specified configuration file (%s) does not exist!' % configFile)
    # Load up the config file in memory
    config.read(configFile)

    # Load config file into memory variables
    PATH_tesseract_bin = config['DEFAULT']['PATH_tesseract_bin']
    if not os.path.exists(PATH_tesseract_bin):
        show_errorbox_exception("Can't find Tesseract v5 binaries, please update the config.ini file to point to the binaries! If it's not installed, on Windows installers are provided by UB Mannheim's at: https://github.com/UB-Mannheim/tesseract/wiki")
    # Add Tesseract binary to the path (so that the user does not need to do it in their OS)
    pytesseract.pytesseract.tesseract_cmd = PATH_tesseract_bin
    # Get the list of available languages (selected by user at Tesseract install)
    teslangs = [os.path.split(x)[1].split('.')[0] for x in glob.glob(os.path.join(os.path.dirname(PATH_tesseract_bin), 'tessdata','*.traineddata'))]
    print('Languages available for OCR: %s' % repr(teslangs))

    # Load up the screenshot capture module
    # We need to load up mss only once, else if it's inside the functions it will fail on second call after being closed in the first call
    # It's also faster to initialize it only once, per https://python-mss.readthedocs.io/examples.html#benchmark
    sct = mss.mss()
    # Set global hotkeys, loading from config file
    keyboard.add_hotkey(config['DEFAULT']['hotkey_set_region_capture'], selectRegion, args=(sct, config, configFile))
    print('Hit %s to set the region to capture.' % config['DEFAULT']['hotkey_set_region_capture'])
    keyboard.add_hotkey(config['DEFAULT']['hotkey_translate_region_capture'], translateRegion, args=(sct, config, configFile))
    print('Hit %s to translate the region (make sure to close the translation window before requesting another one).' % config['DEFAULT']['hotkey_translate_region_capture'])
    keyboard.add_hotkey(config['DEFAULT']['hotkey_set_and_translate_region_capture'], selectAndTranslateRegion, args=(sct, config, configFile))
    print('Hit %s to set AND translate a region.' % config['DEFAULT']['hotkey_set_and_translate_region_capture'])

    # Main waiting loop (we wait for hotkeys to be pressed)
    print('Press CTRL+C or close this window to quit.')
    while 1:
        time.sleep(1)

    # Exit gracefully if no exception until this point
    return 0


if __name__ == "__main__":
    rtncode = main()
    sys.exit(rtncode)
