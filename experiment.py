__author__ = "Austin Hurst"

import os
import re
import random

import klibs
from klibs.KLConstants import TK_MS, TIMEOUT
from klibs import P
from klibs.KLUtilities import deg_to_px
from klibs.KLEventQueue import pump, flush
from klibs.KLUserInterface import any_key, ui_request, key_pressed, smart_sleep
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics import fill, flip, blit, clear, NumpySurface
from klibs.KLText import add_text_style
from klibs.KLExperiment import TrialException
from klibs.KLCommunication import message
from klibs.KLResponseListeners import KeypressListener
from klibs.KLTime import CountDown
from klibs.KLAudio import AudioClip

import sdl2
import numpy as np
import colorednoise

from gamepad import gamepad_init, button_pressed
from gamepad_usb import get_all_controllers
from KLGamepad import TriggerListener


# Define colours for the experiment
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
RED = (255, 0, 0, 255)


class CASTRedux(klibs.Experiment):

    def setup(self):
        
        # Stimulus sizes
        fixation_size = deg_to_px(0.5)
        fixation_thickness = deg_to_px(0.06, even=True)
        warning_cue_size = deg_to_px(1.75)
        warning_cue_thickness = deg_to_px(0.25)
        exo_cue_size = deg_to_px(1.0)
        fish_width = deg_to_px(2.0)
        arrow_width = deg_to_px(1.0)
        arrow_head_width = deg_to_px(0.33, even=True)
        arrow_tail_width = arrow_width - arrow_head_width
        arrow_head_thickness = deg_to_px(0.5)
        arrow_tail_thickness = deg_to_px(0.17)

        # Visual stimuli
        fish_path = os.path.join(P.image_dir, 'fish_left_neutral.png')
        self.fish_l = NumpySurface(fish_path, width=fish_width)
        self.fish_r = self.fish_l.copy().flip_x()
        self.fixation = kld.FixationCross(fixation_size, fixation_thickness, fill=BLACK)
        self.exo_cue = kld.Ellipse(exo_cue_size, fill=BLACK)
        self.warning_circle = kld.Annulus(
            warning_cue_size, warning_cue_thickness, fill=BLACK
        )
        self.warning_square = kld.Rectangle(
            warning_cue_size, stroke=[warning_cue_thickness, BLACK, klibs.STROKE_INNER]
        )
        self.arrow_l = kld.Arrow(
            arrow_tail_width, arrow_tail_thickness,
            arrow_head_width, arrow_head_thickness,
            fill=BLACK, rotation=180
        )
        self.arrow_r = kld.Arrow(
            arrow_tail_width, arrow_tail_thickness,
            arrow_head_width, arrow_head_thickness,
            fill=BLACK,
        )

        # Auditory stimuli
        self.noise_mono = PinkNoise(10.0, stereo=False, volume=0.1)
        self.noise_stereo = PinkNoise(1.0, stereo=True, volume=0.1)
        
        # Layout
        width_offset = deg_to_px(5.0)
        flanker_pad = deg_to_px(0.2)
        self.left_loc = (P.screen_c[0] - width_offset, P.screen_c[1])
        self.right_loc = (P.screen_c[0] + width_offset, P.screen_c[1])
        self.left_flanker_locs = []
        self.right_flanker_locs = []
        for x_loc, y_loc in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            x_offset = x_loc * (flanker_pad + self.fish_l.width)
            y_offset = y_loc * (flanker_pad + self.fish_l.height)
            self.left_flanker_locs.append(
                (self.left_loc[0] + x_offset, self.left_loc[1] + y_offset)
            )
            self.right_flanker_locs.append(
                (self.right_loc[0] + x_offset, self.right_loc[1] + y_offset)
            )

        # Font styles & text
        add_text_style('incorrect', '0.5deg', RED)
        add_text_style('block', '0.5deg', line_space=2.6)
        self.anticipatory_msg = message("Too soon!", 'incorrect')
            
        # Initialize feedback messages for practice block
        timeout_msg = message(
            "Too slow! Please try to respond more quickly."
        )
        incorrect_msg = message(
            "Incorrect response!\n"
            "Please pull the trigger on the same side the middle fish is facing.",
            align='center'
        )
        
        self.feedback_msgs = {'incorrect': incorrect_msg, 'timeout': timeout_msg}

        # If connected, try initializing game controller
        gamepad_init()
        self.gamepad = None
        controllers = get_all_controllers()
        if len(controllers):
            self.gamepad = controllers[0]
            self.gamepad.initialize()

        # Set up Response Collector to get keypress responses
        if self.gamepad:
            print("Using gamepad")
            self.resp_listener = TriggerListener(
                mapping = {'Left': 'left', 'Right': 'right'},
                gamepad = self.gamepad,
                threshold = 0.5,
                timeout = P.response_timeout / 1000
            )
        else:
            print("Using keyboard")
            self.resp_listener = KeypressListener(
                keymap = {'z': 'left', '/': 'right'},
                timeout = P.response_timeout / 1000
            )

        # Generate blocks of trials based on custom block structure
        self.last_block_type = None
        self.was_practicing = False
        self.block_number = 0

        if not P.skip_demos:
            self.general_demo()


    def block(self):

        # If this is the first block of a subtask, run its demo instructions
        if self.last_block_type != self.block_label:
            self.block_number += 1
            if not P.skip_demos:
                if self.block_label == "exo":
                    self.exo_demo()
                elif self.block_label == "endo":
                    self.endo_demo()

        # Show block message at start of every subtest and practice block
        block_msg = None
        if P.practicing:
            header = (
                "This is a practice block.\n"
                "During this block you will be given feedback for your responses."
            )
            block_msg = message(header, 'block', align="center")
        elif self.was_practicing or self.last_block_type != self.block_label:
            # If first non-practice block of subtest, show block start message
            header = "Block {0} of {1}\n".format(self.block_number, 4)
            header += "During this block, your attention will be directed by "
            if self.block_label == "exo":
                header += "brief flashes."
            else:
                header += "arrows."
            block_msg = message(header, 'block', align='center')
        self.last_block_type = self.block_label
        self.was_practicing = P.practicing

        if block_msg:
            message_interval = CountDown(1)
            while message_interval.counting():
                ui_request() # Allow quitting during loop
                fill()
                blit(block_msg, 8, (P.screen_c[0], P.screen_y*0.4))
                flip()
            flush()
            
            start_msg = message("Press any button to start.")
            fill()
            blit(block_msg, 8, (P.screen_c[0], P.screen_y*0.4))
            blit(start_msg, 5, [P.screen_c[0], P.screen_y*0.7])
            flip()
            wait_for_input(self.gamepad)
        else:
            # If second non-practice block of subtest, just show break prompt
            self.show_break_prompt()


    def trial_prep(self):
        
        # Determine location of target and flankers
        if self.target_location == "left":
            self.target_loc = self.left_loc
            self.flanker_locs = self.left_flanker_locs
        else:
            self.target_loc = self.right_loc
            self.flanker_locs = self.right_flanker_locs
        
        # Set central fish and flanker fish types
        if self.target_direction == "left":
            self.target = self.fish_l
            if self.flanker_type == "congruent":
                self.flanker = self.fish_l
            elif self.flanker_type == "incongruent":
                self.flanker = self.fish_r
            else:
                self.flanker = None
        else:
            self.target = self.fish_r
            if self.flanker_type == "congruent":
                self.flanker = self.fish_r
            elif self.flanker_type == "incongruent":
                self.flanker = self.fish_l
            else:
                self.flanker = None

        # Calculate the random non-aging fixation period for the trial
        fix_lambda = 1 / (P.fix_interval_mean - P.fix_interval_min)
        onset_delay_sec = random.expovariate(fix_lambda) + P.fix_interval_min
        while onset_delay_sec > P.fix_interval_max:
            # If delay is above max, regenerate until it isn't
            onset_delay_sec = random.expovariate(fix_lambda) + P.fix_interval_min
        self.onset_delay = int(onset_delay_sec * 1000) # Convert to msec
        
        # Add timecourse of events to EventManager
        self.soa = 200 if self.trial_type == "exo" else 1000
        self.evm.add_event('warning_on', self.onset_delay)
        self.evm.add_event('warning_off', 100, after='warning_on')
        self.evm.add_event('target_on', self.soa, after='warning_on')

        # Pause background noise and give participant a break every 24 trials
        if P.trial_number > 1 and ((P.trial_number - 1) % 24) == 0:
            self.show_break_prompt()

        # Start trial with stereo noise muted & mono noise on low volume
        self.init_background_noise()


    def trial(self):
        
        # Before warning onset, show fixation
        while self.evm.before('warning_on'):
            self.check_anticipatory()
            fill()
            self.draw_fixation()
            flip()

        # Initiate auditory alerting cue (if present for trial)
        if self.trial_type == 'exo':
            if self.alerting_trial:
                self.noise_stereo.volume = 1.0
            else:
                self.noise_stereo.volume = 0.1
            self.noise_mono.volume = 0.0
        elif self.trial_type == 'endo':
            if self.alerting_trial:
                self.noise_stereo.volume = 0.1
                self.noise_mono.volume = 0.0
        
        # Wait until the end of the warning period, then return noise to normal
        while self.evm.before('warning_off'):
            self.check_anticipatory()
            fill()
            self.draw_fixation()
            if self.trial_type == 'exo':
                self.draw_cues()
            flip()
        self.noise_mono.volume = 0.1
        self.noise_stereo.volume = 0.0

        while self.evm.before('target_on'):
            self.check_anticipatory()
            fill()
            self.draw_fixation()
            flip()
        
        # Draw target stimuli/flankers and enter response collection loop
        fill()
        self.draw_fixation()
        blit(self.target, 5, self.target_loc)
        if self.flanker_type != "none":
            for loc in self.flanker_locs:
                blit(self.flanker, 5, loc)
        flip()
        response, rt = self.resp_listener.collect()
        
        # If using gamepad, get max/final pressure on non-response trigger during the
        # response period as a measure of response competition
        nonresp_max, trig_max_l, trig_max_r = (0, 0, 0)
        nonresp_last, trig_last_l, trig_last_r = (0, 0, 0)
        if self.gamepad:
            for trig in self.resp_listener.raw_data:
                if trig.left > trig_max_l:
                    trig_max_l = trig.left
                if trig.right > trig_max_r:
                    trig_max_r = trig.right
                trig_last_l = trig.left
                trig_last_r = trig.right
            nonresp_max = trig_max_r if response == 'left' else trig_max_l
            nonresp_last = trig_last_r if response == 'left' else trig_last_l

        # Prepare response values for database
        accuracy = int(response == self.target_direction)
        if rt == TIMEOUT:
            response = 'NA'
            accuracy = 'NA'
            rt = 'NA'
            nonresp_max = 'NA'
            nonresp_last = 'NA'
        
        # If practice trial, show participant feedback for bad responses
        if P.practicing and response != self.target_direction:
            fill()
            if response == 'NA':
                blit(self.feedback_msgs['timeout'], 5, P.screen_c)
            else:
                blit(self.feedback_msgs['incorrect'], 5, P.screen_c)
            flip()
            wait_for_input(self.gamepad)
        
        # Otherwise, clear screen immediately after response and wait for trial end
        else:
            msg = "Too slow!" if rt == 'NA' else str(int(rt))
            feedback = message(msg)

            feedback_interval = CountDown(P.feedback_duration)
            while feedback_interval.counting():
                ui_request()
                fill()
                blit(feedback, 5, P.screen_c)
                flip()
        
        # Log recorded trial data to database
        return {
            "session": P.session_number,
            "block": P.block_number,
            "trial": P.trial_number,
            "practice": P.practicing,
            "trial_type": self.trial_type,
            "alerting_trial": self.alerting_trial, 
            "cue_type": self.cue_type,
            "target_direction": self.target_direction,
            "target_loc": self.target_location,
            "flanker_type": self.flanker_type,
            "onset_delay": self.onset_delay,
            "soa": self.soa,
            "response": response,
            "accuracy": accuracy,
            "rt": rt,
            "nonresp_max": nonresp_max,
            "nonresp_last": nonresp_last,
        }

    
    def clean_up(self):
        msg = message("You're all done!  Press any button to exit.")
        fill()
        blit(msg, 5, P.screen_c)
        flip()
        wait_for_input(gamepad=self.gamepad)


    def init_background_noise(self):
        # Start playback with stereo noise muted & mono noise on low volume
        self.noise_mono.volume = 0.1
        self.noise_stereo.volume = 0.0
        if not self.noise_mono.playing:
            self.noise_mono.play(loop=True)
            self.noise_stereo.play(loop=True)


    def draw_fixation(self):
        if self.trial_type == 'exo':
            blit(self.fixation, 5, P.screen_c)
        elif self.trial_type == 'endo':
            if self.alerting_trial:
                blit(self.warning_circle, 5, P.screen_c)
            else:
                blit(self.warning_square, 5, P.screen_c)
            if self.cue_type == 'valid':
                arrow = self.arrow_l if self.target_location == 'left' else self.arrow_r
                blit(arrow, 5, P.screen_c)
            if self.cue_type == 'invalid':
                arrow = self.arrow_r if self.target_location == 'left' else self.arrow_l
                blit(arrow, 5, P.screen_c)
            elif self.cue_type == 'none':
                pass


    def draw_cues(self):
        if self.cue_type == 'valid':
            loc = self.left_loc if self.target_location == 'left' else self.right_loc
            blit(self.exo_cue, 5, loc)
        if self.cue_type == 'invalid':
            loc = self.right_loc if self.target_location == 'left' else self.left_loc
            blit(self.exo_cue, 5, loc)
        elif self.cue_type == 'none':
            pass

    
    def check_anticipatory(self):
        # If any response before target onset, display error & recycle trial
        q = pump()
        ui_request(queue=q)
        if key_pressed(queue=q) or button_pressed(q) or trigger_pressed(q):
            feedback_interval = CountDown(P.feedback_duration)
            while feedback_interval.counting():
                ui_request()
                fill()
                blit(self.anticipatory_msg, 5, P.screen_c)
                flip()
            raise TrialException("Recycling trial!")


    def show_break_prompt(self):
        self.noise_mono.stop()
        self.noise_stereo.stop()
        msg1 = message("Take a break!")
        msg2 = message("Whenever you're ready, press any button to continue.")
        wait_msg(msg1, msg2, gamepad=self.gamepad)
        self.init_background_noise()


    def show_demo_text(self, msgs, stim_set, duration=1.0, wait=True, msg_y=None):
        msg_x = int(P.screen_x / 2)
        msg_y = int(P.screen_y * 0.1) if msg_y is None else msg_y
        half_space = deg_to_px(0.5)

        fill()
        if not isinstance(msgs, list):
            msg_y = int(P.screen_y * 0.15)
            msgs = [msgs]
        for msg in msgs:
            txt = message(msg, align="center")
            blit(txt, 8, (msg_x, msg_y))
            msg_y += txt.height + half_space
    
        for stim, locs in stim_set:
            if not isinstance(locs, list):
                locs = [locs]
            for loc in locs:
                blit(stim, 5, loc)
        flip()
        smart_sleep(duration * 1000)
        if wait:
            wait_for_input(self.gamepad)

    
    def sound_demo(self):
        self.init_background_noise()
        msg1 = message("Use the following buttons to demo the alerting sounds:")
        msg2 = message(
            ("(X) - Play the high-intensity noise change\n"
             "(Y) - Play the same-intensity noise change\n"
             "(A) - Continue the experiment"),
            align="left"
        )
        fill()
        blit(msg1, 5, (int(P.screen_x / 2), int(P.screen_y * 0.4)))
        blit(msg2, 8, P.screen_c)
        flip()

        done = False
        while not done:
            if self.gamepad:
                self.gamepad.update()
            q = pump()

            if button_or_key_pressed(q, "x"):
                # Demo loud alerting signal
                self.noise_stereo.volume = 1.0
                self.noise_mono.volume = 0.0
                smart_sleep(100)
                self.noise_mono.volume = 0.1
                self.noise_stereo.volume = 0.0

            elif button_or_key_pressed(q, "y"):
                # Demo isointense alerting signal
                self.noise_stereo.volume = 0.1
                self.noise_mono.volume = 0.0
                smart_sleep(100)
                self.noise_mono.volume = 0.1
                self.noise_stereo.volume = 0.0
            
            elif button_or_key_pressed(q, "a"):
                done = True
                break

    
    def general_demo(self):
        self.show_demo_text(
            "Welcome to the experiment! This tutorial will help explain the task.",
            [(self.fixation, P.screen_c)]
        )
        self.show_demo_text(
            "On each trial, a fish will appear on the left or right side of the screen.",
            [(self.fixation, P.screen_c), (self.fish_r, self.left_loc)]
        )
        self.show_demo_text(
            ["Sometimes the fish will be alone, sometimes it will be surrounded by friends.",
             ("Your job will be to identify which way the middle fish is facing, using the\n"
             "left and right triggers on the game controller.")],
            [(self.fixation, P.screen_c), (self.fish_l, self.right_loc),
             (self.fish_l, self.right_flanker_locs)]
        )
        self.show_demo_text(
            ("Note that sometimes the surrounding fish will be facing a different\n"
             "direction than the middle fish, so do your best to ignore them."),
            [(self.fixation, P.screen_c), (self.fish_l, self.right_loc),
             (self.fish_r, self.right_flanker_locs)
            ]
        )
        self.show_demo_text(
            ["Please try to respond quickly and accurately to the best of your ability.",
             ("Once you make a response, your reaction time will be shown\n"
             "briefly on the screen to let you know how you did.")],
            [(message("359"), P.screen_c)]
        )
        self.init_background_noise()
        self.show_demo_text(
            ("Throughout the experiment, there will be noise playing through the headphones.\n"
             "Please put on the headphones now and adjust the volume to a comfortable level."),
            [(self.fixation, P.screen_c)]
        )


    def exo_demo(self):

        def demo_exo_cue(right=False):
            fill()
            blit(self.fixation, 5, P.screen_c)
            blit(self.exo_cue, 5, self.right_loc if right else self.left_loc)
            flip()
            smart_sleep(100)

        self.init_background_noise()
        self.show_demo_text(
            ("For the next block of the experiment, a dot will flash at one of the two \n"
            "fish locations just before the fish appears."),
            [(self.fixation, P.screen_c)],
        )
        demo_exo_cue()
        fill()
        blit(self.fixation, 5, P.screen_c)
        flip()
        smart_sleep(100) # Fish appears 200ms after cue onset, so 100ms after cue end
        self.show_demo_text(
            ("The location of the flash is completely random and will not help\n"
            "you predict the location of the fish."),
            [(self.fixation, P.screen_c), (self.fish_r, self.right_loc)],
        )
        self.show_demo_text(
            ("When the flash occurs, you will also hear a change in the background noise\n"
            "to alert you that the fish is about to appear."),
            [(self.fixation, P.screen_c)],
        )
        self.show_demo_text(
            ["On some trials, the noise change will include a brief increase in volume.",
             "Press any button to hear an example."],
            [(self.fixation, P.screen_c)],
        )
        self.noise_stereo.volume = 1.0
        self.noise_mono.volume = 0.0
        demo_exo_cue(right=True)
        self.noise_mono.volume = 0.1
        self.noise_stereo.volume = 0.0
        self.show_demo_text(
            [("On other trials, the noise change will be the same volume as the "
              "background noise."),
             "Press any button to hear an example."],
            [(self.fixation, P.screen_c)],
        )
        self.noise_stereo.volume = 0.1
        self.noise_mono.volume = 0.0
        demo_exo_cue()
        self.noise_mono.volume = 0.1
        self.noise_stereo.volume = 0.0
        self.show_demo_text(
            ["Instructions complete!",
             ("Press (X) to repeat the instructions, (B) to hear the alerting sounds\n"
              "again, or (A) to continue with the experiment.")],
            [], duration=0.1, wait=False, msg_y=int(P.screen_y * 0.4)
        )
        done = False
        while not done:
            if self.gamepad:
                self.gamepad.update()
            q = pump()
            if button_or_key_pressed(q, "x"):
                self.exo_demo()
                done = True
            elif button_or_key_pressed(q, "b"):
                self.sound_demo()
                done = True
            elif button_or_key_pressed(q, "a"):
                done = True


    def endo_demo(self):
        self.init_background_noise()
        self.show_demo_text(
            ("For the next part of the experiment, there will be arrows in the middle\n"
             "of the screen to help you predict where the fish will appear."),
            [(self.warning_square, P.screen_c), (self.arrow_l, P.screen_c)],
            duration=2.0, wait=False
        )
        self.show_demo_text(
            ("For the next part of the experiment, there will be arrows in the middle\n"
             "of the screen to help you predict where the fish will appear."),
            [(self.warning_square, P.screen_c), (self.arrow_l, P.screen_c),
             (self.fish_r, self.left_loc)],
            duration = 0.5
        )
        self.show_demo_text(
            "These arrows won't always be accurate, but will be correct more often than not.",
            [(self.warning_square, P.screen_c), (self.arrow_r, P.screen_c),
             (self.fish_r, self.left_loc)
            ]
        )
        self.show_demo_text(
            ["On some trials, the arrow will be surrounded by a circle.",
             ("This means that there will be a slight change in the background noise\n"
             "to alert you when the fish is about to appear."),
             "Press any button to hear an example."],
            [(self.warning_circle, P.screen_c), (self.arrow_l, P.screen_c)]
        )
        self.noise_stereo.volume = 0.1
        self.noise_mono.volume = 0.0
        smart_sleep(100)
        self.noise_mono.volume = 0.1
        self.noise_stereo.volume = 0.0
        self.show_demo_text(
            ["On other trials, the arrow will be surrounded by a square.",
             "This means that you will not be alerted when the fish is about to appear."],
            [(self.warning_square, P.screen_c), (self.arrow_l, P.screen_c)]
        )
        self.show_demo_text(
            ["Instructions complete!",
             ("Press (X) to repeat the instructions, (B) to hear the alerting sounds\n"
              "again, or (A) to continue with the experiment.")],
            [], duration=0.1, wait=False, msg_y=int(P.screen_y * 0.4)
        )
        done = False
        while not done:
            if self.gamepad:
                self.gamepad.update()
            q = pump()
            if button_or_key_pressed(q, "x"):
                self.endo_demo()
                done = True
            elif button_or_key_pressed(q, "b"):
                self.sound_demo()
                done = True
            elif button_or_key_pressed(q, "a"):
                done = True



