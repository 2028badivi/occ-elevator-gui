# imports from guizero
import time
from sqlite3 import Time

from guizero import App, Box, Text, PushButton, CheckBox, Slider, Drawing
# configuration and the variables to track the state of the elevator system, and these would be used and updated by the stub functions and the frontend logic functions to track of the current state of the elevator system in the GUI, and then these would also be used to reflect the state in the GUI elements
floor_count = 4 
start_floor = 1   # the elevator would start here
DEFAULT_SPEED = 50    # the speed can be set to 0-100
current_floor   = start_floor
motor_speed     = DEFAULT_SPEED
is_running      = False   # i made it so that this would only be true while a sequence is running

# here are the vars for the visual simuilation to   track the gliding and sensor state
floor_coords={1: 320, 2: 240, 3: 160, 4: 80}    
car_y = floor_coords[start_floor]    





# i set these up to keep track of the state of the car and the sequence
target_floor = start_floor
sequence_queue = []
sequence_mode = False
pause_timer = 0






#i included the stub functions, which are below
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
    global target_floor, sequence_mode
    sequence_mode = False # it would cancel the sequence mode when a manual call is made (throgh the buttons)
    target_floor = floor





    # this is what would update the GUI and let the user know whats happening
    stub_go_to_floor(floor)
    status_text.value = f"Moving to floor {floor}..."






def home() -> None:
    """I made this so that it would be called to return elevator to floor 1."""
    global target_floor, sequence_mode
    sequence_mode = False
    stub_home()


    target_floor = start_floor
    status_text.value = f"Going to home: Stopped at floor {start_floor}"



def emergency_stop() -> None:
    """I made this so that it would be called to cut the motor immediately and update status."""
    global target_floor, sequence_mode
    sequence_mode = False
    




    # i set these to find the closest floor to the car
    nearest_floor = 1
    min_diff = 9999
    
    
    
    #iterate towards the floors using the y coordinates
    for f, y in floor_coords.items():
        diff = abs(car_y - y)
        if diff < min_diff:
            min_diff = diff
            nearest_floor = f


    # so now the closest floor is the target floor (with the closest one set to the current floor)
    
    target_floor = nearest_floor
    stub_stop()
    status_text.value = "EMERGENCY STOP, motor halted"



def run_sequence() -> None:
    
    """I made this so that it would be called to read checked floors from the Programming Panel and run the sequence."""
    global sequence_queue, sequence_mode, target_floor
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





    sequence_queue = selected
    sequence_mode = True
    if sequence_queue:
        target_floor = sequence_queue.pop(0)
        status_text.value = f"Right now moving to floor {target_floor}..."


def on_speed_change(value)->None:
    """We would cal this whenever the speed slider moves in the GUI so that it is stayed up to date."""
    global motor_speed
    motor_speed=int(value) # the slider value is passed as a string, so I just converted it to an int for the motor speed state
    speed_label.value=f"speed: {motor_speed}%"
    stub_set_speed(motor_speed)
def _refresh_indicator() -> None:
    # apprently if i set the color normally then it will block the event loop so i put it in a async function
    for floor_num, box in indicator_boxes.items(): 
        if floor_num == current_floor: 
            box.bg = "#2d6a4f"   
        else: box.bg = "#3a3a3a"   # I chose this to represent that it would be inactive in state, in other words represented as dark

# this is the code for the other visualizer and it will replace the delay with a glide call, it will still read from sensors
def draw_simulation() -> None:
    drawing.clear()
    


    # this one will draw the elevator shaft visual
    drawing.rectangle(30, 20, 110, 380, color="#1e1e1e", outline=True, outline_color="#555555")
    # vertical guide rails
    drawing.line(70, 20, 70, 380, color="#444444")
    


    any_sensor_active = False
    
    # this would iterate throuhh eahc of the floors sensors to render the sensor beams and the indictaor bulbs ( and the floor label text)
    for floor_num, fy in floor_coords.items():
        is_near = abs(car_y - fy) <= 15
        if is_near:
            any_sensor_active = True
            
        # sensor beam (this would be green if the car is detected there and  dim red otherwise)
        beam_color = "#00FF66" if is_near else "#442222"
        drawing.line(30, fy, 110, fy, color=beam_color)
        
        # indicator bulb (green if the car is detected there, dim red otherwise)
        light_color = "#00FF66" if is_near else "#333333"
        drawing.oval(125, fy - 6, 137, fy + 6, color=light_color)
        
        # floor label text (white if the car is detected there, dim red otherwise)
        text_color = "white" if is_near else "#aaaaaa"
        drawing.text(10, fy - 8, f"F{floor_num}", color=text_color, size=9)
        
    # this woudl update the physical sensor link staus bar
    if any_sensor_active:
        
        sensor_status_light.bg = "#00FF66"
        sensor_status_label.value = "the sensor is active"
        sensor_status_label.text_color = "#00FF66"



    else:
        
        sensor_status_light.bg = "#442222"
        sensor_status_label.value = "inactive sensor"
        sensor_status_label.text_color = "#aaaaaa"
        



    #this would draw the elevator car (just a box)
    
    #the outline lengths
    cx, cy = 70, car_y
    x1, y1 = cx - 18, cy - 20
    x2, y2 = cx + 18, cy + 20
    
    #this would colour the elevator car a cyan colour when its moving and green when it stops
    car_color = "#00bcd4" if abs(car_y - floor_coords[target_floor]) > 1.0 else "#2d6a4f"
    drawing.rectangle(x1, y1, x2, y2, color=car_color, outline=True, outline_color="white")




    # this is a simple direction indicator (with teh colors)
    
    if abs(car_y - floor_coords[target_floor]) > 1.0:
        


        dir_char = "▲" if car_y>floor_coords[target_floor] else "▼"



        drawing.text(cx - 5, cy - 8, dir_char, color="white",size=9)
    
    
    else:


        drawing.text(cx - 5, cy - 6, "●", color="white",size=7)






