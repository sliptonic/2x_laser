#!/usr/bin/env python

# shadowbox dpi=45 speed=300 power=80 on_time=1.5

# user defined parameters
SPEED = 600
ACCEL = 270
laser_power = 30
laser_on_time = 0.3
air_assist = True
bidirectional_raster = False
is_metric = False
origin_x = 0
origin_y = 0
# center, <top|middle|bottom><left|center|right>
origin_loc = 'topleft'
# for mirroring
mirror_x = False
mirror_y = False
# output raster Falsesize
keep_aspect_ratio = True
raster_w = -1
raster_h = -1
# raster dpi
XDPI = 200
YDPI = 200


import os, sys, time, glob
from math import ceil, floor
from subprocess import *
from itertools import *
from PIL import Image
from raster_gui import *


if ( len(sys.argv) > 1 and os.path.exists(sys.argv[1]) ):
    image_name = sys.argv[1]
else:
    image_name = image_not_found()

print('%')
print '(image = %s)' % image_name

image = Image.open(image_name)

(img_w,img_h) = image.size
print('(image size w=%u,h=%u)' % (img_w,img_h))

# system parameters
output_optional_border = False
distribute_bits_in_floats = False
MAX_BPF = 53

# calc lead in + 100% fudge
leadIn = (1.0*SPEED*SPEED/3600)/ACCEL

print '(raster requested size w=%f, h=%f)' % (raster_w,raster_h)

# adjust to aspect ratio
raster_w_scaled_to_h = raster_h*float(img_w)/img_h
raster_h_scaled_to_w = raster_w*float(img_h)/img_w

if raster_w < 0 and raster_h < 0:
    # set size to be exactly input image
    raster_w = img_w/float(XDPI)
    raster_h = img_h/float(YDPI)
    pix_w = img_w
    pix_h = img_h
    W = raster_w
    H = raster_h
else:
    if raster_w < 0:
        raster_w = raster_w_scaled_to_h
    elif raster_h < 0:
        raster_h = raster_h_scaled_to_w
    elif keep_aspect_ratio:
        if raster_w < raster_w_scaled_to_h:
            raster_h = raster_h_scaled_to_w
            print '(keep aspect ratio scaling h down to %f)' % (raster_h)
        elif raster_h < raster_h_scaled_to_w:
            raster_w = raster_w_scaled_to_h
            print '(keep aspect ratio scaling w down to %f)' % (raster_w)

    # calc image raster size
    pix_w = int(raster_w * XDPI)
    pix_h = int(raster_h * YDPI)
    W = float(pix_w) / XDPI
    H = float(pix_h) / YDPI

# handle origin offsetting
if ( origin_loc == 'center' ):
    X = origin_x - W/2.0
    Y = origin_y + H/2.0
else:
    if ( 'top' in origin_loc ):
        Y = origin_y
    elif ( 'bottom' in origin_loc ):
        Y = origin_y + H
    elif ( 'middle' in origin_loc ):
        Y = origin_y + H/2.0
    else:
        print('unknown origin_loc='+origin_loc)
        sys.exit()

    if ( 'left' in origin_loc ):
        X = origin_x
    elif ( 'center' in origin_loc ):
        X = origin_x - W/2.0
    elif ( 'right' in origin_loc ):
        X = origin_x - W
    else:
        print('unknown origin_loc='+origin_loc)
        sys.exit()

print '(raster upper right corner x=%f,y=%f)' % (X,Y)
print '(raster calculated size w=%f,h=%f)' % (W,H)

if img_w != pix_w or img_h != pix_h:
    print '(rescaling image to %u,%u pixels)' % (pix_w, pix_h)
    image = image.resize((pix_w, pix_h), Image.BICUBIC)
else:
    print '(keeping image size %u,%u pixels)' % (pix_w, pix_h)
image = image.convert('1')

if mirror_x:
    print '(flip image left to right)'
    image = image.transpose(Image.FLIP_LEFT_RIGHT)
if mirror_y:
    print '(flip image top to bottom)'
    image = image.transpose(Image.FLIP_TOP_BOTTOM)

image.save('actual.png')

pix = list(image.getdata())

# gcode header
if is_metric:
    print('G21')
else:
    print('G20')
