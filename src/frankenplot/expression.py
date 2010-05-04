#
# frankenplot.expression: expression handling
#

import re

from frankenplot import defaults

# ============================================================================

class Expression(object):
    def __str__(self):
        raise NotImplementedError

    def on_plot(self, figure, app):
        pass

class FluorExpression(Expression):
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
            self.z_name = defaults.z_name
        else:
            self.z_name = z_name

    def __str__(self):
        if self.normalize:
            return self._normalize_expr(self.expr, self.z_name)
        else:
            return self.expr

    def _normalize_expr(self, expression, z_name):
        return "(%s)/$%s" % (expression, z_name)

class ROIExpression(FluorExpression):
    def __init__(self, roi, *args, **kwargs):
        self.roi = roi

        FluorExpression.__init__(self, *args, **kwargs)

    def group_name(self):
        if self.corrected:
            stem = "corr_roi"
        else:
            stem = "roi"

        return "%%%s_%d" % (stem, self.roi)

    def __str__(self):
        self.expr = self.group_name()
        return FluorExpression.__str__(self)

    def on_plot(self, figure, app):
        app.plot_cp.roi_selector.SetValue(str(self.roi))

class ChannelExpression(FluorExpression):
    def __init__(self, roi, channel, *args, **kwargs):
        self.roi = roi
        self.channel = channel

        FluorExpression.__init__(self, **kwargs)

    def column_name(self):
        if self.corrected:
            stem = "corr_roi"
        else:
            stem = "roi"

        return "%s%d_%d" % (stem, self.channel, self.roi)

    def __str__(self):
        self.expr = "$%s" % self.column_name()
        return FluorExpression.__str__(self)

class TransExpression(Expression):
    pass

class SampleExpression(TransExpression):
    pass

class ArbitraryExpression(Expression):
    pass

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