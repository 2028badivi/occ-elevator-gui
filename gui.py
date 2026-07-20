# gui.py
# This is the file that actually builds the window shown on screen, using a
# library called guizero (a simpler wrapper around tkinter, the GUI toolkit
# that comes built into Python). All the buttons, sliders, and little
# drawings live here.
#
# This file doesn't do any of the "thinking" itself - it just calls functions
# from elevator_state.py (for the logic/math) and hardware.py (for the real
# motor/sensors) and displays whatever they report.

from guizero import App, Box, Text, PushButton, CheckBox, Slider, Drawing

import config
from elevator_state import ElevatorState, FLOOR_COORDS
from hardware import HardwareController

# these two objects are basically the "backend" of the whole app - one knows
# about the real hardware, the other knows about the simulated logic/position
hardware = HardwareController()
state = ElevatorState()
motor_speed = config.DEFAULT_SPEED  # starts at the default speed until the slider gets moved


def go_to_floor(floor: int) -> None:
    # runs whenever one of the "Floor 1/2/3/4" buttons is clicked
    state.set_target(floor)
    hardware.move_toward(floor, state.effective_speed_percent(motor_speed))
    status_text.value = f"Moving to floor {floor}..."


def home() -> None:
    # runs when the Home button is clicked, sends the elevator back to the start floor
    state.set_target(config.START_FLOOR)
    hardware.move_toward(config.START_FLOOR, state.effective_speed_percent(motor_speed))
    status_text.value = f"Going home: floor {config.START_FLOOR}"


def emergency_stop() -> None:
    # the big red "stop everything right now" button. figures out whichever
    # floor is closest to where the car currently is and treats that as the
    # new position, then cuts power to the motor immediately
    nearest_floor = state.nearest_floor_to_car()
    state.cancel(nearest_floor)
    hardware.stop()
    status_text.value = "EMERGENCY STOP - motor halted"


def run_sequence() -> None:
    # runs when "Run the selected sequence" is clicked on the Programming
    # panel. first, all the checkboxes get scanned to build a list of which
    # floors are actually checked
    selected = [floor for floor, cb in floor_checkboxes.items() if cb.value == 1]
    if not selected:
        # nothing was picked, so just show a message and bail out early
        prog_status.value = "No floors selected."
        return

    state.start_sequence(selected)
    prog_status.value = f"Running: {sorted(selected)}"
    hardware.move_toward(state.target_floor, state.effective_speed_percent(motor_speed))
    status_text.value = f"Moving to floor {state.target_floor}..."


def on_speed_change(value) -> None:
    # fires every time the speed slider gets dragged
    global motor_speed
    motor_speed = int(value)  # the slider passes its value as a string, so it gets converted to a number
    speed_label.value = f"Speed: {motor_speed}%"
    hardware.move_toward(state.target_floor, state.effective_speed_percent(motor_speed))


def _refresh_indicator() -> None:
    # updates the little colored boxes at the top showing which floor is
    # "active" right now (green = active floor, gray = not active)
    for floor_num, box in indicator_boxes.items():
        box.bg = "#2d6a4f" if floor_num == state.current_floor else "#3a3a3a"


def _update_sensor_status_bar(presence: dict) -> None:
    # updates the little light + text near the simulator showing whether ANY
    # of the real IR sensors are currently triggered. this used to be written
    # in two different places that could disagree with each other, so now
    # it's just this one function that everything calls.
    # (the colored light box shows active/inactive, so the text itself just
    # stays plain white instead of also changing color)
    active = any(presence.values())
    sensor_status_light.bg = "#00FF66" if active else "#442222"
    sensor_status_label.value = "sensor active" if active else "inactive sensor"


def _update_top_bar() -> None:
    # keeps the persistent status strip up to date - this one stays visible
    # no matter which panel (Main/Program/Settings) is currently showing, so
    # the important live numbers are never hidden by switching tabs
    hardware_status = "connected" if hardware.is_gpio else "simulation"
    top_status_label.value = (
        f"Floor {state.current_floor} -> {state.target_floor}"
        f"   |   Speed {motor_speed}%"
        f"   |   Hardware: {hardware_status}"
    )