print('M63 P0 (turn off laser dout)')
print('G0 Z0 (turn off magic z)')
print('G64 P0.0001 Q0.0001 (minimal path blending)')
print('M68 E0 Q%0.3f (set laser power level)' % laser_power)
print('M3 S1 (master laser power on)')
if air_assist:
    print('M7 (air assist on)')
print('#<raster_speed> = %0.3f' % SPEED)
print('F[#<raster_speed>]')

# gcode skip lines that show raster image run box
if output_optional_border:
    print('/ G0 X%0.4f Y%0.4f' % (X,Y))
    print('/ G1 X%0.4f Y%0.4f' % (X+W,Y))
    print('/ G1 X%0.4f Y%0.4f' % (X+W,Y-H))
    print('/ G1 X%0.4f Y%0.4f' % (X,Y-H))
    print('/ G1 X%0.4f Y%0.4f' % (X,Y))
    print('/ M2')

print('o100 sub')
print('  M68 E2 Q[#2]')
print('  M68 E1 Q[#1]')
print('o100 endsub')

forward = True
first_output = True

for y in xrange(0,pix_h):
    offset_y = Y - 1/float(YDPI)/2 - float(y)/YDPI

    row = pix[y * pix_w:(y + 1) * pix_w]

    if not forward:
        row.reverse()

    first_non_zero = -1
    last_non_zero = -1
    for index, pixel in enumerate(row):
        if (pixel <= 127):
            if (first_non_zero == -1):
                first_non_zero = index
            last_non_zero = index

    # debug raster
    #first_non_zero, last_non_zero = (0,len(row)-1)

    # some data to output
    if (first_non_zero >= 0):
        print('(raster line %d)' % y)

        if distribute_bits_in_floats:
            # figure out how many max bpf floats to hold the data and
            # then evenly distribute the bits
            total_bits = last_non_zero - first_non_zero + 1;
            BPF = ceil(total_bits / (ceil(float(total_bits) / MAX_BPF)))
        else:
	    # just pack the floats at max
            BPF = MAX_BPF

        bits = []
        i=0
        bitval=0
        for v in row[first_non_zero:last_non_zero+1]:
            if (v <= 127):
                bitval += (1<<i)
            i += 1
            if (i >= BPF):
                bits.append(bitval);
                bitval = 0
                i = 0
        if (i > 0):
            bits.append(bitval);

        # forward offsets are:
        #   X where we start
        #     + half a dpi to center the dots
        #     + offset to first bit to not waste time scanning air
        #     - lead in to make sure we are at full speed before output
	if forward:
            offset_start = X + (1/float(XDPI)/2 + float(first_non_zero)/XDPI - leadIn)
            offset_end = X + (1/float(XDPI)/2 + float(last_non_zero)/XDPI + leadIn)
        else:
            offset_start = X + (W - 1/float(XDPI)/2 - float(first_non_zero)/XDPI + leadIn)
            offset_end = X + (W - 1/float(XDPI)/2 - float(last_non_zero)/XDPI - leadIn)

        print('G0 X%0.4f Y%0.4f' % (offset_start,offset_y))
        print('M68 E1 Q-1 (start new line)')
        if first_output:
            # only have to send this on the first line output
            print('o100 call [-2] [%d] (gcode is metric 0=no,1=yes)' % (1 if is_metric else 0))
            print('o100 call [-3] [#<raster_speed>] (speed, in/min or mm/min)')
        print('o100 call [-4] [%d] (direction)' % (1 if forward else -1))
        if first_output:
            print('o100 call [-5] [%0.3f] (dpi)' % XDPI)
        if distribute_bits_in_floats or first_output:
            print('o100 call [-6] [%u] (bits per float)' % BPF)
        if first_output:
            print('o100 call [-7] [%d] (laser on time, ns)' % (laser_on_time*1000000))
        # have to send last parameters as this triggers the line init
        print('o100 call [-8] [%0.4f] (lead in)' % leadIn)
        print('(raster data start)')

        first_output = False

        bits_length = len(bits)
        for index, bitval in enumerate(bits):
            if bitval != 0 or index == bits_length-1:
                # we can skip zeros unless it is the last float
                print('o100 call [%u] [%u]' % (index+1, bitval))

        print('G1 X%0.4f' % offset_end)
        print('M1')

    if bidirectional_raster:
        # next line is reverse direction
        forward = not forward

print('M68 E1 Q0 (end raster)')

print('G0 X%0.4f Y%0.4f (go to start)' % (X,Y))
print('M2')
print('%')

