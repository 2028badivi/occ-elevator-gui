


# imports from guizero
import time

from guizero import App, Box, Text, PushButton, CheckBox, Slider, Drawing

try:
    from gpiozero import LED, MCP3008, Motor
    from gpiozero.pins.pigpio import PiGPIOFactory
    GPIO_AVAILABLE = True
except Exception:
    GPIO_AVAILABLE = False





start_floor = 1
floor_count = 4
DEFAULT_SPEED = 50
current_floor = start_floor
motor_speed = DEFAULT_SPEED
is_running = False
pot_voltage = 0.0



# adc wiring and pinout
#physical pins (pi) to the mcp3008 (ADC)
#Pi MOSI  (GPIO10 physical 19) goes to MCP3008 DIN  pin 11
#Pi MISO  (GPIO9  physical 21) goes to MCP3008 DOUT pin 10
#Pi SCLK  (GPIO11 physical 23) goes to MCP3008 CLK  pin 12
#Pi CE0   (GPIO8  physical 24) goes to MCP3008 CS   pin 13
#Pi 3.3V  goes to MCP3008 VDD and VREF
#Pi GND   goes to MCP3008 AGND and DGND



ADC_VREF = 3.3
MCP3008_POT_CHANNEL = 4 
IR_SENSOR_CHANNELS = {1: 0, 2: 1, 3: 2, 4: 3}
IR_DETECT_THRESHOLD = 0.35 #we weould need to calibrate this
PINCHOMETER_THRESHOLDS = [ #also need to calibrate this too
    (0.85, 4),
    (0.60, 3),
    (0.35, 2),
    (0.00, 1),
]

# the motor H-bridge driver pins
MOTOR_DRIVER_IN1 = 17
MOTOR_DRIVER_IN2 = 18
FLOOR_LED_PINS = {1: 5, 2: 6, 3: 13, 4: 19}





class HardwareController:
    def __init__(self):




        self.current_speed = DEFAULT_SPEED
        self.target_floor = start_floor
        self.last_target = None




        self.is_gpio = GPIO_AVAILABLE
        self.motor = None
        self.pot = None
        self.ir_sensors = {}
        self.floor_leds = {}




        if self.is_gpio:


            try:
                factory = PiGPIOFactory()
                self.pot = MCP3008(channel=MCP3008_POT_CHANNEL, pin_factory=factory)
                self.motor = Motor(forward=MOTOR_DRIVER_IN1, backward=MOTOR_DRIVER_IN2, pwm=True, pin_factory=factory,)



                self.floor_leds = {floor: LED(pin, pin_factory=factory) for floor, pin in FLOOR_LED_PINS.items()}



                self.ir_sensors = {floor: MCP3008(channel=channel, pin_factory=factory)
                    for floor, channel in IR_SENSOR_CHANNELS.items()
                }



            except Exception as exc:

                print("[the hardware] GPIO has failed to start :( :", exc)
                self.is_gpio = False



    def read_pinchometer_voltage(self) -> float:
        if self.is_gpio and self.pot:
            try: return float(self.pot.value) * ADC_VREF
            except Exception: return pot_voltage
        return pot_voltage



    def get_floor_from_pinchometer(self, voltage: float) -> int:
        for threshold, floor in PINCHOMETER_THRESHOLDS:
            if voltage >= threshold:
                return floor
        return 1

    def detect_floor_from_ir(self) -> int | None:
        if not self.is_gpio:
            return None
        best_floor = None
        best_reading = IR_DETECT_THRESHOLD
        for floor, sensor in self.ir_sensors.items():
            try:
                reading = float(sensor.value)
            except Exception:
                reading = 0.0
            if reading > best_reading:
                best_reading = reading
                best_floor = floor
        return best_floor

    def get_current_floor(self) -> int:
        if not self.is_gpio:
            return start_floor
        ir_floor = self.detect_floor_from_ir()
        if ir_floor is not None:
            return ir_floor
        voltage = self.read_pinchometer_voltage()
        return self.get_floor_from_pinchometer(voltage)

    def update_floor_leds(self, active_floor: int) -> None:
        if not self.is_gpio: return
        for floor, led in self.floor_leds.items(): led.value = floor == active_floor

    def floor_presence(self) -> dict:
        presence = {}
        if self.is_gpio:
            for floor, sensor in self.ir_sensors.items():
                try:
                    presence[floor] = float(sensor.value) >= IR_DETECT_THRESHOLD
                except Exception:
                    presence[floor] = False
        else:
            presence = {floor: False for floor in IR_SENSOR_CHANNELS}
        return presence

    def move_toward(self, target_floor: int, speed: int) -> None:
        if not self.is_gpio or self.motor is None:
            return
        current = self.get_floor_from_pinchometer(self.read_pinchometer_voltage())
        duty = max(0.0, min(1.0, speed / 100.0))
        if target_floor > current:
            self.motor.forward(duty)
        elif target_floor < current:
            self.motor.backward(duty)
        else:
            self.stop()
        self.last_target = target_floor

    def stop(self) -> None:
        if not self.is_gpio:
            return
        if self.motor is not None:
            self.motor.stop()
        self.last_target = None


