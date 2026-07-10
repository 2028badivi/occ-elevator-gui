# elevator_gui.py
# This is the file that gets run to start the app (python elevator_gui.py).
# all the real code lives in the other files
# (config.py, hardware.py, elevator_state.py, gui.py). This file just kicks
# everything off by calling main() from gui.py.

from gui import main

if __name__ == "__main__":
    # the if __name__ == "__main__" part just means "only run this if this
    # file was launched directly, not if some other file imported it"
    main()
