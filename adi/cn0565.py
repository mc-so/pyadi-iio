# Copyright (C) 2023 Analog Devices, Inc.
#
# SPDX short identifier: ADIBSD
# Author: Ivan Gil Mercano <ivangil.mercano@analog.com>

import numpy as np
from adi.ad5940 import ad5940
from adi.adg2128 import adg2128
from adi.context_manager import context_manager


class cn0565(ad5940, adg2128, context_manager):

    """CN0565 Impedance Measurement"""

    _device_name = ""

    def __init__(self, uri=""):
        """Constructor for CN0565 class."""
        context_manager.__init__(self, uri, self._device_name)
        ad5940.__init__(self)
        adg2128.__init__(self)
        self._switch_sequence = None
        self.add(0x71)
        self.add(0x70)

    # Close the iio board connection
    def close(self):
        del context_manager.ctx

    # Select the mode for the CN0565 board
    def mode(
        self, freq=10000, el=8, force_distance=1, sense_distance=1, fixed_ref=True
    ):
        self.excitation_frequency = freq
        self.electrode_count = el
        self.force_distance = force_distance
        self.sense_distance = sense_distance
        self.fixed_ref = fixed_ref

    # Used to generate the combination of force distance and sense distance
    def generate_switch_sequence(self):
        seq = 0
        ret = []
        for i in range(self.electrode_count):
            f_plus = i
            f_minus = (i + self.force_distance) % self.electrode_count
            for j in range(self.electrode_count):
                s_plus = j % self.electrode_count
                if s_plus == f_plus or s_plus == f_minus:
                    continue
                s_minus = (s_plus + self.sense_distance) % self.electrode_count
                if s_minus == f_plus or s_minus == f_minus:
                    continue
                ret.append((f_plus, s_plus, s_minus, f_minus))
                seq += 1
        return ret

    # Read boundary voltages
    def read_boundary_voltages(self):
        if self._switch_sequence == None:
            self._switch_sequence = self.generate_switch_sequence()

        self.impedance_mode = False
        ret = []
        for seq in self._switch_sequence:
            # reset cross point switch
            self.gpio1_toggle = True

            # set new cross point switch configuration from pregenerated sequence
            self._xline[seq[0]][0] = True
            self._xline[seq[1]][1] = True
            self._xline[seq[2]][2] = True
            self._xline[seq[3]][3] = True

            # read impedance
            s = self.channel["voltage0"].raw
            ret.append([s.real, s.imag])

        return np.array(ret).reshape(len(ret), 2)

    # Supported Electrode Count
    def supported_electrode_count(self):
        return np.array([8, 16, 32])

    # Calls the electrode pair then return the voltage
    def query(self, freq, f_plus, f_minus, s_plus, s_minus, mode):
        self.gpio1_toggle = True
        self.impedance_mode = mode == "Z"

        self._xline[f_plus][0] = True
        self._xline[s_plus][1] = True
        self._xline[s_minus][2] = True
        self._xline[f_minus][3] = True

        return self.channel["voltage0"].raw

    # Used to close the board
    def stop(self):
        self.intf.quit()
