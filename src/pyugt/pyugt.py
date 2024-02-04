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
# To gracefully print stack trace in console in case of an exception
import traceback
# To display screenshots and select a region and preprocess the screenshot to enhance letters detection against translucent backgrounds
if sys.version_info[0] == 2:  # the tkinter library changed it's name from Python 2 to 3.
    import Tkinter
    tkinter = Tkinter #I decided to use a library reference to avoid potential naming conflicts with people's programs.
else:
    import tkinter
from PIL import Image, ImageTk, ImageFilter, ImageMath
# To show error message boxes and textboxes with scrollbars
from tkinter import messagebox, scrolledtext

## External modules
# For global hotkeys (TODO: find another library to support MacOSX)
import keyboard
# For (cross-platform) screenshots
import mss
# For Optical Character Recognition
import pytesseract

## External modules - translators
# For free online translation (may be throttled)
import translators
from tenacity import retry, wait_random, wait_exponential, stop_after_delay  # to retry when throttled
# Paid online translations via DeepL (there is a free tier)
import deepl
# Local offline free unthrottled translator via Argos Translate using OpenNMT
import argostranslate.package
import argostranslate.translate

## Import version
# Get version, better than importing the module because can fail if the requirements aren't met
# See https://packaging.python.org/guides/single-sourcing-package-version/
import codecs, re
curpath = os.path.abspath(os.path.dirname(__file__))
def read(*parts):
    with codecs.open(os.path.join(*parts), 'r') as fp:
        return fp.read()
def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__\s*=\s*['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")
__version__ = find_version(curpath, "_version.py")

### Auxiliary functions

class showPILandSelect(threading.Thread):
    """Display a screenshot in fullscreen and allow to select a rectangle region inside"""
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)  # always close thread along with parent process
        self.start()

    def run(self):
        # Create a Toplevel() dialog window, we can create multiple ones
        root = tkinter.Tk()  # use Toplevel() instead of Tk() to reopen the same dialog multiple times, see also: https://github.com/dangillet/PythonFaqFr/blob/master/doc/tkinter.md and https://stackoverflow.com/questions/39458318/how-to-allow-a-tkinter-window-to-be-opened-multiple-times
        self.root = root
        # Create empty canvas
        self.canvas = None
        # Create empty photoimage for reuse
        self.photoimage = None
        # hide root dialog
        root.overrideredirect(1)
        root.withdraw()

        # Launch the window
        self.root.mainloop()

    def display(self, pilImage, quitOnSelect=False):
        # Setup a variable that will be used as a lock to signal to parent thread that the user is not yet done with the region selection
        self.selectionDone = False
        # Get screen size
        w, h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        # Set canvas to be fullscreen
        self.root.geometry("%dx%d+0+0" % (w, h))
        # Initialize/reset canvas
        if self.canvas is not None:
            # Clear and reuse canvas if previously created
            canvas = self.canvas
            canvas.delete('all')
        else:
            # Else create it
            canvas = tkinter.Canvas(self.root,width=w,height=h)
            self.canvas = canvas
        # Prepare the canvas to load the screenshot image supplied as argument in pilImage
        canvas.pack()
        canvas.configure(background='black')
        imgWidth, imgHeight = pilImage.size
        if imgWidth > w or imgHeight > h:
            ratio = min(w/imgWidth, h/imgHeight)
            imgWidth = int(imgWidth*ratio)
            imgHeight = int(imgHeight*ratio)
            pilImage = pilImage.resize((imgWidth,imgHeight), Image.ANTIALIAS)
        if self.photoimage is not None:
            del self.photoimage
        image = ImageTk.PhotoImage(pilImage)
        self.photoimage = image
        #else:
        #    image = self.photoimage.paste(pilImage)
        imagesprite = canvas.create_image(w/2,h/2,image=image)

        # Prepare the rectangle drawing to select a region
        self.rect = None  # reset region
        self.start_x = None
        self.start_y = None
        self.x = self.y = 0
        self.canvas = canvas
        canvas.bind("<ButtonPress-1>", self.on_button_press)
        canvas.bind("<B1-Motion>", self.on_move_press)

        canvas.create_text(w/2,h/2,fill="red",font="Times 20 italic bold",
                        text="Please select the region to capture text to translate\n(use mouse left click).%s" % ("\nPress ESCAPE when done." if not quitOnSelect else ""))

        # What do we do after the user selected a region (ie, releasing the mouse button)?
        canvas.bind("<ButtonRelease-1>", lambda event: self.on_button_release(event, quitOnSelect))
        # Another way to finish is to press Escape (this is the only way if using the CTRL+SHIFT+F3 hotkey, because then we allow the user to redraw the region how many times they want until they get it right)
        self.root.bind("<Escape>", self.signal_done)

        # Show this window
        self.root.deiconify()

        # set window on foreground, on top of others
        self.root.focus_set()
        self.root.lift()
        self.root.attributes('-topmost', 'true')

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

    def on_button_release(self, event, quitOnSelect=False):
        # Quit directly after selecting?
        if quitOnSelect:
            self.signal_done(event)
        else:
            pass

    def signal_done(self, event):
        """Hides window and signal the user finished the selection of a region"""
        # Hide the window
        self.root.withdraw()
        #event.widget.withdraw()
        # Signal the region selection is done
        self.selectionDone = True

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

