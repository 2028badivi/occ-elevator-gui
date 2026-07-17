Run:

```bash


gh repo clone https://github.com/2028badivi/occ-elevator-gui

cd occ-elevator-gui
python3 -m venv .venv


source /Users/<USER_ID>/<PATH_TO_CLONED_FOLDER>/.venv/bin/activate
./.venv/bin/python elevator_gui.py

```

The GUI should render in its own window. Please be aware of some potential version compatibility issues.

If you didn't previously install GUIzero, then you should do so in order for it to work. GUIzero is a framework for the Graphical User Interface (GUI):

```bash
sudo apt install guizero
```

or you can also do:

```bash
brew install python
pip3 install guizero
```

## Running on the Raspberry Pi 4B (Ubuntu 24.04)

This is the actual target hardware, so the real GPIO code path matters here
(on any other OS it just falls back to simulation-only mode).

```bash
sudo apt update
sudo apt install -y python3-tk python3-pip git   # python3-tk is required for guizero
pip3 install guizero gpiozero lgpio
```

`lgpio` is the pin backend gpiozero uses on Ubuntu - `RPi.GPIO` doesn't work
reliably here since Ubuntu handles GPIO access differently than Raspberry Pi
OS, and no pin factory is hardcoded in the code, so gpiozero auto-selects
`lgpio` on its own. No extra daemon (like `pigpiod`) needs to be installed or
running for this setup.
