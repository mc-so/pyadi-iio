# Copyright (C) 2022 Analog Devices, Inc.

# Author: Ivan Gil Mercano <ivangil.mercano@analog.com>

from __future__ import absolute_import, division, print_function

import matplotlib.pyplot as plt
import numpy as np
import pyeit.eit.bp as bp
import pyeit.eit.protocol as protocol
import pyeit.mesh as mesh
from adi import cn0565
from pyeit.eit.fem import EITForward
from pyeit.mesh.shape import thorax
from pyeit.mesh.wrapper import PyEITAnomaly_Circle

# variable/board declartion
value_type = "re" # re, im, others->magnitude
n_el = 16 # 8, 16, 24
port = "COM6"
baudrate = 230400

# mesh and protocol creation
mesh = mesh.create(n_el, h0=0.08)
protocol = protocol.create(n_el, dist_exc=1, step_meas=1, parser_meas="std")

# board initialization
eit_board = cn0565(uri=f"serial:{port},{baudrate},8n1")
eit_board.mode(freq=10000, el=n_el, force_distance=1, sense_distance=1)

# boundary voltage reading
voltages = eit_board.read_boundary_voltages()
if value_type == "re":
    current_data = voltages[:, 0]
elif value_type == "im":
    current_data = voltages[:, 1]
else:
    current_data = np.sqrt((voltages ** 2).sum(axis=1))

# Resistor array board is fixed. Use this to get absolute impedance
v0 = np.full_like(current_data, 1)
v1 = current_data


eit = bp.BP(mesh, protocol)
eit.setup(weight="none")
ds = 192.0 * eit.solve(v1, v0, normalize=True)
points = mesh.node
triangle = mesh.element

# Plot
fig, ax = plt.subplots()
im = ax.tripcolor(points[:, 0], points[:, 1], triangle, ds)
ax.set_title(r"Impedence Measurement Using Back Projection")
ax.axis("equal")
fig.colorbar(im, ax=ax)
plt.show()