def _update_diagnostics(pot_reading: dict, ir_readings: dict) -> None:
    # updates the little "Diagnostics" readout with the actual numbers coming
    # off the sensors, mostly handy for checking things are sane once the
    # real hardware is wired up. both the pot and (once uncommented) the IR
    # sensors are read through the same MCP3008 now, so the pot shows a clean
    # 0-100% straight from the ADC, and IR still shows as ON/off since the
    # sensors themselves are only ever two-level even though they're read as
    # an analog value
    pot_diagnostics_label.value = f"Pot: {pot_reading['fraction'] * 100:.0f}%"
    ir_diagnostics_label.value = "IR: " + "  ".join(
        f"F{floor} {'ON' if triggered else 'off'}" for floor, triggered in sorted(ir_readings.items())
    ) if ir_readings else "IR: (disabled for testing)"


def draw_simulation() -> None:
    # redraws the little visual "elevator shaft" on the right side of the
    # screen. this is PURELY visual - it doesn't change any state, it just
    # looks at the current state and draws a picture of it.
    #
    # NOTE: all the numbers below (like 30, 20, 110, 380) are the original
    # pixel positions this was designed at, back when the canvas was always a
    # fixed 200x380. now that the canvas size actually changes depending on
    # the screen (see DRAWING_SCALE near the bottom of this file), every
    # coordinate gets passed through sc() first, which multiplies it by that
    # scale factor so everything grows/shrinks together and nothing ends up
    # squished or floating in the wrong spot. state.car_y and FLOOR_COORDS
    # themselves are NOT scaled - those stay in the original "logical" units
    # that elevator_state.py's logic uses; scaling only happens right before
    # actually drawing things on screen.
    drawing.clear()  # wipe the canvas so everything can be drawn fresh

    # the outer shaft box and the vertical guide rail down the middle
    drawing.rectangle(sc(30), sc(20), sc(110), sc(380), color="#1e1e1e", outline=True, outline_color="#555555")
    drawing.line(sc(70), sc(20), sc(70), sc(380), color="#444444")

    # draw a little beam + light bulb + label for each floor
    for floor_num, fy in FLOOR_COORDS.items():
        is_near = abs(state.car_y - fy) <= 15  # is the car close enough to this floor to "light up"
        beam_color = "#00FF66" if is_near else "#442222"
        drawing.line(sc(30), sc(fy), sc(110), sc(fy), color=beam_color)

        light_color = "#00FF66" if is_near else "#333333"
        drawing.oval(sc(125), sc(fy - 6), sc(137), sc(fy + 6), color=light_color)

        # the beam/bulb already show near vs not-near, so the label text just stays white
        drawing.text(sc(10), sc(fy - 8), f"F{floor_num}", color="white", size=text_size(9))

    # draw the elevator car itself as a little box
    cx, cy = 70, state.car_y
    x1, y1 = cx - 18, cy - 20
    x2, y2 = cx + 18, cy + 20
    car_color = "#00bcd4" if not state.has_arrived() else "#2d6a4f"  # blue while moving, green once stopped
    drawing.rectangle(sc(x1), sc(y1), sc(x2), sc(y2), color=car_color, outline=True, outline_color="white")

    # little arrow (or dot if stopped) showing which way the car is heading
    if not state.has_arrived():
        target_y = FLOOR_COORDS[state.target_floor]
        dir_char = "▲" if state.car_y > target_y else "▼"
        drawing.text(sc(cx - 5), sc(cy - 8), dir_char, color="white", size=text_size(9))
    else:
        drawing.text(sc(cx - 5), sc(cy - 6), "●", color="white", size=text_size(7))