def selectRegion(sct, RegionSelector, config, config_internal, quitOnSelect=False):
    """Region-based selection: take a whole desktop screenshot and allow the user to select the region from where to take further screenshots (easier than manipulating the OS window manager to draw rectangles on the REAL screen).
    The result is saved in the config file directly."""

    if config['USER']['debug'] == 'True':
        print('selectRegion triggered')

    # Grab whole desktop screenshot
    monitor = int(config['USER']['monitor'])
    with mss.mss() as sct2:  # TODO: workaround for the thread unsafe issue https://github.com/BoboTiG/python-mss/issues/273
        sct_img = sct2.grab(sct2.monitors[monitor]) if monitor >= 0 else 1 # sct.shot() captures the first monitor, sct.shot(mon=-1) captures all monitors, but they cannot capture a specific region. Under the hood, sct.shot() uses sct.save(), which itself calls sct.grab(), itself calling PIL.ImageGrab.grab(), with sct.grab(1) capturing the first monitor (it's 1-indexed, not 0! sct.monitors[0] should contain the list of all monitors), etc. - note that only sct.shot() can capture automatically the first monitor or all monitors, not grab() which on the other hand can capture a specific region on screen if provided a bounding box
    # Convert to a PIL Image (else we can't show it on screen)
    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    if config['USER']['debug'] == 'True':
        # Get path to temporary image file (need to save to a file to pass onto Tesseract, there's no other way to directly pipe)
        imgtemppath = 'debugselect.png'
        # Save to the picture file
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=imgtemppath)

    # Display screenshot and allow user to select a region
    RegionSelector.display(img, quitOnSelect=quitOnSelect)
    # Wait until the user selects a region (we launch the RegionSelector as a thread, so it's non-blocking + the thread is never stopped so we can reuse it and avoid memory leaks)
    while RegionSelector.selectionDone is not True:  # we wait until the thread changes its lock-like variable to signal the user selected a region
        # TODO: maybe do this more elegantly with a threading.Lock?
        time.sleep(1)
    # Get the selected rectangle's coordinates
    rectcoords = RegionSelector.get_rect_coords()
    # Need to manually destroy Tk root window, else if we try to display it twice it will fail with a weird exception
    #appregionselect.destroy()
    # Save in config
    if rectcoords is not None:
        if not 'INTERNAL' in config_internal:
            config_internal['INTERNAL'] = {}
        config_internal['INTERNAL']['region'] = repr(rectcoords)  # convert to a string to be parseable by configParser
        with open(config_internal.fullpath, 'w') as cfg:
            config_internal.write(cfg)

