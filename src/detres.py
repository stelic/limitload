# Detect desktop resolution.
# This is run in a separate process in order
# not to mess up normal engine startup.
import sys
from pandac.PandaModules import loadPrcFileData
loadPrcFileData("main", """
window-type none
""")
import direct.directbase.DirectStart
base.windowType = "offscreen"
base.makeDefaultPipe()
w = base.pipe.getDisplayWidth()
h = base.pipe.getDisplayHeight()
# Make sure selected values are not bigger than display.
di = base.pipe.getDisplayInformation()
wdi, hdi = max((di.getDisplayModeWidth(i), di.getDisplayModeHeight(i))
               for i in xrange(di.getTotalDisplayModes()))
if wdi < w:
    w, h = wdi, hdi
sys.stdout.write("res: %d %d\n" % (w, h))