def glide_step() -> None:
    
    #the globals for status tracking of the car and stuffs


    global car_y, current_floor, target_floor, sequence_mode, sequence_queue, pause_timer
    


    if pause_timer > 0:

        # it will pause for the duration of the timer (not per frame)


        pause_timer -= 1
        return
        
    target_y = floor_coords[target_floor]
    


    if abs(car_y - target_y) > 1.0:

        if motor_speed > 0:

            step = max(0.5, (motor_speed / 100.0) * 6.0)

            if car_y < target_y:

                car_y += min(step, target_y - car_y)

            else:

                car_y -= min(step, car_y - target_y)


    else:
        if current_floor != target_floor:

            current_floor = target_floor

            status_text.value = f"Currently just stopped at floor {current_floor}"
            _refresh_indicator()
            
            if sequence_mode:
                if current_floor in floor_checkboxes:
                    floor_checkboxes[current_floor].value = 0
                

                if sequence_queue:
                    target_floor = sequence_queue.pop(0)
                    status_text.value = f"Currently on its way to floor {target_floor}..."
                    pause_timer = 40


                else:
                    sequence_mode = False
                    prog_status.value = ""
                    status_text.value = f"The elevator car has JUST stopped at floor {current_floor}"
                    
    draw_simulation()





def show_panel(panel_name: str) -> None:
    """This wouild hide all of hte panels nad then show the one that was requested"""
    prog_panel.hide()
    main_panel.hide()
    settings_panel.hide()
    if panel_name == "main": main_panel.show()
    elif panel_name == "prog": prog_panel.show()
    elif panel_name == "settings": settings_panel.show()



#UI (FROM GUI ZERO) and this is where the actual GUI layout and design is created, and then the functions above are called when the buttons/sliders are interacted with by the user.
app=App(title="OCC Testbed Final Version GUI", width=640, height=480, bg="#1e1e1e") # this was adjusted from trial and error but can be changed layer for the dimensions/selection



#the containers side by side so that the controls are on the left and the visualizer is on the right
controls_box = Box(app, align="left", width=420, height="fill")
visual_box = Box(app, align="right", width=220, height="fill")
visual_box.bg = "#121212"




nav_box =Box(controls_box,width="fill", height=70, layout="grid") # this was adjusted from trial and error but can be changed layer for the dimensions/selection
btn_nav_main=PushButton(nav_box,text="Main", grid=[0, 0], width=10, height=2, command=lambda:show_panel("main"))
 #the lamdba functin is needed to create a closure that capturees the current value of the panel name when the buton is created, otherwise it would just call show_panel with the last value of panel_name in the loop (which would be "settings" in this case) for all buttons 



btn_nav_prog=PushButton(nav_box,text="Program", grid=[1, 0], width=10, height=2,command=lambda: show_panel("prog"))
btn_nav_settings=PushButton(nav_box,text="Settings", grid=[2, 0], width=10, height=2, command=lambda: show_panel("settings"))


main_panel=Box(controls_box,width="fill",height="fill", layout="auto")



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
prog_panel=Box(controls_box,width="fill",height="fill",layout="auto")
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

settings_panel=Box(controls_box,width="fill",height="fill",layout="auto")
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


# this will setup the visual simulaiton componnets in the visual box
Text(visual_box, text="simulator", color="#00bcd4", size=10, bold=True)

sensor_status_box=Box(visual_box, width=180, height=30)
sensor_status_light=Box(sensor_status_box, align="left", width=12, height=12)
sensor_status_light.bg="#442222"
sensor_status_label=Text(sensor_status_box, align="left", text="  inactive sensor", color="#aaaaaa", size=9)

drawing=Drawing(visual_box, width=200, height=380)

#this will initalize the first state of the simulation, using the code from before
draw_simulation()

#this will periodically update the physical car coordinates at 60 FPS (so that it is stable.)
app.repeat(16, glide_step)





# this would finally render the app

app.display()

#im going to add the gpio code very soon but if i add that part then the gui would not compile/render because the code would be running on mac os and the pins are only connected to the pi whcih is not yet ready yet