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
sys.stdout.write("res: %d %d\n" % (w, h))
