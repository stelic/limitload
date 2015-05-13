# -*- coding: UTF-8 -*-

from math import *

from pandac.PandaModules import *

from src.core import *
from src.blocks import *

_, p_, n_, pn_ = make_tr_calls_campaign(__file__)


campaign_shortdes = p_("campaign name", "Broken Star")

campaign_longdes = p_("campaign description", """
The story about an old Soviet ace, his customized MiG-29 fighter, and a secretive committee, operating from deep in Siberia. Despite having been denounced in the country that was once the core of the great Union, this bunch of red commissars never gave up on the Revolution. Their actions, entangled in the chaotic political life of the Russian Federation at the turn of the new millennium, are going to get them into a variety of local intrigues and geopolitical games.
""").strip()

campaign_shortdes_compact = p_("campaign name, compact", "Broken\nStar")

