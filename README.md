# pyugt - Python Universal Game Translator

[![PyPI-Status](https://img.shields.io/pypi/v/pyugt.svg)](https://pypi.org/project/pyugt)
[![PyPI-Versions](https://img.shields.io/pypi/pyversions/pyugt.svg?logo=python&logoColor=white)](https://pypi.org/project/pyugt)
[![PyPI-Downloads](https://img.shields.io/pypi/dm/pyugt.svg?logo=python&logoColor=white)](https://pypi.org/project/pyugt)

pyugt is a python universal game translator: it takes screenshots from a region you select on your screen, uses OCR (via Tesseract v5) to extract the characters, then feeds them to a machine translator (Google Translate) to then show you a translated text.

Since it works directly on images, there is no need to hack the game or anything to access the text. It is also cross-platform (support for Windows and Linux and experimentally on MacOSX.

Here is a demo:
![demo](https://github.com/lrq3000/pyugt/raw/master/doc/demo.gif)

Of course, since the translation is done by a machine, don't expect a very nice translation, but for games where no translation is available, it can be sufficient to understand the gist and be able to play.

The software can also be useful to human translators, as it is possible to enable logging of OCR'ed text in the config file, so that all captured text will be saved in a log file that can later be used as the source for a manual translation.

The software is also not limited to games, but can be applied to anything that displays text on screen.

This software was inspired by the amazing work of Seth Robinson on [UGT (Universal Game Translator)](https://github.com/SethRobinson/UGT).

## How to install & update

1. First, install Tesseract v5, installers are provided by [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki). Make sure to install the additional languages you want to translate from (eg, Japanese).

2. Then install pyugt:
   
   * Either on Windows x64, there is a prepackaged binary you can [download here](https://github.com/lrq3000/pyugt/releases/download/v0.3.4/pyugt_v0.3.4_bin_win64.zip).
   
   * Either for other platform or if you want to run from sourcecode, you need to install a Python interpreter. [Anaconda](https://www.anaconda.com/distribution/) is a good one.
     
     Then, install this software:
     
     `pip install --upgrade pyugt`
     
     Or maybe what can be more easy if you want to edit the config file, is to download the archive from Github, unzip anywhere, cd in the folder and type:
     
     `python setup.py develop`
     
     Note the software was tested on Windows 10 x64 with Python 3.7 (Anaconda). It should also work on other Python versions and on Linux but this was not tested (please let me know if you try on Linux!).

## How to use

* First, you need to configure the config file `config.ini`. A sample config file is provided with the software that should work fine on Windows, but on other platforms or in some cases you may need to edit it, particularly to setup the path to the Tesseract binaries.
  The config file also allows you to change the hotkeys and the monitor to screenshot from, and a few other things such as the source and target languages (by default, the source is japanese and target is english).

* Then, you can launch the script from a terminal/console:

`pyugt`

or:

`python -m pyugt`

* Then, use the hotkey to select a region to capture from (default hotkey: `CTRL+SHIFT+F3`). The selected region does not need to be very precise, but need to contain the text to translate.

* Finally, use the hotkey to translate what is shown in the region (default: `CTRL+F3`). This will display a window with the original text and the translated text. Repeat as many times as you need, you don't need to reselect the region to translate again.

* Tip: if the software has difficulties in recognizing the characters (you get gibberish and non-letters characters instead of words), first try to redefine the region with CTRL+F2 and make sure the region includes all text with some margin but not too much of the background (the tighter around the text, the less the OCR will be confused by the background, this can help a lot!). You can use the region selection and translation hotkey to do both in a streamlined fashion (default: `CTRL+F2`).

* Tip2: Try to make the game screen bigger. The bigger the characters, the easier for the OCR to work.

* Tip3: You can specify the path to a config file by using the `-c` or `--config` argument: `pyugt -c <path_to_config_file>`

* Tip4: In the translation box, it's possible to manually edit the OCR'ed text and force a new translation by clicking on the "Translate again" button. This can be useful when the OCR has wrongly detected non-letters characters.

**IMPORTANT NOTE:** The software is still in alpha stage (and may forever stay in this state). It IS working, but sometimes the hotkeys glitch and they do not work anymore. If this happens, simply focus the Python console and hit `CTRL+C` to force quit the app, then launch it again. The selected region is saved in the config file, so you don't have to redo this step everytime.

## Options

Here is a sample configuration file, with comments for the various additional options (such as logs for the OCR'ed text and translated text):

```ini
[DEFAULT]
# Path to Tesseract v5 binary. Easily install it from UB Mannheim installers: https://github.com/UB-Mannheim/tesseract/wiki
path_tesseract_bin = C:\Program Files\Tesseract-OCR\tesseract.exe
# Source language to translate from, for OCR. Both the Optical Recognition Character and the translator will search specifically for strings in this language, this reduces the amount of false positives (eg, translating strings in other languages that are more prominent or bigger on-screen). Language code can be found inside Tesseract tessdata folder (depends on what languages you chose in the installer).
lang_source_ocr = jpn
# Source language to translate from, for Google Translate. Use Google Translate language codes here. Look at googletrans doc in googletrans.LANGUAGES: https://readthedocs.org/projects/py-googletrans/downloads/pdf/latest/
lang_source_trans = ja
# Target language to translate to. Must be a Google Translate language code (NOT a Tesseract code!).
lang_target = en
# Hotkey to set the region on screen to capture future screenshots from. The region does not need to be precise, but must contain the region where text is likely to be found.
hotkey_set_region_capture = ctrl+shift+F3
# Hotkey to translate from the selected region
hotkey_translate_region_capture = ctrl+F3
# Hotkey to set a region AND translate it directly on mouse click release. This is useful for games where the contrast between the text and background is bad (eg, transparent dialog box), so reselecting a tight region for each dialogue may yield better results, this is a faster way to do that with one shortcut instead of 2.
hotkey_set_and_translate_region_capture = ctrl+F2
# On which monitor the screen region capture should display? If you have only one screen, leave this to 0 (first monitor)
monitor = 0
# Save all OCR'ed text into a log file? Set a path or file name different than None to activate (exemple: log_ocr = log_ocr.txt). This can be very useful for human translators to gather game text data.
log_ocr = None
# Save all translated text into a log file? Set a path or file name different than None to activate (exemple: log_translation = log_trans.txt).
log_translation = None
# Show debug information
debug = False
```

## Shortcomings & advantages

Compared to UGT, the translated text is not overlaid over a screenshot of the original text. This could maybe be done as Tesseract provides some functions (`image_to_boxes()` or `image_to_osd()` or `image_to_data()`). PRs are very welcome if anyone would like to give it a try!

UGT can also directly select and translate the active window. We dropped this feature because it's platform dependent, so a region selection seemed like the most reliable and cross-platform way to implement screen capture, even if it adds one additional step.

On the other hand, there are several advantages to our approach:

* it's cross-platform (Windows & Linux currently, MacOSX could be supported if we find a python module to register global hotkeys on it),

* we use Tesseract so that OCR is done locally (instead of via the Google Cloud Vision API) so we only send text which is a lot smaller footprint and thus less expensive (generally free), and a big advantage is that it's possible to freely resize the game window to a bigger size, with bigger characters improving the OCR recognition, and also no downscaling/quality reduction is necessary since there is no image transfer,

* Regions can be selected, so that unnecessary screen objects that may confuse the OCR can be elimited with a carefully selected region,

* We enforce the source and target languages, so that both the OCR and translator know what to expect, instead of trying to autodetect, which may fail particularly when there are names that may be written in another language or character form (eg, not in Kanji).

## License

This software is made by Stephen Larroque and is published under the MIT Public License.