class TranslationBox(threading.Thread):
    """Translation box, where the OCR'ed text will be copied to, and the translation will be displayed. It's essentially a text container, but it allows the user to manually correct the OCR'ed text before feeding it to the machine translator, and it can be done iteratively since we provide a Translate button to retry an erronous translation (also, the config file can be edited to change translator on-the-fly)."""
    def __init__(self, config, config_internal):
        threading.Thread.__init__(self)
        self.config = config
        self.config_internal = config_internal
        self.previewer = None
        self.setDaemon(True)  # always close thread along with parent process
        self.start()
    
    def closeWindow(self):
        self.root.withdraw()
        #self.root.quit()

    def save_geometry(self, event):
        """Save size and position of window when moved around to reopen later at the same position"""
        # Inspired by https://stackoverflow.com/a/43160322/1121352
        if not 'INTERNAL' in self.config_internal:
            self.config_internal['INTERNAL'] = {}
        self.config_internal['INTERNAL']['translationbox_position'] = self.root.geometry()
        with open(self.config_internal.fullpath, 'w') as cfg:
            self.config_internal.write(cfg)

    def load_geometry(self):
        """Load size and position of window from config file"""
        if 'INTERNAL' in self.config_internal and 'translationbox_position' in self.config_internal['INTERNAL']:
            self.root.geometry(self.config_internal['INTERNAL']['translationbox_position'])

    def translate(self):
        # Reload config file, so that user can change parameters on-the-fly
        self.config = read_config(self.config.fullpath)
        self.config_internal = read_config(self.config_internal.fullpath)
        # Update ocrtext with the textbox input
        self.ocrtext = self.txtsrc.get("1.0","end-1c")  # end-1c trick from https://stackoverflow.com/questions/14824163/how-to-get-the-input-from-the-tkinter-text-box-widget
        # Translate using machine translation (various several translators API are supported)
        self.transtext = translate_any(self.config, self.ocrtext, self.config['USER']['lang_source_trans'], self.config['USER']['lang_target'])
        # Clear up the translation textbox
        self.txtout.delete("1.0", tkinter.END)
        # Rewrite the translation textbox content with the new translation
        self.txtout.insert('1.0', self.transtext)

    def run(self):
        # Launch GUI
        root = tkinter.Tk()  # this is the main window, so we can use Tk() to initialize, instead of Toplevel() for others
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
        root.grid_columnconfigure(2, weight=1)
        root.grid_rowconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)
        root.grid_rowconfigure(2, weight=1)
        root.resizable(True, True)
        # Create the textboxes (with scrollbars)
        self.txtsrc = scrolledtext.ScrolledText(root, undo=True)
        self.txtout = scrolledtext.ScrolledText(root, undo=True)
        # Place the textboxes vertically
        self.txtsrc.grid(row=0)
        self.txtout.grid(row=1)
        # Insert the text (translation and original)
        self.txtsrc.insert('1.0', '')  # original OCR'ed text in the 1st textbox
        self.txtout.insert('1.0', '')  # translated text in the 2nd textbox
        # Create a button to allow user to manually edit the OCR'ed text and manually force translation again
        self.buttontrans = tkinter.Button(root, text='Translate again', command=self.translate)
        self.buttontrans.grid(row=3)
        # Set window on foreground and stay on top of others
        root.focus_set()
        root.lift()
        root.attributes('-topmost', 'true')
        # Show window
        root.mainloop()

    def update_text(self, ocrtext, transtext):
        # Clear up the textboxes
        self.txtsrc.delete("1.0", tkinter.END)
        self.txtout.delete("1.0", tkinter.END)
        # Replace with the supplied text
        self.txtsrc.insert('1.0', ocrtext)  # original OCR'ed text in the 1st textbox
        self.txtout.insert('1.0', transtext)  # translated text in the 2nd textbox
        # Show dialog if it was closed/hidden
        self.root.deiconify()  # opposite of .withdraw()
        # Set window on foreground and stay on top of others
        self.root.focus_set()
        self.root.lift()
        self.root.attributes('-topmost', 'true')

@retry(wait=wait_exponential(multiplier=1, max=5) + wait_random(0, 2), stop=stop_after_delay(10))
def translate_online_free(ocrtext, langsource_trans, langtarget='en', translator='google'):
    """Translate using the translators module which queries web apps free interfaces, but can be denied access due to throttling, hence we retry"""
    return translators.translate_text(ocrtext, translator=translator, from_language=langsource_trans, to_language=langtarget)

def translate_online_paid_deepl(ocrtext, langsource_trans, langtarget='EN-US', authkey=None):
    """Translate using DeepL API, not throttled but may require payments if too many requests. Currently best in class japaneses -> english translator."""
    translator = deepl.Translator(authkey)
    return translator.translate_text(ocrtext, source_lang=langsource_trans, target_lang=langtarget).text

