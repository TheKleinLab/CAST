import random
from copy import deepcopy
from collections import OrderedDict
from itertools import product


def is_iterable(x):
    return hasattr(x, "__iter__") and not hasattr(x, "upper")


class FactorSet(object):
    
    def __init__(self, factors=None):
        if factors is None:
            factors = {}
        self._factors = deepcopy(factors)
        
    def _get_combinations(self):            
        factor_names = list(self._factors.keys())
        factor_levels = [self._factors[f] for f in factor_names]
        factor_set = []
        for combination in product(*factor_levels):
            trial_dict = dict(zip(factor_names, combination))
            factor_set.append(trial_dict)
        return factor_set

    def override(self, factor_mask):
        """Creates a new copy of the factor set with a given set of overrides.

        All provided factor overrides must correspond to factors that currently
        exist within the set: this method only allows for modifying the levels
        of existing factors, not adding new factors.
        
        """
        err = "'{0}' is not the name of a factor in the set."
        new = deepcopy(self._factors)
        for factor in factor_mask.keys():
            if factor in self.names:
                new_levels = factor_mask[factor]
                if not is_iterable(new_levels):
                    new_levels = [new_levels]
                new[factor] = new_levels
            else:
                raise ValueError(err.format(factor))
        return FactorSet(new)
        
    @property
    def names(self):
        """list: The names of all factors within the set."""
        return list(self._factors.keys())

    @property
    def set_length(self):
        """int: The number of trials required for the full factor set."""
        return len(self._get_combinations())



class Block(object):
    """Defines a custom block of trials.

    """

    def __init__(self, factors, label=None, trials=None, practice=False):
        self.practice = practice
        self.label = label
        if not isinstance(factors, FactorSet):
            factors = FactorSet(factors)
        self._factors = factors
        self.trialcount = trials if trials else self._factors.set_length
    
    def get_trials(self, full_shuffle=False):
        """Generates a shuffled set of trials from the block.

        """
        trials = []
        while len(trials) < self.trialcount:
            new = self._factors._get_combinations()
            remaining = self.trialcount - len(trials)
            random.shuffle(new)
            if remaining < len(new):
                new = new[:remaining]
            trials += new

        if full_shuffle:
            random.shuffle(trials)

        return trials
        
    @property
    def factors(self):
        """list: The names of all trial factors used in the block."""
        return self._factors.names
