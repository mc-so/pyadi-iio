# CN0565_EIT

import numpy as np
from adi import cn0565

class CN0565_EIT():

    def __init__(self, port, baudrate=230400):
        self._serial = port
        self._baudrate = baudrate
        self._switch_sequence = None
    
        self.cnboard = cn0565(uri=f"serial:{port},{baudrate},8n1")
        self.cnboard.add(0x71)
        self.cnboard.add(0x70)

    def mode(self, freq=10000, el=8, force_distance=1, sense_distance=1, fixed_ref=True):
        self.cnboard.excitation_frequency = freq
        self.electrode_count = el
        self.force_distance = force_distance 
        self.sense_distance = sense_distance
        self.fixed_ref = fixed_ref
        

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

    def read_boundary_voltages(self):
        if self._switch_sequence == None:
            self._switch_sequence = self.generate_switch_sequence()

        self.cnboard.impedance_mode = False
        ret = []
        for seq in self._switch_sequence:
            # reset cross point switch
            self.cnboard.gpio1_toggle = True

            # set new cross point switch configuration from pregenerated sequence
            self.cnboard[seq[0]][0] = True
            self.cnboard[seq[1]][1] = True
            self.cnboard[seq[2]][2] = True
            self.cnboard[seq[3]][3] = True

            # read impedance
            s = self.cnboard.channel["voltage0"].raw
            ret.append([s.real, s.imag])

        return np.array(ret).reshape(len(ret), 2)
    
    def supported_electrode_count(self):
        return np.array([8, 16, 32])
    
    def query(self, freq, f_plus, f_minus, s_plus, s_minus, mode):
        self.cnboard.gpio1_toggle = True
        self.cnboard.impedance_mode = (mode == 'Z')

        self.cnboard[f_plus][0] = True
        self.cnboard[s_plus][1] = True
        self.cnboard[s_minus][2] = True
        self.cnboard[f_minus][3] = True

        return self.cnboard.channel["voltage0"].raw
    
    def close(self):
        self.cnboard.close()