def glide_step() -> None:
    # this is the "main loop." it gets called automatically about 60 times a
    # second (see app.repeat near the bottom of this file). every time it
    # runs, it checks the real sensors, moves the simulated car a little bit,
    # checks whether anything arrived, and redraws the picture.
    #
    # note: the pot gets read ONCE per tick, through the MCP3008, and that
    # same reading is handed to both get_current_floor() and the diagnostics
    # display, instead of each of them triggering its own separate SPI read
    pot_reading = hardware.read_potentiometer()
    hardware_floor = hardware.get_current_floor(pot_reading)
    hardware.update_floor_leds(hardware_floor)
    presence = hardware.floor_presence()
    ir_readings = hardware.ir_raw_readings()

    if hardware.is_gpio:
        # the real motor safety checks only matter if real hardware is
        # actually hooked up - running the simulation on a laptop means
        # there's no motor to stall in the first place
        stalled_now = state.note_hardware_target(hardware_floor)
        if stalled_now:
            hardware.stop()
            status_text.value = f"FAULT: motor stall - floor {state.target_floor} not reached"
        elif not state.stalled:
            hardware.move_toward(state.target_floor, state.effective_speed_percent(motor_speed), pot_reading)

    if not state.stalled:
        # keeps animating the simulated car UNLESS a stall fault has been flagged
        state.step_car(motor_speed)

    if state.has_arrived() and state.on_arrival():
        # a brand new floor was just reached this frame, so everything updates
        _refresh_indicator()
        if state.sequence_mode:
            # unchecks the box for the floor just visited, and shows the next stop
            if state.current_floor in floor_checkboxes:
                floor_checkboxes[state.current_floor].value = 0
            status_text.value = f"On its way to floor {state.target_floor}..."
        elif state.sequence_queue == [] and not state.sequence_mode:
            # sequence is fully done (or this was just a normal single stop)
            prog_status.value = ""
            status_text.value = f"Stopped at floor {state.current_floor}"

    _update_sensor_status_bar(presence)
    _update_diagnostics(pot_reading, ir_readings)
    _update_top_bar()
    draw_simulation()


def show_panel(panel_name: str) -> None:
    # the "screens" (main / programming / settings) aren't separate windows,
    # they're just boxes that get shown/hidden one at a time to fake having
    # multiple pages
    prog_panel.hide()
    main_panel.hide()
    settings_panel.hide()
    if panel_name == "main":
        main_panel.show()
    elif panel_name == "prog":
        prog_panel.show()
    elif panel_name == "settings":
        settings_panel.show()

    # highlights whichever nav button matches the panel that's now showing,
    # so it's obvious at a glance which tab is active
    for name, button in nav_buttons.items():
        if name == panel_name:
            button.bg = ACCENT_COLOR
            button.text_color = "#1e1e1e"
        else:
            button.bg = "#333333"
            button.text_color = "white"


# ---------------------------------------------------------------------------
# everything below here just builds the actual window and all its widgets
# ---------------------------------------------------------------------------

# a single accent color used consistently for headers, the active nav tab,
# and the "primary action" button, so those all read as visually related
ACCENT_COLOR = "#00bcd4"
CARD_BG = "#242424"  # slightly lighter than the app background, for "card" panels

app = App(title="OCC Testbed Final Version GUI", width=640, height=480, bg="#1e1e1e")
# NOTE: fullscreen is deliberately NOT set here, right after creating an
# empty window. On some Linux window managers, toggling -fullscreen on a
# window before its widgets exist confuses the redraw pipeline - the window
# appears but stays blank until something (like closing it) forces a repaint.
# app.set_full_screen() is called at the very end of main(), after every
# widget below has already been built, which avoids that.

TOP_BAR_HEIGHT = 56

# this app used to be a fixed 640x480 window, so everything below was
# designed around that. now that it opens fullscreen, the REAL screen size
# gets used to scale things up to match, instead of leaving a tiny 640x480
# island of content surrounded by empty background.
screen_width = app.tk.winfo_screenwidth()
screen_height = app.tk.winfo_screenheight()

# the shaft simulator drawing was originally designed at 200 wide x 380 tall.
# that design gets scaled up a bit (keeping its proportions) so it isn't a
# tiny postage stamp on a big screen, but the growth is CAPPED - on a huge
# monitor, filling all the leftover height made everything (car, beams, text)
# look cartoonishly oversized. 1.6x was the sweet spot in testing.
DESIGN_DRAWING_WIDTH = 200
DESIGN_DRAWING_HEIGHT = 380
SIMULATOR_HEADER_HEIGHT = 140
MAX_DRAWING_SCALE = 1.6
available_height = screen_height - TOP_BAR_HEIGHT - SIMULATOR_HEADER_HEIGHT
uncapped_scale = max(DESIGN_DRAWING_HEIGHT, available_height) / DESIGN_DRAWING_HEIGHT
DRAWING_SCALE = min(uncapped_scale, MAX_DRAWING_SCALE)
drawing_height = round(DESIGN_DRAWING_HEIGHT * DRAWING_SCALE)
drawing_width = round(DESIGN_DRAWING_WIDTH * DRAWING_SCALE)


