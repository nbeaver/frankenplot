#
# frankenplot.defaults: default values for various parameters
#

class Mode:
    pass

# global defaults
x_name = "sam_hor"
y_name = "sam_vert"
colormaps = ['autumn', 'bone', 'cool', 'copper', 'flag', 'gray', 'hot', 'hsv',
    'pink', 'prism', 'spring', 'summer', 'winter']
colormap = "hot"
title = ""

# Fluorescence Mode defaults
fluor_mode = Mode()
fluor_mode.normalize = True
fluor_mode.corrected = True
fluor_mode.z_name = "Io"

# Transmission Mode defaults
trans_mode = Mode()

# Transmission/Sample Mode defaults
trans_mode.samp_mode = Mode()
trans_mode.samp_mode.Io = "Io"
trans_mode.samp_mode.It = "It"

# Transmission/Reference Mode defaults
trans_mode.ref_mode = Mode()
trans_mode.ref_mode.Io = "It"
trans_mode.ref_mode.It = "Iref"
