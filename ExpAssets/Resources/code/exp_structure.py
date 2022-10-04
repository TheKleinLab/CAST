from klibs import P
from KLStructure import FactorSet, Block


# Define the different factor sets for exo and endo blocks

"""
Factors:

- alerting_trial: The type of auditory alert for the trial. If 'trial_type' == 'exo',
    'True' indicates a loud stereo alert and 'False' indicates a same-volume stereo
    alert. If 'trial_type' == 'endo', 'True' indicates a same-volume stereo alert,
    and 'False' indicates no auditory alert.

- cue_type: The type of cue ("valid" == same location as 'target_location')

- target_location: The location of the target fish

- target_direction: The direction of the target fish

- flanker_type: The type of flanker fish for the trial (same direction, opposite
    direction, or no flankers)

- trial_type: Whether the trial uses exogenous or endogenous visual cues.

"""

exo_factors = FactorSet({
    "alerting_trial": [True, False],
    "cue_type": ["valid", "invalid"], # 50% validity
    "target_location": ["left", "right"],
    "target_direction": ["left", "right"],
    "flanker_type": ["congruent", "incongruent", "none"],
    "trial_type": ["exo"],
})

endo_factors = exo_factors.override({
    "cue_type": ["valid", "valid", "invalid"], # 66% validity
    "trial_type": ["endo"],
})


# Define the block types and possible block sequences for the task

exo_practice = Block(exo_factors, label="exo", trials=24, practice=True)
exo = Block(exo_factors, label="exo")

endo_practice = Block(endo_factors, label="endo", trials=24, practice=True)
endo = Block(endo_factors, label="endo")

exo_first = [
    exo_practice, exo, exo, endo_practice, endo, endo,
    exo_practice, exo, exo, endo_practice, endo, endo,
]
endo_first = [
    endo_practice, endo, endo, exo_practice, exo, exo,
    endo_practice, endo, endo, exo_practice, exo, exo,
]


# Initialize the experiment structure based on the condition

if P.condition == "exo":
    structure = exo_first
else:
    structure = endo_first
