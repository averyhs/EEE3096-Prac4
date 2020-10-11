# Import libraries
import RPi.GPIO as GPIO
import random
import ES2EEPROMUtils
import os
import time

# some global variables that need to change as we run the program
end_of_game = None  # set if the user wins or ends the game
guess_val = 0  # current guess value
gen_val = None # random generated number
new_score = 0 # current score of current player
score_count = 0 # number of scores stored

# DEFINE THE PINS USED HERE
LED_value = [11, 13, 15]
LED_accuracy = 32
btn_submit = 16
btn_increase = 18
buzzer = 33
eeprom = ES2EEPROMUtils.ES2EEPROM()


# Print the game banner
def welcome():
    os.system('clear')
    print("  _   _                 _                  _____ _            __  __ _")
    print("| \ | |               | |                / ____| |          / _|/ _| |")
    print("|  \| |_   _ _ __ ___ | |__   ___ _ __  | (___ | |__  _   _| |_| |_| | ___ ")
    print("| . ` | | | | '_ ` _ \| '_ \ / _ \ '__|  \___ \| '_ \| | | |  _|  _| |/ _ \\")
    print("| |\  | |_| | | | | | | |_) |  __/ |     ____) | | | | |_| | | | | | |  __/")
    print("|_| \_|\__,_|_| |_| |_|_.__/ \___|_|    |_____/|_| |_|\__,_|_| |_| |_|\___|")
    print("")
    print("Guess the number and immortalise your name in the High Score Hall of Fame!")


# Print the game menu
def menu():
    global end_of_game

    end_of_game = False

    option = input("Select an option:   H - View High Scores     P - Play Game       Q - Quit\n")
    option = option.upper()
    if option == "H":
        os.system('clear')
        print("HIGH SCORES!!")
        s_count, ss = fetch_scores()
        display_scores(s_count, ss)
        menu()
    elif option == "P":
        os.system('clear')
        print("Starting a new round!")
        print("Use the buttons on the Pi to make and submit your guess!")
        print("Press and hold the guess button to cancel your game")
        value = generate_number()

        # TEST: print gen_val
        print("gen_val = ", gen_val)

        while not end_of_game:
            pass
    elif option == "Q":
        print("Come back soon!")
        exit()
    else:
        print("Invalid option. Please select a valid one!")


def display_scores(count, raw_data):
    if count == 0:
        print("No scores yet")
        pass
    
    # print the scores to the screen in the expected format
    if count >= 3:
        print("There are {} scores. Here are the top 3!".format(count))
    
    # print out the scores in the required format
    r = count if(count<3) else 3

    for i in range(r):
        b = 4*i
        name = raw_data[b] + raw_data[b+1] + raw_data[b+2]
        print(i+1, "- ", name, "took", ord(raw_data[b+3]), "guesses")
    pass


