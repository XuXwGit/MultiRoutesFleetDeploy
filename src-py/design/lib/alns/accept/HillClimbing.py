
from design.lib.alns import ALNS


class HillClimbing:
    """
    Hill climbing only accepts progressively better solutions, discarding those
    that result in a worse objective value.
    """

    def _is_better(self, new_obj: float, old_obj: float, optimization_direction: str) -> bool:
        if optimization_direction == "minimize":
            return new_obj < old_obj
        else:  # maximize
            return new_obj > old_obj

    def __call__(self, rng, best, current, candidate, optimization_direction):
        # return candidate.objective() <= current.objective()
        return self._is_better(candidate.objective(), current.objective(), optimization_direction)
