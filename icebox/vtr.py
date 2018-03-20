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

# Electrical and timing characteristics have been taken from vpr/sample_arch.xml
# which has realistic model data for a hypothetical 40nm architecure.

# TODO
#  - .subckt vs. .gate
#  - combinational_sink_ports
#  - interconnects
#  - carry logic mux modes
#  - class="flipflop", class="lut", port_class=


import lxml.etree as et
import sys

e_architecture = et.Element('architecture')

#
# Models
#

class Model:
    def __init__(self, name, inputs, outputs, clock=None):
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.clock = clock

    def model(self):
        e_model = et.Element('model', name=self.name)

        e_input_ports = et.Element('input_ports')
        if self.clock:
            e_input_ports.extend(
                [et.Element('port', name=i, clock=self.clock)
                    for i in self.inputs] +
                [et.Element('port', name=self.clock, is_clock="1")])
        else:
            e_input_ports.extend(
                [et.Element('port', name=i) for i in self.inputs])

        e_output_ports = et.Element('output_ports')
        e_output_ports.extend(
            [et.Element('port', name=i) for i in self.outputs])

        e_model.extend([e_input_ports, e_output_ports])
        return e_model

def dff_types():
    return ([(neg_clk, en, False)
        for en in [False, True] for neg_clk in [False, True]] +
        [(neg_clk, en, True, set) for set in [False, True]
        for en in [False, True] for neg_clk in [False, True]])

def dff_suffix(neg_clk, en, sync, set=False):
    return (('N' if neg_clk else '') + ('E' if en else '') +
        ('S' + ('S' if set else 'R') if sync else ''))

def dff_name(*k):
    return 'DFF' + dff_suffix(*k)

def dff(neg_clk, en, sync, set=False):
    return Model('SB_' + dff_name(neg_clk, en, sync, set),
        ['D'] + (['E'] if en else []) + ((['S'] if set else ['R']) if sync else []),
        ['Q'], 'C')

carry = Model('SB_CARRY', ['CI', 'I0', 'I1'], ['CO'])
dffs = [dff(*t) for t in dff_types()]
#gb = Model('SB_GB', ['USER_SIGNAL_TO_GLOBAL_BUFFER'], ['GLOBAL_BUFFER_OUTPUT'])
lut4 = Model('SB_LUT4', ['I0', 'I1', 'I2', 'I3'], ['O'])

models = [carry] + dffs + [lut4] #[gb, lut4]

e_models = et.Element('models')
e_models.extend([m.model() for m in models])
e_architecture.append(e_models)

#
# Layout
#

e_fixed_layout = et.Element('fixed_layout', name='ice40', width='33', height='33')
e_layout = et.Element('layout')
e_layout.append(e_fixed_layout)
e_architecture.append(e_layout)

#
# Device
#

e_device = et.Element('device')
e_architecture.append(e_device)

e_device.append(et.Element(
    'sizing', R_minW_nmos='8926', R_minW_pmos='16067'))
e_device.append(et.Element(
    'timing', C_ipin_cblock='1.47e-15', T_ipin_cblock='7.247000e-11'))
e_device.append(et.Element('area', grid_logic_tile_area="53894"))

e_device.append(et.Element('switch_block', type='custom'))

#
# Switch List
#

e_switchlist = et.Element('switchlist')
e_architecture.append(e_switchlist)

e_switchlist.append(et.Element('switch', type='mux', name='0', R='551',
    Cin='.77e-15', Cout='4e-15', Tdel='58e-12', mux_trans_size='2.630740',
    buf_size='27.645901'))

#
# Segment List
#

e_segmentlist = et.Element('segmentlist')
e_architecture.append(e_segmentlist)

for length in [4, 12]:
    e_segment = et.Element('segment', name='span%d' % length, freq='50',
        length=str(length), type='bidir', Rmetal='101', Cmetal='22.5e-15')

    e_sb = et.Element('sb', type='pattern')
    e_sb.text = ' '.join(['0'] * (length + 1))
    e_segment.append(e_sb)

    e_cb = et.Element('cb', type='pattern')
    e_cb.text = ' '.join(['1'] * length)
    e_segment.append(e_cb)

    e_wire_switch = et.Element('wire_switch', name='0')
    e_segment.append(e_wire_switch)

    e_opin_switch = et.Element('opin_switch', name='0')
    e_segment.append(e_opin_switch)

    e_segmentlist.append(e_segment)

