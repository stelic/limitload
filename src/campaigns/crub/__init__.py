# -*- coding: UTF-8 -*-

from math import *

from pandac.PandaModules import *

from src.core import *
from src.blocks import *

_, p_, n_, pn_ = make_tr_calls_campaign(__file__)


campaign_shortdes = p_("campaign name", "Cloudy Rubicon")

campaign_longdes = p_("campaign description", """
In the near future, open divisions within the European Union and the countries of the Maghreb, about the ongoing conflict in the Western Sahara, left the security of this disputed territory neglected. An enigmatic tycoon-warlord used the opportunity, to invade and claim the land for himself. Following unsuccessful negotiations, the United Nations have given the EU the mandate to use military force against the warlord. The F-16 Squadron Leeuwarden is going to deliver the first strike, but its commander will soon realize that all may not be as it seems in this conflict.
""").strip()

campaign_shortdes_compact = p_("campaign name, compact", "Cloudy\nRubicon")

