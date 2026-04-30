# imports from guizero
import time
from sqlite3 import Time

from guizero import App, Box, Text, PushButton, CheckBox, Slider
# configuration and the variables to track the state of the elevator system, and these would be used and updated by the stub functions and the frontend logic functions to track of the current state of the elevator system in the GUI, and then these would also be used to reflect the state in the GUI elements
floor_count = 4 
start_floor = 1   # the elevator would start here
DEFAULT_SPEED = 50    # the speed can be set to 0-100
current_floor   = start_floor
motor_speed     = DEFAULT_SPEED
is_running      = False   # i made it so that this would only be true while a sequence is running
#i included the stub functions are below
def stub_go_to_floor(floor: int) -> None:
    """
    STUB FUNCTION: this would just drive the motor until the elevator car would reach "floor"
    In the real implementation of the elevetor subsystem: send motor direction & run until floor sensor triggers.
    """
    print(f"[STUB] go_to_floor({floor}) called ~ motor would drive to floor {floor}")
def stub_home() -> None:
    """
    STUB FUNCTION: This would be meant to drive car downward (vertical) until the bottom limit switch actives, and then it would reset counter to 1
    In the real implementation of the elevetor subsystem: it would just reverse the motor until limit_switch_bottom.is_pressed, and then
    reset encoder/counter to bottom floor 1.
    """
    print("[STUB] home() called ~ the motor would now just drive down to limit switch")
def stub_get_current_floor() -> int:
    """
    STUB FUNCTION: return the value for the actual floor number from sensors (IR or ultrasonic).
    In the real implementation of the elevetor subsystem: it would just read GPIO sensor or encoder and return int floor number.
    This would just return the tracked software state as a fallback while hardware is absent.
    """
    print(f"[STUB] get_current_floor() ~ this would just be returning software state: {current_floor}")
    return current_floor # this is just a fallback to track the floor state in the GUI without any hardware link, in the real implementation after we connect to the hardware for the testbed, this would read from sensors/encoder instead
def stub_run_sequence(floors: list) -> None:
    """
    STUB FUNCTION: visit each floor in `floors` list in the order as selected
    In the real implementation of the elevetor subsystem: iterate and call go_to_floor for each and just waiting for
    arrival confirmation between each of the stops.
    """
    print(f"[STUB] run_sequence({floors}) called ~ this would just visit floors in order")
def stub_set_speed(value: int) -> None:
    """
    STUB FUNCTION: would pass the speed value from 0-100 to the motor controller for the Raspberry Pi.
    """
    print(f"[STUB] set_speed({value}) called ~ motor PWM would now just be set to {value}%")
def stub_stop() -> None:
    """
    STUB FUNCTION: this would immediately cuts the power to the motor power (just an emergency stop)
    """
    print("[STUB] stop() called ~ the motor power would now be cut immediately")
 #frontend logic functions are below and these would primarily cal the GUI stub functoiojns that are not connected to the backend yet 
def go_to_floor(floor: int) -> None:
    """I made this so that it would be called when a floor button is tapped."""
    global current_floor
    current_floor = floor
    
    stub_go_to_floor(floor)
    status_text.value = f"Stopped at floor {floor}"
    _refresh_indicator()
def home() -> None:
    """I made this so that it would be called to return elevator to floor 1."""
    global current_floor
    stub_home()
    current_floor = start_floor
    status_text.value = f"Stopped at floor {start_floor}"
    _refresh_indicator()
def emergency_stop() -> None:
    """I made this so that it would be called to cut the motor immediately and update status."""
    stub_stop()
    status_text.value = "EMERGENCY STOP — motor halted"
def run_sequence() -> None:
    """I made this so that it would be called to read checked floors from the Programming Panel and run the sequence."""
    selected=[]
    for floor_num,cb in floor_checkboxes.items(): 
        if cb.value==1: 
            selected.append(floor_num)
    if not selected: # if there isnt anything that is selected, then it can just return and not do anything, and also update the status text to indicate that no floors were selected in the calll to the function
        prog_status.value="No floors selected."
        return
    # This will sort ascending so the elevator visits floors iin logical order
    # Then its neccesary to sort the order to maintain efficiency
    selected.sort()
    prog_status.value=f"currently running: {selected}"
    stub_run_sequence(selected)

    # then I chose to update the  state of the gui to the last floor in the sequence
    global current_floor
    current_floor=selected[-1] # last one in the list is the last one that the elevator would visit, so it pretty much makes sense to update the current floor state to that one after the sequence is done
    status_text.value=f"The elevator car has stopped at floor {current_floor}"
    _refresh_indicator() # then I just refreshed the floor indicator strip to reflect the new floor that the elevator is at after the sequence is done
def on_speed_change(value)->None:
    """We would cal this whenever the speed slider moves in the GUI so that it is stayed up to date."""
    global motor_speed
    motor_speed=int(value) # the slider value is passed as a string, so I just converted it to an int for the motor speed state
    speed_label.value=f"speed: {motor_speed}%"
    stub_set_speed(motor_speed)