#to init
hardware = HardwareController()







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
    print(f"[HARDWARE] go_to_floor({floor}) called ~ target floor {floor}")
    hardware.target_floor = floor
    hardware.move_toward(floor, motor_speed)

def stub_home() -> None:
    """
    STUB FUNCTION: This would be meant to drive car downward (vertical) until the bottom limit switch actives, and then it would reset counter to 1
    In the real implementation of the elevetor subsystem: it would just reverse the motor until limit_switch_bottom.is_pressed, and then
    reset encoder/counter to bottom floor 1.
    """
    print("[HARDWARE] home() called ~ moving toward floor 1")
    hardware.target_floor = start_floor
    hardware.move_toward(start_floor, motor_speed)

def stub_get_current_floor() -> int:
    """
    STUB FUNCTION: return the value for the actual floor number from sensors.
    In the real implementation of the elevator subsystem: it would read IR floor beacons
    and fallback to the pinchometer position reading.
    """
    floor_from_ir = hardware.detect_floor_from_ir()
    if floor_from_ir is not None:
        print(f"[HARDWARE] get_current_floor() IR detected floor {floor_from_ir}")
        return floor_from_ir

    voltage = hardware.read_pinchometer_voltage()
    actual_floor = hardware.get_floor_from_pinchometer(voltage)
    print(
        f"[HARDWARE] get_current_floor() pinchometer={voltage:.2f} V => floor {actual_floor}"
    )
    return actual_floor

def stub_run_sequence(floors: list) -> None:
    """
    STUB FUNCTION: visit each floor in `floors` list in the order as selected
    In the real implementation of the elevetor subsystem: iterate and call go_to_floor for each and just waiting for
    arrival confirmation between each of the stops.
    """
    print(f"[HARDWARE] run_sequence({floors}) called ~ starting sequence")
    if floors:
        hardware.target_floor = floors[0]
        hardware.move_toward(floors[0], motor_speed)

def stub_set_speed(value: int) -> None:
    """
    STUB FUNCTION: would pass the speed value from 0-100 to the motor controller for the Raspberry Pi.
    """
    print(f"[HARDWARE] set_speed({value}) called ~ motor PWM would now just be set to {value}%")
    hardware.current_speed = value
    if hardware.target_floor is not None:
        hardware.move_toward(hardware.target_floor, value)

def stub_stop() -> None:
    """
    STUB FUNCTION: this would immediately cuts the power to the motor power (just an emergency stop)
    """
    print("[HARDWARE] stop() called ~ the motor power would now be cut immediately")
    hardware.stop()
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


#frontend gui code is below

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


    global car_y, current_floor, target_floor, sequence_mode, sequence_queue, pause_timer, pot_voltage
    
    # read sensor values from hardware
    pot_voltage = hardware.read_pinchometer_voltage()

    current_floor = hardware.get_current_floor()
    hardware.update_floor_leds(current_floor)

    floor_presence = hardware.floor_presence()




    if pause_timer > 0:

        # it will pause for the duration of the timer (not per frame)


        pause_timer -= 1
        return
        
    target_y = floor_coords[target_floor]
    
    if abs(car_y - target_y) > 1.0:

        if motor_speed > 0:

            #just to make sure that it is avialable
            if GPIO_AVAILABLE:
                hardware.move_toward(target_floor, motor_speed)

            step = max(0.5, (motor_speed / 100.0) * 6.0)

            if car_y < target_y:
                car_y += min(step, target_y - car_y)
            else:
                car_y -= min(step, car_y - target_y)

    else:
        hardware.stop()
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

    any_sensor_active = any(floor_presence.values())
    if any_sensor_active:
        sensor_status_light.bg = "#00FF66"
        sensor_status_label.value = "the sensor is active"
        sensor_status_label.text_color = "#00FF66"
    else:
        sensor_status_light.bg = "#442222"
        sensor_status_label.value = "inactive sensor"
        sensor_status_label.text_color = "#aaaaaa"

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