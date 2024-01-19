from queue import Queue

import numpy as np
import pandas as pd
from bluesky import plan_stubs as bps
from bluesky import plans as bp
from bluesky.callbacks.core import CollectThenCompute
from bluesky.preprocessors import subs_decorator
from bluesky_adaptive.per_event import adaptive_plan, recommender_factory
from bluesky_adaptive.recommendations import NoRecommendation
from ophyd.sim import motor

from ..instrument.instrument_registry import registry


__all__ = ["GainRecommender", "auto_gain"]


class GainRecommender:
    """A recommendation engine for finding the best ion chamber gain*.

    Responds to ion chamber voltage as the dependent variable by
    changing the gain. If the voltage is above *volts_max* then the
    next gain* level will be higher, and if the voltage is below
    *volts_min* then the next gain* level will be lower. This engine
    will find all the values between *volts_min* and *volts_max*,
    assuming the output of the pre-amp changes monotonically with
    gain.

    *Gain is actually sensitivity in the case of an SRS-570 preamp, so
     raising the sensitivity results in a lower gain.

    """

    volts_min: float
    volts_max: float
    gain_min: int = 0
    gain_max: int = 27
    last_point: np.ndarray = None
    dfs: list = None
    big_step: int = 3

    def __init__(self, volts_min: float = 0.5, volts_max: float = 4.5):
        self.volts_min = volts_min
        self.volts_max = volts_max

    def tell(self, gains, volts):
        self.last_point = gains
        # Check if dataframes exist yet
        if self.dfs is None:
            self.dfs = [pd.DataFrame() for i in gains]
        # Add this measurement to the dataframes
        self.dfs = [pd.concat([df, pd.DataFrame(data={"gain": [gain], "volts": [volt]})], ignore_index=True)
                    for gain, volt, df in zip(gains, volts, self.dfs)]

    def tell_many(self, xs, ys):
        for x, y in zip(xs, ys):
            self.tell(x, y)

    def ask(self, n, tell_pending=True):
        """Figure out the next gain point based on the past ones we've measured."""
        if n != 1:
            raise NotImplementedError
        # Get the gains to try next
        next_point = [self.next_gain(df) for df in self.dfs]
        if np.array_equal(next_point, self.last_point):
            # We've already found the best point, so end the scan
            raise NoRecommendation
        return next_point

    def next_gain(self, df: pd.DataFrame):
        """Determine the next gain for this preamp based on past measurements.
        
        Parameters
        ==========
        df
          The past measurements for this preamp. Expected to have
          columns ["gain", "volts"].

        """
        # We're too low, so go up in gain (down in sensitivity)
        if np.all(df.volts < self.volts_max):
            # Determine step size
            step = self.big_step if np.all(df.volts < self.volts_min) else 1
            print(df.gain.min(), step)
            # Determine next gain to use
            new_gain = df.gain.min() - step
            return np.min([new_gain, self.gain_max])
        # We're too high, so go down in big steps
        if np.all(df.volts > self.volts_min):
            step = self.big_step if np.all(df.volts > self.volts_max) else 1
            new_gain = df.gain.max() + step
            return np.max([new_gain, self.gain_min])
        # Fill in any missing values through the correct gain
        values_in_range = df[(df.volts < self.volts_max) & (df.volts > self.volts_min)]
        needed_gains = np.arange(
            df[df.volts < self.volts_min].gain.max() + 1,
            df[df.volts > self.volts_max].gain.max()
        )
        missing_gains = [gain for gain in needed_gains if gain not in values_in_range.gain]
        if len(missing_gains) > 0:
            return min(missing_gains)
        # We have all the data we need, now decide on the best gain to use
        target = (self.volts_min + self.volts_max) / 2
        best = df.iloc[(df.volts - target).abs().argmin()]
        return best.gain


def auto_gain(
    dets="ion_chambers",
    volts_min: float = 0.5,
    volts_max: float = 4.5,
    max_count: int = 28,
    queue: Queue = None,
):
    """An adaptive Bluesky plan for optimizing pre-amp gains.

    For each detector, the plan will search for the range of gains
    within which the pre-amp output is between *volts_min* and
    *volts_max*, and select the gain that produces a voltage closest
    to the mid-point between *volts_min* and *volts_max*.

    Parameters
    ==========
    dets
      A sequence of detectors to scan. Can be devices, names, or Ophyd
      labels.
    volts_min
      The minimum acceptable range for each ion chamber's voltage.
    volts_max
      The maximum acceptable range for each ion chamber's voltage.
    max_count
      The scan will end after *max_count* iterations even if an
      optimal gain has not been found for all pre-amps.
    queue
      [Testing] A Queue object for passing recommendations between the
      plan and the recommendation engine.

    """
    # Resolve the detector list into real devices
    dets = registry.findall(dets)
    # Prepare the recommendation enginer
    recommender = GainRecommender(volts_min=volts_min, volts_max=volts_max)
    ind_keys = [det.preamp.sensitivity_level.name for det in dets]
    dep_keys = [det.volts.name for det in dets]
    rr, queue = recommender_factory(
        recommender,
        independent_keys=ind_keys,
        dependent_keys=dep_keys,
        max_count=max_count,
        queue=queue,
    )
    # Start from the current gain settings
    first_point = {
        det.preamp.sensitivity_level: det.preamp.sensitivity_level.get() for det in dets
    }
    # Make sure the detectors have the correct read attrs.
    old_kinds = {}
    signals = [(det.preamp, det.preamp.sensitivity_level) for det in dets]
    signals = [sig for tpl in signals for sig in tpl]
    for sig in signals:
        old_kinds[sig] = sig.kind
        sig.kind = "normal"
    # Execute the adaptive plan
    try:
        yield from adaptive_plan(
            dets=dets,
            first_point=first_point,
            to_recommender=rr,
            from_recommender=queue,
        )
    finally:
        # Restore the detector signal kinds
        for sig in signals:
            sig.kind = old_kinds[sig]


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2024, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
