def calculate_parabolic_speed(start_floor: int, end_floor: int) -> tuple[list[float], float]:
    
    speeds_normalized = []

    delays_between_each_speed = 0.5 

    floors_to_travel = abs(end_floor - start_floor)
    
    num_of_speed_changes = 10 * floors_to_travel





    parabolic_portion = int(num_of_speed_changes * 0.80)
    
    for i in range(parabolic_portion):
        

        x = (i / (parabolic_portion - 1)) * 9.25 if parabolic_portion > 1 else 5

        raw_speed = (-1 * ((x - 5) ** 2) + 25) * 4 





        current_speed = max(0.0, min(100, raw_speed))

        speeds_normalized.append(round(current_speed, 2))




    starting_buffer_speed = speeds_normalized[-1]




    constant_portion = num_of_speed_changes - parabolic_portion
    
    for i in range(constant_portion):
        


        linear_speed = starting_buffer_speed * (1 - ((i + 1) / constant_portion))




        speeds_normalized.append(round(linear_speed, 2))




    return speeds_normalized, delays_between_each_speed







if __name__ == "__main__":



    speeds, delay = calculate_parabolic_speed(1, 4)
    


    print(f"Delay between changes: {delay} seconds")


    print(f"Total speed steps calculated: {len(speeds)}")
    

    print("\n")


    print(f"Start speed:  {speeds[0]}")

    print(f"First 3 steps: {speeds[1:4]}")

    print(f"Peak speed:    {max(speeds):.2f}")


    print(f"Last 3 steps:  {speeds[-4:-1]}")

    print(f"Final speed:   {speeds[-1]}")


    
    print(f"Entire thing: {speeds}")


