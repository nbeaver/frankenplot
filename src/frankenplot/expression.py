#
# frankenplot.expression: expression handling
#

import re

from frankenplot import defaults, util

# ============================================================================

class Expression(object):
    def __str__(self):
        """Produces an expression parsable by xdp.Data.evaluate()

        """
        raise NotImplementedError

    def on_plot(self, figure, app):
        """Callback to be run after the expression is plotted

        """
        pass

class FluorExpression(Expression):
    """Fluorescence Mode expression

    """
    def __init__(self, corrected=None, normalize=None, z_name=None):
        if corrected is None:
            self.corrected = defaults.fluor_mode.corrected
        else:
            self.corrected = corrected

        if normalize is None:
            self.normalize = defaults.fluor_mode.normalize
        else:
            self.normalize = normalize

        if z_name is None:
            self.z_name = defaults.fluor_mode.z_name
        else:
            self.z_name = z_name

    def __str__(self):
        if self.normalize:
            return self._normalize_expr(self.expr, self.z_name)
        else:
            return self.expr

    def _normalize_expr(self, expression, z_name):
        return "(%s)/$%s" % (expression, z_name)

    def on_plot(self, figure, app):
        # update the ROI selector with the currently plotted ROI
        app.plot_cp.roi_selector.SetValue(str(self.roi))

class ROIExpression(FluorExpression):
    """Expression representing a single ROI

    """
    def __init__(self, roi, *args, **kwargs):
        self.roi = roi

        FluorExpression.__init__(self, *args, **kwargs)

    def group_name(self):
        return util.get_roi_group_name(self.roi, self.corrected)

    def __str__(self):
        self.expr = self.group_name()
        return FluorExpression.__str__(self)

class ChannelExpression(FluorExpression):
    """Expression representing a single channel in an ROI

    """
    def __init__(self, roi, channel, *args, **kwargs):
        self.roi = roi
        self.channel = channel

        FluorExpression.__init__(self, **kwargs)

    def column_name(self):
        return util.get_data_column_name(self.roi, self.channel, self.corrected)

    def __str__(self):
        self.expr = "$%s" % self.column_name()
        return FluorExpression.__str__(self)

class TransExpression(Expression):
    """Expression in Transmission Mode

    """

    def __str__(self):
        Io = "$%s" % self.Io
        It = "$%s" % self.It

        return "log(%s/%s)" % (Io, It)

class SampleExpression(TransExpression):
    """Expression representing the sample transmission

    """

    def __init__(self, Io=None, It=None):
        if Io is None:
            self.Io = defaults.trans_mode.samp_mode.Io
        else:
            self.Io = Io

        if It is None:
            self.It = defaults.trans_mode.samp_mode.It
        else:
            self.It = It

class RefExpression(TransExpression):
    """Expression representing the reference transmission

    """

    def __init__(self, Io=None, It=None):
        if Io is None:
            self.Io = defaults.trans_mode.ref_mode.Io
        else:
            self.Io = Io

        if It is None:
            self.It = defaults.trans_mode.ref_mode.It
        else:
            self.It = It

class ArbitraryExpression(Expression):
    def __init__(self, expr):
        self.expr = expr

    def __str__(self):
        return self.expr

# ============================================================================

# groups are signified by a percent sign (e.g., '%roi1')
GROUP_RE = re.compile(r'%[a-zA-Z_][a-zA-Z0-9_]*')

def expand_groups(expression, groups):
    """Expand any group names into sums over their constituent columns

    Replace any groups "%group" with "(col1 +col2+...+colN)" where
    (col1, ..., colN) comprise the group.

    """

    def group_repl(m):
        group = m.group(0)
        return "(%s)" % "+".join(["$" + col for col in groups[group]])

    return GROUP_RE.sub(group_repl, expression)
