import sys
import time

import adi

cn0565 = adi.cn0565(uri="serial:COM8,230400,8n1n")
# reset the cross point switch

cn0565.gpio1_toggle = True
cn0565.excitation_amplitude = 300
cn0565.excitation_frequency = 80000
cn0565.magnitude_mode = False
cn0565.impedance_mode = True

cn0565.add(0x71)
cn0565.add(0x70)

fplus = 1
splus = 4
fminus = 4
sminus = 1

if len(sys.argv) > 1:
    fplus = int(sys.argv[1])
    fminus = int(sys.argv[2])
    splus = int(sys.argv[3])
    sminus = int(sys.argv[4])

cn0565[fplus][0] = True
cn0565[splus][1] = True
cn0565[sminus][2] = True
cn0565[fminus][3] = True

print(cn0565.channel["voltage0"].raw)
