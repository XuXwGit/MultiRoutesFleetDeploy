import logging

import numpy as np

from .update import update

logger = logging.getLogger(__name__)


class SimulatedAnnealing:
    """
    The Simulated Annealing acceptance criterion. This criterion accepts a
    candidate solution :math:`s'` with probability :math:`\\exp(-\\delta / T)`,
    where :math:`\\delta = f(s') - f(s)` is the objective difference, and
    :math:`T` is the temperature parameter. :math:`T` is updated in each
    iteration as:

    .. math::

        T \\gets \\max \\{ T_\\text{end},~T - \\gamma \\}

    when ``method = 'linear'``, or

    .. math::

        T \\gets \\max \\{ T_\\text{end},~\\gamma T \\}

    when ``method = 'exponential'``. Initially, :math:`T` is set to
    :math:`T_\\text{start}`.

    Parameters
    ----------
    start_temp
        The initial temperature :math:`T_\\text{start} > 0`.
    end_temp
        The final temperature :math:`0 < T_\\text{end} \\le T_\\text{start}`.
    step
        The updating step :math:`\\gamma > 0`. For linear updating, this should
        be set to a small value like 1e-4. For exponential updating, this
        should be set to a value slightly below 1, like 0.9999.
    method
        The updating method, one of {'linear', 'exponential'}. Default
        'linear'.
    """

    def __init__(
        self,
        start_temp: float,
        end_temp: float,
        step: float,
        method: str = "linear",
    ):
        if not 0 < end_temp <= start_temp:
            raise ValueError("Must have 0 < end_temp <= start_temp.")

        if step <= 0:
            raise ValueError("Step must be positive.")

        if method == "exponential" and step > 1:
            raise ValueError("Exponential updating cannot have step > 1.")

        self._start_temp = start_temp
        self._end_temp = end_temp
        self._step = step
        self._method = method

        self._temp = start_temp

    @property
    def start_temp(self) -> float:
        return self._start_temp

    @property
    def end_temp(self) -> float:
        return self._end_temp

    @property
    def step(self) -> float:
        return self._step

    @property
    def method(self) -> str:
        return self._method

    def __call__(self, rng, best, current, candidate):
        # Always accept better
        diff = candidate.objective() - current.objective()

        if diff < 0:
            res = True
        else:  # maybe accept worse
            prob = min(1.0, max(0.0, float(rng.random()))) < 0.1
            res = diff == 0 or rng.random() < (
                1 if diff == 0 else (self._temp / diff)
            )

        self._temp = max(
            self.end_temp, update(self._temp, self.step, self.method)
        )

        return res

    @classmethod
    def autofit(
        cls,
        init_obj: float,
        worse: float,
        accept_prob: float,
        num_iters: int,
        method: str = "exponential",
    ) -> "SimulatedAnnealing":
        """
        Returns an SA object with initial temperature such that there is a
        ``accept_prob`` chance of selecting a solution up to ``worse`` percent
        worse than the initial solution. The step parameter is then chosen such
        that the temperature reaches 1 in ``num_iters`` iterations.

        This procedure was originally proposed by Ropke and Pisinger (2006),
        and has seen some use since - i.a. Roozbeh et al. (2018).

        Parameters
        ----------
        init_obj
            The initial solution objective.
        worse
            Percentage (in (0, 1), exclusive) the candidate solution may be
            worse than initial solution for it to be accepted with probability
            ``accept_prob``.
        accept_prob
            Initial acceptance probability (in [0, 1]) for a solution at most
            ``worse`` worse than the initial solution.
        num_iters
            Number of iterations the ALNS algorithm will run.
        method
            The updating method, one of {'linear', 'exponential'}. Default
            'exponential'.

        Raises
        ------
        ValueError
            When the parameters do not meet requirements.

        Returns
        -------
        SimulatedAnnealing
            An autofitted SimulatedAnnealing acceptance criterion.

        References
        ----------
        .. [1] Ropke, Stefan, and David Pisinger. 2006. "An Adaptive Large
               Neighborhood Search Heuristic for the Pickup and Delivery
               Problem with Time Windows." *Transportation Science* 40 (4): 455
               - 472.
        .. [2] Roozbeh et al. 2018. "An Adaptive Large Neighbourhood Search for
               asset protection during escaped wildfires."
               *Computers & Operations Research* 97: 125 - 134.
        """
        if not (0 <= worse <= 1):
            raise ValueError("worse outside [0, 1] not understood.")

        if not (0 < accept_prob < 1):
            raise ValueError("accept_prob outside (0, 1) not understood.")

        if num_iters <= 0:
            raise ValueError("Non-positive num_iters not understood.")

        if method not in ["linear", "exponential"]:
            raise ValueError("Method must be one of ['linear', 'exponential']")

        start_temp = -worse * init_obj / np.log(accept_prob)

        if method == "linear":
            step = (start_temp - 1) / num_iters
        else:
            step = (1 / start_temp) ** (1 / num_iters)

        logger.info(
            f"Autofit {method} SA: start_temp {start_temp:.2f}, "
            f"step {step:.2f}."
        )

        return cls(start_temp, 1, step, method=method)