def sc(value):
    """Scales one of the original design-time pixel coordinates up to the real canvas size."""
    return round(value * DRAWING_SCALE)


def text_size(value):
    """Font sizes stay as designed - scaling them up with the shapes made them too big to read comfortably."""
    return value


# ------------------ Persistent top status bar ------------------
# stays visible no matter which panel (Main/Program/Settings) is showing, so
# the live floor/speed/hardware numbers are never hidden by switching tabs
top_bar = Box(app, align="top", width="fill", height=TOP_BAR_HEIGHT)
top_bar.bg = "#141414"
Text(top_bar, text="OCC Elevator Testbed", color=ACCENT_COLOR, size=14, align="left")
top_status_label = Text(top_bar, text="", color="white", size=10, align="right")

# splits the rest of the window into a left side (buttons/controls) and right
# side (the little visual simulator drawing). the visual side just needs to
# be big enough to fit the scaled-up drawing, and the controls side gets
# whatever width is left over on the actual screen. a thin divider sits
# between them just to make the split visually obvious.
DIVIDER_WIDTH = 2
visual_box_width = drawing_width + 40  # a bit of padding around the canvas
controls_box_width = screen_width - visual_box_width - DIVIDER_WIDTH

controls_box = Box(app, align="left", width=controls_box_width, height="fill")
divider = Box(app, align="left", width=DIVIDER_WIDTH, height="fill")
divider.bg = "#333333"
visual_box = Box(app, align="right", width=visual_box_width, height="fill")
visual_box.bg = "#121212"

# little helper so every button gets a consistent look instead of whatever
# the OS theme happens to default to (which on some systems is white text on
# a light button face - basically invisible). "kind" picks a color scheme:
# neutral (most buttons), primary (the main action on a page), or danger
# (anything that should visually stand out as high-stakes, like emergency stop)
BUTTON_STYLES = {
    "neutral": ("#333333", "white"),
    "primary": (ACCENT_COLOR, "#1e1e1e"),
    "danger": ("#8b2e2e", "white"),
}


def _style_button(button, kind="neutral"):
    bg, text_color = BUTTON_STYLES[kind]
    button.bg = bg
    button.text_color = text_color
    return button


# top nav bar with 3 buttons to switch between the "pages" - show_panel()
# highlights whichever one is active using nav_buttons
nav_box = Box(controls_box, width="fill", height=70, layout="grid")
nav_buttons = {
    "main": _style_button(PushButton(nav_box, text="Main", grid=[0, 0], width=10, height=2, command=lambda: show_panel("main"))),
    "prog": _style_button(PushButton(nav_box, text="Program", grid=[1, 0], width=10, height=2, command=lambda: show_panel("prog"))),
    "settings": _style_button(PushButton(nav_box, text="Settings", grid=[2, 0], width=10, height=2, command=lambda: show_panel("settings"))),
}

# ------------------ Main panel: floor buttons + status ------------------
main_panel = Box(controls_box, width="fill", height="fill", layout="auto")
Text(main_panel, text="Main Controls", color=ACCENT_COLOR, size=12)
Text(main_panel, text="")  # spacer

# little strip of colored boxes across the top showing which floor is active
indicator_strip = Box(main_panel, width="fill", height=30, layout="grid")
indicator_strip.bg = CARD_BG
indicator_boxes = {}
for i in range(1, config.FLOOR_COUNT + 1):
    b = Box(indicator_strip, width=50, height=25, grid=[i - 1, 0])
    b.bg = "#2d6a4f" if i == config.START_FLOOR else "#3a3a3a"
    Text(b, text=f"F{i}", size=9, color="white")
    indicator_boxes[i] = b

Text(main_panel, text="")  # empty spacer so things aren't crammed together
for i in range(config.FLOOR_COUNT, 0, -1):
    _style_button(PushButton(main_panel, text=f"Floor {i}", width=20, command=lambda f=i: go_to_floor(f)))