def translate_offline_argos(ocrtext, from_code, to_code='en'):
    """Offline translation using Argos Translate, based on OpenNMT"""
    # Download and install Argos Translate package if necessary, otherwise will automatically reuse the one already downloaded
    argostranslate.package.update_package_index()
    try:
        available_packages = argostranslate.package.get_available_packages()
        package_to_install = next(
            filter(
                lambda x: x.from_code == from_code and x.to_code == to_code, available_packages
            )
        )
        argostranslate.package.install_from_path(package_to_install.download())
    except StopIteration as exc:
        raise ValueError('ERROR: no matching language found for either the target language %s or source language %s, please check if they are valid for the selected translator!' % (to_code, from_code))
    except Exception as exc:
        traceback.print_exc()
        pass

    # Translate
    return argostranslate.translate.translate(ocrtext, from_code, to_code)

def translate_any(config, ocrtext, langsource_trans, langtarget):
    """Helper function to select a translator according to config file and return a translation, and manage exceptions gracefully"""
    # Send ocr text to the machine translator, but first select which translator we want
    transtext = ''
    try:
        if config['USER']['translator_lib'] == 'online_free':
            transtext = translate_online_free(ocrtext, langsource_trans, langtarget, translator=config['USER']['translator_lib_online_free_service'])
        elif config['USER']['translator_lib'] == 'deepl':
            transtext = translate_online_paid_deepl(ocrtext, langsource_trans, langtarget, authkey=config['USER']['translator_lib_deepl_authkey'])
        elif config['USER']['translator_lib'] == 'offline_argos':
            transtext = translate_offline_argos(ocrtext, langsource_trans, langtarget)
        else:
            raise ValueError('Specified translator_lib in config.ini does not exist! Please specify one of the following: online_free, deepl or offline_argos.')
    except Exception as exc:
        # When querying online services, we can always run into exceptions and availability issues, then this may crash the app, so we need to catch the exception
        print('ERROR: an exception occurred while trying to translate text:')
        traceback.print_exc()
        transtext = 'ERROR'
    return transtext

