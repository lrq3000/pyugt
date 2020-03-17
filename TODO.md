# TODO

* Explore tesseract osd extraction to see if it's possible to retain the position (and hence potentially overlaying the translated text over a screenshot of the game).
  
  Checkout https://tesseract-ocr.github.io/tessdoc/ImproveQuality sparse text with OSD mode may work better

* Find if a japanese -> english offline translator exists (if possible under opensource and cross-platform), to reduce the dependency on Google Translator.

* Add image preprocessing (to increase contrast, detect edges, etc) to improve Tesseract OCR? Maybe also use Waifu2x to upscale kanjis?
  
  TODO: try https://github.com/wwtg99/image_filter
  
  TODO: try (but will slow down a lot): https://gist.github.com/Tydus/987239fea966438d8a873fbb083240d6#file-waifu2x-py

* Use Travis-CI and AppVeyor to automatically build binaries across platforms?

* New shortcut to translate active window, using https://github.com/asweigart/pygetwindow on Windows (would be nice to find for Linux and MacOSX - there is a PR for MacOSX)
    See also:
    https://stackoverflow.com/questions/10266281/obtain-active-window-using-python
    https://stackoverflow.com/questions/12775136/get-window-position-and-size-in-python-with-xlib
    https://github.com/Pithikos/winlaunch

* BUG: when CTRL+F3 is used first (reuse previous region) as the first shortcut, and then CTRL+F2 is used, the program may fail because Tkinter root is first created in the thread, instead of the main app! We should initiate Tkinter root in main app first before anything!