class PinkNoise(AudioClip):
    """An audio clip containing randomly-generated pink noise.

    Args:
        duration (float): The seconds of noise to generate.
        stereo (bool, optional): If True, generates different noise streams for
            the left and right channels. If False, the left and right channel
            noise will be identical. Defaults to False.
        volume (float, optional): The volume of the audio clip. Defaults to 1.0
            (max volume).

    """
    
    def __init__(self, duration, stereo=False, volume=1.0):
        left = self.generate_channel(duration)
        right = self.generate_channel(duration) if stereo else left
        noise = np.c_[left, right]
        super(PinkNoise, self).__init__(noise, volume)
        
    def generate_channel(self, duration):
        max_int = (2 ** 17) - 1 # 32767, which is the max/min value for a signed 16-bit int
        dtype = np.int16 # Default audio format for SDL_mixer is signed 16-bit integer
        sample_rate = 44100 / 2 # sample rate for each channel is 22050 kHz, so 44100 total.
        size = int(duration * sample_rate)
        
        arr = colorednoise.powerlaw_psd_gaussian(1.0, size)
        arr = (arr / max(abs(arr))) * max_int 
        
        return arr.astype(dtype)


def button_or_key_pressed(events, key=None):
    return button_pressed(events, key) or key_pressed(key, queue=events)