def translateRegion(sct, TBox, config, config_internal):
    """Capture a screenshot of a previously defined region, preprocess to increase contrast for OCR, detect text out of image using Tesseract OCR and finally translate via a machine translator"""
    # Reload config file, so that user can change parameters on-the-fly
    config = read_config(config.fullpath)
    config_internal = read_config(config_internal.fullpath)
    # Debug print
    if config['USER']['debug'] == 'True':
        print('translateRegion triggered')
    # First check a region was set, else raise an error
    if 'INTERNAL' not in config_internal or 'region' not in config_internal['INTERNAL'] or ast.literal_eval(config_internal['INTERNAL']['region']) is None:
        show_errorbox("Error: please first select a region to capture from (use hotkey %s)" % config['USER']['hotkey_set_region_capture'])
        return
    # Load config file into memory variables
    langsource_ocr = config['USER']['lang_source_ocr']
    langsource_trans = config['USER']['lang_source_trans']
    langtarget = config['USER']['lang_target']
    # Grab screenshot of a specific region
    x0,y0,x1,y1 = ast.literal_eval(config_internal['INTERNAL']['region'])
    screenregion = {'top': y0, 'left': x0, 'width': x1-x0, 'height': y1-y0}  # region to capture
    monitor = int(config['USER']['monitor'])  # get user selected monitor (-2 for first monitor, -1 for all monitors, 0 for monitor 0, etc).
    screenregion['mon'] = monitor if monitor >= 0 else 1  # if the region to capture is on another monitor than the default one, the user can specify it. Note that only sct.grab() can capture a subregion on the screen provided a bounding box, but requires a monitor, unlike sct.shot() / sct.save().
    with mss.mss() as sct2:  # TODO: workaround for the thread unsafe issue https://github.com/BoboTiG/python-mss/issues/273
        sct_img = sct2.grab(screenregion)  # grab screenshot of the region
    # Convert to a PIL Image (else we can't show it on screen)
    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    # Save screenshot if in debug mode
    if config['USER']['debug'] == 'True':
        # Get path to temporary image file (need to save to a file to pass onto Tesseract, there's no other way to directly pipe)
        imgtemppath = 'debugtranslate.png'
        # Save to the picture file
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=imgtemppath)

    # Preprocess screenshot to improve OCR accuracy (particularly over translucent backgrounds)
    if config['USER']['preprocessing'] == 'True':
        # Convert to greyscale and upscale image to artificially increase resolution
        img = img.convert('L').resize((2 * _ for _ in img.size), resample=Image.LANCZOS)
        if config['USER']['preprocessing_filters'] != 'None':
            # Load up the list of filters to apply, from the config file
            # The filters should be part of PILLOW.ImageFilter
            imfilters = ast.literal_eval(config['USER']['preprocessing_filters'])
            # Apply filters (remove translucent background, increase contrast of the letters, etc)
            for imfilter in imfilters:
                img = img.filter(getattr(ImageFilter, imfilter))
        if config['USER']['preprocessing_binarize_threshold'] != 'None':
            # Binarize
            #fn = lambda x : 255 if x > thresh else 0  # real binarization
            fn = lambda p : p > thresh and p + 100  # fake binarization, we simply add 100 to the pixels above the threshold, this helps keep some of the variation in the pixels intensities which can be helpful to recognize the letters, from: https://stackoverflow.com/questions/51688973/image-preprocessing-for-ocr-tessaract
            thresh = int(config['USER']['preprocessing_binarize_threshold'])
            try:
                img = img.point(fn, mode='1')
            except ValueError as exc:
                # Exception when the screenshot is too small
                pass
        if config['USER']['preprocessing_invert'] == 'True':
            # Invert image so that the text is black and background white, this works better with Tesseract according to doc: https://tesseract-ocr.github.io/tessdoc/ImproveQuality
            img = ImageMath.eval('255 - (a)', a=img.convert('1')).convert('L')  # convert back to greyscale, else can't save a binary image and is buggy for PILLOW and maybe for Tesseract, so better be safe

    # Save preprocessed screenshot if in debug mode
    preview_on = TBox.previewer is not None and TBox.previewer.shown
    if config['USER']['debug'] == 'True' or preview_on:
        # Get path to temporary image file
        imgtemppath = 'debugtranslatepreproc.png'
        # Save to the picture file
        img.save(imgtemppath, 'PNG')
        # Refresh OCR preview image is the preview window is there
        # Since we are using threads, it's difficult to pass objects between threads, so as a workaround we save into a temporary file and reopen it in the OCR Preview window thread
        if preview_on:
            TBox.previewer.preview(imgtemppath)

    # Tesseract OCR to extract text, directly from a PIL image object thanks to the pytesseract wrapper. Otherwise, we would need to save to a temporary file to pass onto Tesseract, as there's no other way to directly pipe without pytesseract
    ocrtext = pytesseract.image_to_string(img, lang=langsource_ocr, nice=1)
    # TODO: use image_to_boxes or image_to_osd or image_to_data to get position of strings and place them back in place on a screenshot, similarly to what Universal Game Translator does
    if not ocrtext.strip():
        show_errorbox('No text found by OCR! Make sure your capture region is properly set!')
        return
    if config['USER']['debug'] == 'True':
        print('OCR\'ed text:')
        print(ocrtext)
    #os.system('tesseract -l {imgpath} {srclang} {outputtxt}'.format(imgpath=os.path.abspath(imgtemppath), srclang=langsource, outputtxt='test'))  # alternative way to generate the OCR, by commandline call directly

    # Translate using a machine translator
    if config['USER']['ocr_only'] == 'True':
        # Do not translate if ocr_only is enabled
        transtext = ''
    else:
        if config['USER']['remove_line_returns'] == 'True':
            # If enabled, remove line returns automatically, so that we consider all sentences to be one (this can help the translator make more sense because it will have more context to work with).
            ocrtext = ocrtext.replace("\n", "")
        # Send ocr text to the machine translator
        transtext = translate_any(config, ocrtext, langsource_trans, langtarget)

    if config['USER']['debug'] == 'True':
        print('Translated text:')
        print(transtext)

    # Save OCR'ed text and translation in logs if specified. The same datetime will be written for both, so that they can be matched externally.
    curdatetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if config['USER']['log_ocr'] != 'None':
        with codecs.open(config['USER']['log_ocr'], 'a', 'utf-8-sig') as f:
            f.write("-> OCR at %s:\n" % curdatetime)
            f.write(ocrtext)
            f.write("\n---------------------\n")
    if config['USER']['log_translation'] != 'None':
        with codecs.open(config['USER']['log_translation'], 'a', 'utf-8-sig') as f:
            f.write("-> Translation at %s:\n" % curdatetime)
            f.write(transtext)
            f.write("\n---------------------\n")

    TBox.update_text(ocrtext, transtext)