def _refresh_indicator() -> None:
    # Calculate delay between floors based on motor speed
    # Higher speed = shorter delay, lower speed = longer delay
    if motor_speed > 0:
        

        base_delay = 0.5 
        floor_delay = base_delay * (100 - motor_speed) / 100 + 0.05
    else:
        floor_delay = 2.0
    
    for floor_num, box in indicator_boxes.items(): 
        if floor_num == current_floor: 
            box.bg = "#2d6a4f"   
   
            time.sleep(floor_delay)
        else: box.bg = "#3a3a3a"   # I chose this to represent that it would be inactive in state, in other words represented as dark
def show_panel(panel_name: str) -> None:
    """This wouild hide all of hte panels nad then show the one that was requested"""
    prog_panel.hide()
    main_panel.hide()
    settings_panel.hide()
    if panel_name == "main": main_panel.show()
    elif panel_name == "prog": prog_panel.show()
    elif panel_name == "settings": settings_panel.show()



#UI (FROM GUI ZERO) and this is where the actual GUI layout and design is created, and then the functions above are called when the buttons/sliders are interacted with by the user.
app=App(title="OCC Testbed Final Version GUI", width=420, height=480, bg="#1e1e1e") # this was adjusted from trial and error but can be changed layer for the dimensions/selection
nav_box =Box(app,width="fill", height=70, layout="grid") # this was adjusted from trial and error but can be changed layer for the dimensions/selection
btn_nav_main=PushButton(nav_box,text="Main", grid=[0, 0], width=10, height=2, command=lambda:show_panel("main"))
 #the lambda function is needed to create a closure that captures the current value of the panel name when the button is created, otherwise it would just call show_panel with the last value of panel_name in the loop (which would be "settings" in this case) for all buttons 
btn_nav_prog=PushButton(nav_box,text="Program", grid=[1, 0], width=10, height=2,command=lambda: show_panel("prog"))
btn_nav_settings=PushButton(nav_box,text="Settings", grid=[2, 0], width=10, height=2, command=lambda: show_panel("settings"))
main_panel=Box(app,width="fill",height="fill", layout="auto")
indicator_strip=Box(main_panel, width=220, height=30, layout="grid")









indicator_boxes={}
for i in range(1, floor_count+1):    #this would be meant to fill in the array using the loop
    col=i-1
    b=Box(indicator_strip,width=50,height=25,grid=[col, 0])
    b.bg = "#2d6a4f" if i == start_floor else "#3a3a3a"
    Text(b, text=f"F{i}", size=9, color="white")
    indicator_boxes[i] = b
Text(main_panel, text="")  # spacer (i added this because I figured that it was very crammed together before
# Floor buttons (Floor N down to Floor 1, top to bottom)
for i in range(floor_count, 0, -1):
    PushButton(main_panel,text=f"Floor {i}",width=20,command=lambda f=i: go_to_floor(f))
Text(main_panel ,text="")  # i searched up online how to add a spacer in guizero and it said that you can just add an empty text element, so I added this as a spacer between the floor buttons and the status text below
status_text=Text(main_panel,text=f"Stopped at floor {start_floor}", color="white", size=11)
Text(main_panel, text="")  # another one
PushButton(main_panel,text="Home",width=20,command=home)
Text(main_panel, text="")  # another spacer
PushButton(main_panel,text="Emergency Stop", width=20,command=emergency_stop
)
#prrogramming panel is below and this is where the user can select a sequence of floors for the elevator to visit, and then run that sequence, and the status text would update to show the current sequence that is being run, and then after the sequence is done, it would update the status text to show the new floor that the elevator is at after completing the sequence
prog_panel=Box(app,width="fill",height="fill",layout="auto")
Text(prog_panel,text="Please pick the order for the stop sequence:",color="white",size=11)
Text(prog_panel,text="") # for the spacer
floor_checkboxes = {} #this one would just store the order of the checkboxes and the info from it
for i in range(1,floor_count+1): #for the entire floor_count
    cb=CheckBox(prog_panel,text=f"Floor {i}",command=None) #no command because its just to select
    cb.text_color="white"
    floor_checkboxes[i]=cb #send to the dictionary to track the checkboxes and their corrresponding states
Text(prog_panel,text="") # another spacer to seperate the checkboxes from the run sequence button and the status text below
PushButton(prog_panel, text="Run the selected sequence",width=20,command=run_sequence)
Text(prog_panel,text="") # another spacer

prog_status =Text(prog_panel,text="",color="#aaaaaa",size=10)
prog_panel.hide()

#the settings panel

settings_panel=Box(app,width="fill",height="fill",layout="auto")
Text(settings_panel,text="Control the motor speed", color="white", size=11) #text for the speed slider
speed_slider=Slider(settings_panel,start=0,end=100,width=300,command=on_speed_change)
speed_slider.value = DEFAULT_SPEED # this is to set the initial position of the slider to match the default speed, otherwise it would just start at 0 and then the user would have to move it to the default speed position before they can change it, which would be a bit unintuitive in my opinion, so I just set it to start at the default speed value on startup
speed_label = Text(settings_panel,text=f"Speed: {DEFAULT_SPEED}%",color="#aaaaaa",size=10)
Text(settings_panel,text="")
Text(settings_panel,text="[This is a placeholder for any future features/iteraations]",color="#555555",size=9)
Text(settings_panel,text="e.g. acceleration ramp, floor offsets",color="#444444",size=9)
settings_panel.hide()


#i need to initalize the default speed so that the stub function and the slider are syncced on startup
stub_set_speed(DEFAULT_SPEED)


# this would finally render the app

app.display()