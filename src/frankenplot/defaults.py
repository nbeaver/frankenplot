#
# frankenplot.defaults: default values for various parameters
#

class Mode:
    pass

x_name = "sam_hor"
y_name = "sam_vert"
colormap = "hot"
title = ""

fluor_mode = Mode()
fluor_mode.normalize = True
fluor_mode.corrected = True
fluor_mode.z_name = "Io"
