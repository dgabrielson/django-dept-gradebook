"""
FormulaLib -- working with formula objects.
"""
###############################################################
from __future__ import print_function, unicode_literals

from .add import AddCalc
from .bin import BinCalc
from .bonus import BonusCalc
from .bubblesheet import BubbleSheetCalc
from .ceil import CeilCalc
from .drop import DropCalc
from .iclicker import IClickerCalc, IClickerMoodleCalc
from .noop import NoopCalc
from .rank_weight import RankWeightCalc
from .registry import NoValueChange, formula_registry
from .sum import SumCalc
from .weight import WeightCalc

CALC_CLASSES = [
    AddCalc,
    BinCalc,
    BubbleSheetCalc,
    DropCalc,
    IClickerCalc,
    IClickerMoodleCalc,
    NoopCalc,
    SumCalc,
    WeightCalc,
    CeilCalc,
    BonusCalc,
    RankWeightCalc,
]

###############################################################
# This should be in app.ready()


def ready():
    for calc in CALC_CLASSES:
        formula_registry.register(calc)


###############################################################
