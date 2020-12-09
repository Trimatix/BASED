from urllib import request
import json

class SDBGame:
    def __init__(self, owner, meta_url, expansionNames):
        self.owner = owner
        self.meta_url = meta_url
        deckMeta = json.load(request.urlopen(meta_url))
        self.expansionNames = expansionNames
        self.deckName = deckMeta["deck_name"]
        self.expansions = {}
        for expansionName in expansionNames:
            self.expansions[expansionName] = deckMeta["expansions"][expansionName]