def selectAndTranslateRegion(sct, RegionSelector, TBox, config, config_internal):
    """Wrapper to select a region and translate it directly after, this streamlines the process"""
    selectRegion(sct, RegionSelector, config, config_internal, quitOnSelect=True)
    translateRegion(sct, TBox, config, config_internal)

def show_errorbox(msg):
    """Show an error box"""
    root = tkinter.Toplevel()  # when we want to display another window on top of the root, such as an error box, then a TopLevel() is to be used instead of Tk(), but do not ever destroy these children windows, only hide them when done, so we can reuse and show them later
    root.withdraw()
    messagebox.showerror("Error", msg)
    # DEPRECATED: do not destroy anymore as we prefer now to keep windows always loaded and just updated, this avoids memory leaks with Tkinter (as it seems it's not possible to completely destroy Tkinter in a thread)
    #root.quit()
    #root.destroy()  # need to manually destroy the main window, else tk shows an empty window alongside the messagebox... Solution from: https://stackoverflow.com/a/57523108/1121352

def show_errorbox_exception(msg):
    """Show both an error box and raise an Exception"""
    show_errorbox(msg)
    raise Exception(msg)

def read_config(configFileArg=None, default_path='config.ini'):
    """Read a config file, either in the default path or in the provided path"""
    # Path to current script (to find the config file)
    curpath = os.path.dirname(os.path.abspath(__file__))
    # Load config file
    config = configparser.ConfigParser()
    if configFileArg:
        # Specified by user
        configFile = os.path.abspath(configFileArg)
    else:
        # Default path
        configFile = os.path.join(curpath, default_path)
    # Check the path exists
    if not os.path.exists(configFile):
        show_errorbox_exception('Specified configuration file (%s) does not exist!' % configFile)
    # Load up the config file in memory
    config.read(configFile)
    # Add an attribute to the config object to store the fullpath, so that we can overwrite the config file later
    config.fullpath = configFile
    # Return the fully loaded config file
    return config

class OCRPreviewer(threading.Thread):
    """Display small window of the size of the input image, and refresh it anytime by supplying a new image"""
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)  # always close thread along with parent process
        self.start()

    def run(self):
        # Create a Toplevel() dialog window, we can create multiple ones
        root = tkinter.Toplevel()  # use Toplevel() instead of Tk() to reopen the same dialog multiple times and to avoid the pyimage2 does not exist error, see also: https://github.com/dangillet/PythonFaqFr/blob/master/doc/tkinter.md and https://stackoverflow.com/questions/39458318/how-to-allow-a-tkinter-window-to-be-opened-multiple-times and https://stackoverflow.com/questions/26097811/image-pyimage2-doesnt-exist -- but then there are issues with this approach, so we want each window to be separated and not interact together directly but only indirectly through files such as config files and images: https://stackoverflow.com/questions/45799121/runtimeerror-calling-tcl-from-different-appartment-tkinter-and-threading
        self.root = root
        # Create empty canvas
        self.canvas = None
        # Create empty photoimage for reuse
        self.photoimage = None
        # Save current window state (shown or hidden?)
        self.shown = False
        # Allow to be resizable
        root.resizable(True, True)
        # Set title
        root.title("OCR preview")
        # Default size
        root.geometry('300x300')
        # hide root dialog
        root.overrideredirect(1)
        root.withdraw()
        # Launch the window
        # self.root.mainloop()  # unnecessary when there is already another Tk() root, which here is the TranslationBox!

    def preview(self, image_path):
        """Load an image and display in the window, delete any previous image in the canvas, and resize the window to the image size"""
        # Open image using Pillow
        pilImage = Image.open(image_path)
        # Get screen size
        w, h = pilImage.size
        # Set canvas to be fullscreen
        self.root.geometry("%dx%d+0+0" % (w, h))
        # Initialize/reset canvas
        if self.canvas is not None:
            # Clear and reuse canvas if previously created
            canvas = self.canvas
            canvas.delete('all')
        else:
            # Else create it
            canvas = tkinter.Canvas(self.root,width=w,height=h)  # could alternatively use a Label? https://www.tutorialspoint.com/how-can-i-display-an-image-using-pillow-in-tkinter
            self.canvas = canvas
        # Prepare the canvas to load the screenshot image supplied as argument in pilImage
        canvas.pack()
        canvas.configure(background='black')
        if self.photoimage is not None:
            del self.photoimage
        image = ImageTk.PhotoImage(pilImage)
        self.photoimage = image
        #else:
        #    image = self.photoimage.paste(pilImage)
        imagesprite = canvas.create_image(w/2,h/2,image=image)

    def show(self):
        # Show dialog if it was closed/hidden
        self.root.deiconify()  # opposite of .withdraw()
        self.shown = True

    def hide(self):
        self.root.withdraw()
        self.shown = False

    def switch_visibility(self):
        """Display window is currently hidden, and inversely"""
        if self.shown:
            self.hide()
        else:
            self.show()

    def destroy(self):
        self.root.destroy()