#
# Switch Block List
#

e_switchblocklist = et.Element('switchblocklist')

e_switchblock = et.Element('switchblock', name='sb', type='unidir')

e_switchblocklocation = et.Element('switchblock_location', type='EVERYWHERE')
e_switchblock.append(e_switchblocklocation)

e_switchfuncs = et.Element('switchfuncs')
e_switchblock.append(e_switchfuncs)

e_switchblocklist.append(e_switchblock)

e_architecture.append(e_switchblocklist)

#
# Complex Block List
#

def ios(tag, name_fmt, indices=1, num_pins=1, **kw):
  return [et.Element(tag, name=name_fmt.format(i), num_pins=str(num_pins),
    equivalent='false', **kw) for i in range(indices)]

e_complexblocklist = et.Element('complexblocklist')
e_architecture.append(e_complexblocklist)

#
# IO
#

def pb_type_io():
    e_pb_type = et.Element('pb_type', name='io', capacity='2')

    # Declare I/O
    e_pb_type.extend(ios('input', 'inpad'))
    e_pb_type.extend(ios('output', 'outpad'))

    e_pb_type.extend(ios('input', 'io_{0}/D_IN', 2, 2))
    e_pb_type.extend(ios('output', 'io_{0}/D_OUT', 2, 2))
    e_pb_type.extend(ios('input', 'io_{0}/OUT_ENB', 2))
    e_pb_type.extend(ios('input', 'io_global/cen'))
    e_pb_type.extend(ios('input', 'io_global/inclk'))
    e_pb_type.extend(ios('output', 'io_global/outclk'))
    e_pb_type.extend(ios('input', 'io_global/latch'))

    # Declare fc
    e_pb_type.append(et.Element('fc',
        default_in_type='abs', default_in_val='1',
        default_out_type='abs', default_out_val='1'))

    # Declare locations
    '''
    e_gridlocations = et.Element('gridlocations')
    e_gridlocations.append(et.Element('loc', type='perimeter', priority='2'))
    e_pb_type.append(e_gridlocations)
    '''

    # Declare interconnects
    e_interconnect = et.Element('interconnect')
    e_pb_type.append(e_interconnect)

    # Declare pinlocationss
    e_pb_type.append(et.Element('pinlocations', pattern='spread'))

    return e_pb_type

e_complexblocklist.append(pb_type_io())

#
# LOGIC
#

def plb_mode(neg_clk, en, sync, set=False):
    e_mode = et.Element('mode', name='PLB' + dff_suffix(neg_clk, en, sync, set))

    e_pb_type = et.Element('pb_type', num_pb='8', name='lutff')

    # CARRY

    e_pb_type_carry = et.Element('pb_type', name='CARRY',
        blif_model='.subckt SB_CARRY', num_pb='1')
    e_pb_type_carry.extend(ios('input', 'CI'))
    e_pb_type_carry.extend(ios('input', 'I{0}', 2))
    e_pb_type_carry.extend(ios('output', 'CO'))

    e_interconnect = et.Element('interconnect')
    e_pb_type_carry.append(e_interconnect)

    e_pb_type.append(e_pb_type_carry)

    # LUT4

    e_pb_type_lut4 = et.Element('pb_type', name='LUT4',
        blif_model='.subckt SB_LUT4', num_pb='1')
    e_pb_type_lut4.extend(ios('input', 'I{0}', 4))
    e_pb_type_lut4.extend(ios('output', 'O'))

    e_interconnect = et.Element('interconnect')
    e_pb_type_lut4.append(e_interconnect)

    e_pb_type.append(e_pb_type_lut4)

    # DFF

    name = dff_name(neg_clk, en, sync, set)

    e_pb_type_dff = et.Element('pb_type', name=name,
        blif_model='.subckt SB_' + name, num_pb='1')

    e_pb_type_dff.extend(ios('clock', 'C'))
    e_pb_type_dff.extend(ios('input', 'D'))
    e_pb_type_dff.extend([et.Element('T_setup', value='0', port='D', clock='C')])
    if en:
        e_pb_type_dff.extend(ios('input', 'E'))
        e_pb_type_dff.extend([et.Element('T_setup', value='0', port='E', clock='C')])
    if sync:
        port = 'S' if set else 'R'
        e_pb_type_dff.extend(ios('input', port))
        e_pb_type_dff.extend([et.Element('T_setup', value='0', port=port, clock='C')])
    e_pb_type_dff.extend(ios('output', 'Q'))


    e_interconnect = et.Element('interconnect')
    e_pb_type_dff.append(e_interconnect)

    e_pb_type.append(e_pb_type_dff)


    e_interconnect = et.Element('interconnect')
    e_pb_type.append(e_interconnect)

    e_interconnect = et.Element('interconnect')
    e_mode.append(e_interconnect)

    e_mode.append(e_pb_type)

    return e_mode

