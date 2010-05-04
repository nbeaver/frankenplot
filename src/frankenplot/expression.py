#
# frankenplot.expression: expression parser
#

import re

# ============================================================================

# groups are signified by a percent sign (e.g., '%roi1')
GROUP_RE = re.compile(r'%[a-zA-Z_][a-zA-Z0-9_]*')

# ============================================================================

def expand_groups(expression, groups):
    """Expand any group names into sums over their constituent columns

    Replace any groups "%group" with "(col1 +col2+...+colN)" where
    (col1, ..., colN) comprise the group.

    """

    def group_repl(m):
        group = m.group(0)
        return "(%s)" % "+".join(["$" + col for col in groups[group]])

    return GROUP_RE.sub(group_repl, expression)