### Main program
def main():
    # Commandline arguments
    parser = optparse.OptionParser()
    parser.add_option("-c", "--config", dest="config", default=None,
                        help="Path to the config file with user specified parameters, will be read-only, not modified by the program, and can be modified on-the-fly by user (default: config.ini)", metavar="FILE")
    parser.add_option("--config_internal", dest="config_internal", default=None,
                        help="Path to the internal config file, where temporary data will be written such as selected window coordinates (default: config_internal.ini)", metavar="FILE")
    # Fetch commandline args
    (options, args) = parser.parse_args()
    configFileArg = options.config
    configFileIntArg = options.config_internal

    # Print description message on startup
    print('pyugt - Python Universal Game Translator v%s - started' % __version__)

    # Load up the config file in memory
    config = read_config(configFileArg, default_path='config.ini')
    config_internal = read_config(configFileIntArg, default_path='config_internal.ini')

    # Load config file into memory variables
    PATH_tesseract_bin = config['USER']['PATH_tesseract_bin']
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

    # Initialize GUI windows
    RegionSelector = showPILandSelect()
    TBox = TranslationBox(config, config_internal)
    OPreviewer = OCRPreviewer()
    TBox.previewer = OPreviewer  # attach the OCR Previewer to the translation box, so that we can call the previewer when translating

    # Set global hotkeys, loading from config file
    keyboard.add_hotkey(config['USER']['hotkey_set_region_capture'], selectRegion, args=(sct, RegionSelector, config, config_internal))  # Do NOT set suppress=True, else this may raise exceptions!
    print('Hit %s to set the region to capture.' % config['USER']['hotkey_set_region_capture'])
    keyboard.add_hotkey(config['USER']['hotkey_translate_region_capture'], translateRegion, args=(sct, TBox, config, config_internal))
    print('Hit %s to translate the region (make sure to close the translation window before requesting another one).' % config['USER']['hotkey_translate_region_capture'])
    keyboard.add_hotkey(config['USER']['hotkey_set_and_translate_region_capture'], selectAndTranslateRegion, args=(sct, RegionSelector, TBox, config, config_internal))
    print('Hit %s to set AND translate a region.' % config['USER']['hotkey_set_and_translate_region_capture'])
    keyboard.add_hotkey(config['USER']['hotkey_show_ocr_preview'], OPreviewer.switch_visibility)
    print('Hit %s to show/hide OCR preview.' % config['USER']['hotkey_show_ocr_preview'])

    # Main waiting loop (we wait for hotkeys to be pressed)
    print('Press CTRL+C or close this window to quit.')
    while 1:
        time.sleep(1)

    # Exit gracefully if no exception until this point
    return 0


if __name__ == "__main__":
    rtncode = main()
    sys.exit(rtncode)
