# TODO

* Explore tesseract osd extraction to see if it's possible to retain the position (and hence potentially overlaying the translated text over a screenshot of the game).

* BUG: When no text is detected and an error messagebox is shown, the hotkeys stop working after, the program needs to be closed down and reopened. Maybe caused by a problem with the tkinter root not being closed/destroyed properly since we simply return.

* Find if a japanese -> english offline translator exists (if possible under opensource and cross-platform), to reduce the dependency on Google Translator.

* Add image preprocessing (to increase contrast, detect edges, etc) to improve Tesseract OCR? Maybe also use Waifu2x to upscale kanjis?

* Use Travis-CI and AppVeyor to automatically build binaries across platforms?

* New shortcut to translate active window, using https://github.com/asweigart/pygetwindow on Windows (would be nice to find for Linux and MacOSX - there is a PR for MacOSX)
    See also:
    https://stackoverflow.com/questions/10266281/obtain-active-window-using-python
    https://stackoverflow.com/questions/12775136/get-window-position-and-size-in-python-with-xlib
    https://github.com/Pithikos/winlaunch
