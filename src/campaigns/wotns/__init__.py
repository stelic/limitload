# -*- coding: UTF-8 -*-

from math import *

from pandac.PandaModules import *

from src.core import *
from src.blocks import *

_, p_, n_, pn_ = make_tr_calls_campaign(__file__)


campaign_shortdes = p_("campaign name", "Way of the Northern Storm")

campaign_longdes = p_("campaign description", """
It is mid 1972 and the war in Vietnam is raging through its final chapter. United States regime is making the last push to end the conflict on their terms, while the unyielding North Vietnamese are furiously contesting the aerial onslaught. Join the two elite US Navy crewmen in their unexpected next generation fighter, or step into the cockpit of MiG-21 as a young Soviet officer volunteer to aid the people's army. The outcome of the war hangs in balance, but the breaking point is at hand. The next few weeks could prove crucial for either side.
""").strip()

campaign_shortdes_compact = p_("campaign name, compact", "Way\nof the\nNorthern\nStorm")

