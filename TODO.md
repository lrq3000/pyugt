# TODO

* Version number in console output at program start (set `__version` in init.py and then in setup.py fetch version from init.py)

* Use argparse to allow to specify a config file at any location.

* Explore tesseract osd extraction to see if it's possible to retain the position (and hence potentially overlaying the translated text over a screenshot of the game).

* BUG: When no text is detected and an error messagebox is shown, the hotkeys stop working after, the program needs to be closed down and reopened. Maybe caused by a problem with the tkinter root not being closed/destroyed properly since we simply return.

* Find if a japanese -> english offline translator exists (if possible under opensource and cross-platform), to reduce the dependency on Google Translator.

