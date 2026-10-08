"""A validated view of analysis controls; saved JSON and cache identities stay intact."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class AnalysisSettings:
    mode: str
    minimum: float
    maximum: float
    windows: int

    @classmethod
    def read(cls, settings):
        from modes import PROFILES
        try:
            options = cls(settings['mode'], float(settings['minimum']),
                          float(settings['maximum']), settings['windows'])
            coverage = float(settings.get('coverage', .35 if options.mode == 'Sports' else 1.))
            valid = (options.mode in PROFILES
                     and type(settings['minimum']) in (int,float)
                     and type(settings['maximum']) in (int,float)
                     and type(settings.get('coverage',1.)) in (int,float)
                     and math.isfinite(options.minimum) and math.isfinite(options.maximum)
                     and 0 < options.minimum <= options.maximum
                     and type(options.windows) is int and options.windows >= 1
                     and math.isfinite(coverage) and 0 < coverage <= 1
                     and type(settings['vision']) is bool and type(settings['semantic']) is bool)
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            raise ValueError('Choose valid video type, durations, coverage and review settings.')
        return options