# Setup Pins
def setup():
    global LED_pwm
    global buzzer_pwm

    # Setup board mode
    GPIO.setmode(GPIO.BOARD)

    # Setup regular GPIO
    GPIO.setup(LED_value, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(LED_accuracy, GPIO.OUT)
    GPIO.setup(buzzer, GPIO.OUT, initial=GPIO.LOW)
    
    GPIO.setup(btn_submit, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(btn_increase, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    # Setup PWM channels
    LED_pwm = GPIO.PWM(LED_accuracy, 50)
    buzzer_pwm = GPIO.PWM(buzzer, 50)
    
    # Setup debouncing and callbacks
    GPIO.add_event_detect(btn_submit, GPIO.FALLING, callback=btn_guess_pressed, bouncetime=200)
    GPIO.add_event_detect(btn_increase, GPIO.FALLING, callback=btn_increase_pressed, bouncetime=200)


# Load high scores
def fetch_scores():
    # Get number of scores
    count = eeprom.read_byte(0)

    # Get the scores
    scores = eeprom.read_block(1,4*count)

    # convert the codes back to ascii
    for i in range(0,4*count):
        scores[i] = chr(scores[i])

    # return back the results
    return count, scores


# Save high scores
def save_scores(nm, scr):
    # fetch scores
    count, raw = fetch_scores()

    # include new score
    raw.append(nm[0])
    raw.append(nm[1])
    raw.append(nm[2])
    raw.append(chr(scr)) # type consistency

    # update total amount of scores
    count += 1

    # sort
    # - make list with just score numbers
    num = []
    for i0 in range(0,count):
        num.append(raw[4*i0+3])

    # - sort num list
    num.sort()

    # - add score to list based on index of numeric
    scores = []
    for i1 in range(count):
        b = i1*4
        idx = num.index(raw[b+3])
        d = 4*idx

        num[idx] = None # prevent overwriting same score
        
        scores.insert(d, raw[b])
        scores.insert(d+1, raw[b+1])
        scores.insert(d+2, raw[b+2])
        scores.insert(d+3, raw[b+3])

    # cut off score list if it gets too long
    # (eeprom has 4096 words, but we start from block 1, so 4092)
    if len(scores) > 4092:
        scores = scores[:4092]

    # write score count
    eeprom.write_byte(0, count)

    # write new scores
    reg = 4
    for i2 in range(count*4):
        eeprom.write_byte(reg, ord(scores[i2]))
        reg += 1

# Generate guess number
def generate_number():
    global gen_val
    gen_val = random.randint(0, pow(2, 3)-1)
    return gen_val


# Increase button pressed
def btn_increase_pressed(channel):
    global guess_val
    
    # Increase the value shown on the LEDs
    guess_val += 1
    guess_val %= 8
    display_val()
    pass


# Guess button
def btn_guess_pressed(channel):
    global end_of_game, gen_val, LED_pwm, buzzer_pwm, new_score
   
    LED_pwm.start(0)
    buzzer_pwm.start(0)

    # If they've pressed and held the button, clear up the GPIO and take them back to the menu screen
    time.sleep(2)
    if not GPIO.input(btn_submit):
        end_of_game = True

    # Increase score
    new_score += 1

    # Compare the actual value with the user value displayed on the LEDs
    diff = abs(gen_val - guess_val)

    # if it's an exact guess
    if diff == 0:
        # - disable LEDs and buzzer
        LED_pwm.stop()
        buzzer_pwm.stop()
        GPIO.output(LED_accuracy, 0)
        GPIO.output(buzzer, 0)

        # - tell the user and prompt them for a name
        name = input("You guessed the number!\nEnter your name: ")
        name = name[:3] if (len(name)>3) else name # take only first 3 chars

        # - save score
        save_scores(name, new_score)

        # - end game
        end_of_game = True

    # Change the PWM LED
    # if it's close enough, adjust the buzzer
    # if it's an exact guess:
    # - Disable LEDs and Buzzer
    # - tell the user and prompt them for a name
    # - fetch all the scores
    # - add the new score
    # - sort the scores
    # - Store the scores back to the EEPROM, being sure to update the score count
    pass

def display_val():
    global guess_val

    if guess_val == 0:
        GPIO.output(LED_value, (0,0,0))
    if guess_val == 1:
        GPIO.output(LED_value, (0,0,1))
    if guess_val == 2:
        GPIO.output(LED_value, (0,1,0))
    if guess_val == 3:
        GPIO.output(LED_value, (0,1,1))
    if guess_val == 4:
        GPIO.output(LED_value, (1,0,0))
    if guess_val == 5:
        GPIO.output(LED_value, (1,0,1))
    if guess_val == 6:
        GPIO.output(LED_value, (1,1,0))
    if guess_val == 7:
        GPIO.output(LED_value, (1,1,1))

# LED Brightness
def accuracy_leds():
    # Set the brightness of the LED based on how close the guess is to the answer
    # - The % brightness should be directly proportional to the % "closeness"
    # - For example if the answer is 6 and a user guesses 4, the brightness should be at 4/6*100 = 66%
    # - If they guessed 7, the brightness would be at ((8-7)/(8-6)*100 = 50%
    pass

# Sound Buzzer
def trigger_buzzer():
    # The buzzer operates differently from the LED
    # While we want the brightness of the LED to change(duty cycle), we want the frequency of the buzzer to change
    # The buzzer duty cycle should be left at 50%
    # If the user is off by an absolute value of 3, the buzzer should sound once every second
    # If the user is off by an absolute value of 2, the buzzer should sound twice every second
    # If the user is off by an absolute value of 1, the buzzer should sound 4 times a second
    pass

def clean_all():
    global LED_pwm, buzzer_pwm, new_score

    # cleanup GPIO, incl pwm channels
    LED_pwm = None
    buzzer_pwm = None
    GPIO.cleanup()

    # set conditions right for new game
    end_of_game = False
    new_score = 0

if __name__ == "__main__":
    try:
        while True:
            setup()
            welcome()
            while True:
                menu()
                if end_of_game:
                    clean_all()
                    break # go back to top of outer loop

    except Exception as e:
        print(e)
    finally:
        GPIO.cleanup()