def pb_type_plb():
    e_pb_type = et.Element('pb_type', name='plb', height='2')

    # Declare I/O
    e_pb_type.extend(ios('input', 'lutff_global/clk'))
    e_pb_type.extend(ios('input', 'lutff_global/cen'))
    e_pb_type.extend(ios('input', 'lutff_global/s_r'))
    e_pb_type.extend(ios('input', 'carry_in'))
    e_pb_type.extend(ios('input', 'carry_in_mux'))
    e_pb_type.extend(ios('input', 'lutff_{0}/in', 8, 4))
    e_pb_type.extend(ios('output', 'lutff_{0}/lout', 7))
    e_pb_type.extend(ios('output', 'lutff_{0}/out', 8))
    e_pb_type.extend(ios('output', 'lutff_{0}/cout', 8))

    # Modes
    e_pb_type.extend([plb_mode(*t) for t in dff_types()])

    # Declare fc
    e_pb_type.append(et.Element('fc',
        default_in_type='abs', default_in_val='1',
        default_out_type='abs', default_out_val='1'))

    # Declare interconnects
    e_interconnect = et.Element('interconnect')
    e_pb_type.append(e_interconnect)

    # Delare the pin locations
    e_pb_type.append(et.Element('pinlocations', pattern='spread'))

    # Declare locations
    '''
    e_gridlocations = et.Element('gridlocations')
    e_gridlocations.append(et.Element('loc', type='fill', priority='0'))
    e_pb_type.append(e_gridlocations)
    '''

    return e_pb_type

e_complexblocklist.append(pb_type_plb())

#
# RAM
#

def pb_type_ram():
    e_pb_type = et.Element('pb_type', name='ram')
    #setattr(e_pb_type, 'class', 'memory')

    # Declare I/O
    e_pb_type.extend(ios('output', 'ram/RDATA', 1, 16, port_class='data_out1'))
    e_pb_type.extend(ios('input', 'ram/RADDR', 1, 11, port_class='address1'))
    e_pb_type.extend(ios('input', 'ram/WADDR', 1, 11, port_class='address2'))
    e_pb_type.extend(ios('input', 'ram/MASK', 1, 16))
    e_pb_type.extend(ios('input', 'ram/WDATA', 1, 16, port_class='data_in2'))
    e_pb_type.extend(ios('input', 'ram/RCLKE'))
    e_pb_type.extend(ios('input', 'ram/RCLK'))
    e_pb_type.extend(ios('input', 'ram/RE'))
    e_pb_type.extend(ios('input', 'ram/WCLKE'))
    e_pb_type.extend(ios('clock', 'ram/WCLK'))
    e_pb_type.extend(ios('input', 'ram/WE', port_class='write_en2'))

    # Declare fc
    e_pb_type.append(et.Element('fc',
        default_in_type='abs', default_in_val='1',
        default_out_type='abs', default_out_val='1'))

    # Delare the pin locations
    e_pb_type.append(et.Element('pinlocations', pattern='spread'))

    # Declare locations
    '''
    e_gridlocations = et.Element('gridlocations')
    for col in [8, 25]:
        e_gridlocations.append(et.Element('loc', type='col', start=str(col),
            repeat='1', priority='1'))
    e_pb_type.append(e_gridlocations)
    '''

    # Declare interconnects
    e_interconnect = et.Element('interconnect')
    e_pb_type.append(e_interconnect)

    return e_pb_type

e_complexblocklist.append(pb_type_ram())

#
# Output XML
#

sys.stdout.write(et.tostring(e_architecture, pretty_print=True).decode('utf-8'))
