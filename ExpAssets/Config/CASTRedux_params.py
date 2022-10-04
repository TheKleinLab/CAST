### Klibs Parameter overrides ###

#########################################
# Runtime Settings
#########################################
collect_demographics = True
manual_demographics_collection = False
manual_trial_generation = True
run_practice_blocks = True
multi_user = False
view_distance = 57 # in centimeters, 57cm = 1 deg of visual angle per cm of screen
allow_hidpi = True

#########################################
# Available Hardware
#########################################
eye_tracker_available = False
eye_tracking = False
    
#########################################
# Environment Aesthetic Defaults
#########################################
default_fill_color = (255, 255, 255)
default_color = (0, 0, 0, 255)
default_font_size = 0.5
default_font_unit = 'deg'
default_font_name = 'Hind-Medium'

#########################################
# EyeLink Settings
#########################################
manual_eyelink_setup = False
manual_eyelink_recording = False

saccadic_velocity_threshold = 20
saccadic_acceleration_threshold = 5000
saccadic_motion_threshold = 0.15

#########################################
# Experiment Structure
#########################################
multi_session_project = False
trials_per_block = 0
blocks_per_experiment = 1
table_defaults = {}
conditions = ['endo', 'exo']
default_condition = 'exo'

#########################################
# Development Mode Settings
#########################################
dm_auto_threshold = True
dm_trial_show_mouse = True
dm_ignore_local_overrides = False
dm_show_gaze_dot = True

#########################################
# Data Export Settings
#########################################
primary_table = "trials"
unique_identifier = "userhash"
exclude_data_cols = ["created"]
append_info_cols = ["random_seed"]
datafile_ext = ".txt"

#########################################
# PROJECT-SPECIFIC VARS
#########################################

skip_demos = False
max_trials_per_block = None

# Fixation durations are drawn from a non-aging exponential distribution.
# These parameters define the min/max/mean durations.
fix_interval_min = 1.0 # sec
fix_interval_mean = 2.0 # sec
fix_interval_max = 10.0 # sec

feedback_duration = 1.0 # sec
response_timeout = 1200 # ms