def wait_for_input(gamepad=None):
    valid_input = [
        sdl2.SDL_KEYDOWN,
        sdl2.SDL_MOUSEBUTTONDOWN,
        sdl2.SDL_CONTROLLERBUTTONDOWN,
    ]
    flush()
    user_input = False
    while not user_input:
        if gamepad:
            gamepad.update()
        q = pump()
        ui_request(queue=q)
        for event in q:
            if event.type in valid_input:
                user_input = True
                break


def trigger_pressed(queue, threshold=0.1):
    valid_axes = [
        sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT,
        sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT,
    ]
    pressed = False
    for e in queue:
        if e.type == sdl2.SDL_CONTROLLERAXISMOTION:
            if e.caxis.axis in valid_axes:
                if (e.caxis.value / 32767.0) > threshold:
                    pressed = True
                    break
    return pressed


def wait_msg(msg1, msg2, delay=1.0, gamepad=None):
    # Show first part of message and wait for the delay
    message_interval = CountDown(delay)
    while message_interval.counting():
        ui_request() # Allow quitting during loop
        fill()
        blit(msg1, 8, (P.screen_c[0], P.screen_y*0.4))
        flip()
    flush()
    
    # Show the second part of the message and wait for input
    fill()
    blit(msg1, 8, (P.screen_c[0], P.screen_y*0.4))
    blit(msg2, 5, [P.screen_c[0], P.screen_y*0.6])
    flip()
    wait_for_input(gamepad)