Text(main_panel, text="")  # spacer
status_text = Text(main_panel, text=f"Stopped at floor {config.START_FLOOR}", color="white", size=11)
Text(main_panel, text="")  # spacer
_style_button(PushButton(main_panel, text="Home", width=20, command=home))
Text(main_panel, text="")  # spacer
_style_button(PushButton(main_panel, text="Emergency Stop", width=20, command=emergency_stop), kind="danger")

# ------------------ Programming panel: pick + run a sequence ------------------
prog_panel = Box(controls_box, width="fill", height="fill", layout="auto")
Text(prog_panel, text="Program Sequence", color=ACCENT_COLOR, size=12)
Text(prog_panel, text="Pick the order for the stop sequence:", color="white", size=11)
Text(prog_panel, text="")  # spacer
floor_checkboxes = {}
for i in range(1, config.FLOOR_COUNT + 1):
    cb = CheckBox(prog_panel, text=f"Floor {i}")
    cb.text_color = "white"
    floor_checkboxes[i] = cb
Text(prog_panel, text="")  # spacer
_style_button(PushButton(prog_panel, text="Run the selected sequence", width=20, command=run_sequence), kind="primary")
Text(prog_panel, text="")  # spacer
prog_status = Text(prog_panel, text="", color="white", size=10)
prog_panel.hide()  # hidden until "Program" is clicked up top

# ------------------ Settings panel: motor speed slider ------------------
settings_panel = Box(controls_box, width="fill", height="fill", layout="auto")
Text(settings_panel, text="Settings", color=ACCENT_COLOR, size=12)
Text(settings_panel, text="Control the motor speed", color="white", size=11)
speed_slider = Slider(settings_panel, start=0, end=100, width=300, command=on_speed_change)
speed_slider.value = config.DEFAULT_SPEED  # starts the slider at the default so it's not just 0 on launch
speed_label = Text(settings_panel, text=f"Speed: {config.DEFAULT_SPEED}%", color="white", size=10)
Text(settings_panel, text="")
Text(settings_panel, text="[Placeholder for future features]", color="white", size=9)
Text(settings_panel, text="e.g. acceleration ramp, floor offsets", color="white", size=9)
settings_panel.hide()  # hidden until "Settings" is clicked up top

# ------------------ Right side: little visual elevator simulator ------------------
Text(visual_box, text="Simulator", color=ACCENT_COLOR, size=12)
sensor_status_box = Box(visual_box, width="fill", height=30)
sensor_status_box.bg = CARD_BG
sensor_status_light = Box(sensor_status_box, align="left", width=12, height=12)
sensor_status_light.bg = "#442222"
sensor_status_label = Text(sensor_status_box, align="left", text="  inactive sensor", color="white", size=9)
drawing = Drawing(visual_box, width=drawing_width, height=drawing_height)

# little card underneath the shaft drawing showing the raw sensor numbers -
# mostly useful for debugging/checking calibration once the real hardware is
# actually wired up, but also just makes the panel look more like a real
# diagnostics screen instead of only the cartoon shaft
diagnostics_box = Box(visual_box, width="fill", height="fill", layout="auto")
diagnostics_box.bg = CARD_BG
Text(diagnostics_box, text="")  # spacer
Text(diagnostics_box, text="Diagnostics", color=ACCENT_COLOR, size=11)  # bumped from 9 to 11 to stay visually distinct now that it's not bold
hardware_mode_label = Text(diagnostics_box, text="Hardware: --", color="white", size=8)
pot_diagnostics_label = Text(diagnostics_box, text="Pot: --", color="white", size=8)
ir_diagnostics_label = Text(diagnostics_box, text="IR: --", color="white", size=8)
hardware_mode_label.value = "Hardware: connected" if hardware.is_gpio else "Hardware: simulation only"

show_panel("main")  # sets the initial nav tab highlight to match the panel shown by default

draw_simulation()  # draws once immediately so the window doesn't start out blank
app.repeat(16, glide_step)  # keeps calling glide_step roughly every 16ms, which is about 60 times a second


def main() -> None:
    # fullscreen gets set here, right before displaying, now that every
    # widget already exists - see the NOTE near the App() creation above
    app.set_full_screen()
    # this is what actually opens the window and keeps it running. nothing
    # after this line runs until the window is closed
    app.display()


if __name__ == "__main__":
    main()
