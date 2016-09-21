#!/usr/bin/env python3
#
#  Copyright (C) 2016 Joel Holdsworth <joel@airwebreathe.org.uk> 
#
#  Permission to use, copy, modify, and/or distribute this software for any
#  purpose with or without fee is hereby granted, provided that the above
#  copyright notice and this permission notice appear in all copies.
#
#  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
#  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
#  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
#  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
#  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
#  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import lxml.etree as et
import sys

class Model:
  def __init__(self, name, inputs, outputs, clocks=[]):
    self.name = name
    self.inputs = inputs
    self.outputs = outputs
    self.clocks = clocks

  def model(self):
    def create_ports_node(type):
      e_ports = et.Element(type + '_ports')
      e_ports.extend([et.Element('port', name=i) for i in
          getattr(self, type + 's', [])])
      return e_ports
    e_model = et.Element('model', name='.gate ' + self.name)
    e_model.extend([create_ports_node(t) for t in ['input', 'output', 'clock']])
    return e_model

def dff_types():
  return ([(neg_clk, en, False)
    for en in [False, True] for neg_clk in [False, True]] +
    [(neg_clk, en, True, set) for set in [False, True]
    for en in [False, True] for neg_clk in [False, True]])

def dff_suffix(neg_clk, en, sync, set=False):
  return (('N' if neg_clk else '') + ('E' if en else '') +
    ('S' + ('S' if set else 'R') if sync else ''))

def dff(neg_clk, en, sync, set=False):
  return Model('SB_DFF' + dff_suffix(neg_clk, en, sync, set),
    ['D'] + (['E'] if en else []) + ((['S'] if set else ['R']) if sync else []),
    ['Q'], ['C'])

def plb_mode(neg_clk, en, sync, set=False):
  e_mode = et.Element('mode', name='PLB' + dff_suffix(neg_clk, en, sync, set))
  return e_mode

def pb_type_plb():
  e_pb_type = et.Element('pb_type', name='PLB')
  e_pb_type.extend([plb_mode(*t) for t in dff_types()])
  return e_pb_type

carry = Model('SB_CARRY', ['CI', 'I0', 'I1'], ['C0'])
dffs = [dff(*t) for t in dff_types()]
gb = Model('SB_GB', ['USER_SIGNAL_TO_GLOBAL_BUFFER'], ['GLOBAL_BUFFER_OUTPUT'])
lut4 = Model('SB_LUT4', ['I0', 'I1', 'I2', 'I3'], ['O'])

models = [carry] + dffs + [gb, lut4]

e_architecture = et.Element('architecture')

e_models = et.Element('models')
e_models.extend([m.model() for m in models])
e_architecture.append(e_models)

e_architecture.append(et.Element('layout', width='33', height='33'))

e_device = et.Element('device')
e_device.append(et.Element(
    'sizing', R_minW_nmos='8926', R_minW_pmos='16067'))
e_device.append(et.Element(
    'timing', C_ipin_cblock='1.47e-15', T_ipin_cblock='7.247000e-11'))
e_device.append(et.Element('switch_block'))
e_architecture.append(e_device)

e_switchlist = et.Element('switchlist')
e_architecture.append(e_switchlist)

e_segmentlist = et.Element('segmentlist')
e_architecture.append(e_segmentlist)

e_complexblocklist = et.Element('complexblocklist')
e_complexblocklist.append(pb_type_plb())
e_architecture.append(e_complexblocklist)

sys.stdout.write(et.tostring(e_architecture, pretty_print=True).decode('utf-8'))
