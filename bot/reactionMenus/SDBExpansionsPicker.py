from bot.users import basedUser
from discord import Message, Member, Role, Embed
from typing import Dict, Tuple
from . import reactionMenu, pagedReactionMenu
from .. import lib, botState
from ..scheduling import timedTask
from ..users import basedUser
from ..cfg import cfg


async def cancelGame(menuID):
    if menuID in botState.reactionMenusDB:
        menu = botState.reactionMenusDB[menuID]
        await menu.msg.channel.send("Game Cancelled.")
        callingBGuild = botState.guildsDB.getGuild(menu.msg.guild.id)
        if menu.msg.channel in callingBGuild.runningGames:
            del callingBGuild.runningGames[menu.msg.channel]
        await menu.timeout.forceExpire(callExpiryFunc=False)
        await menu.msg.delete()
        del botState.reactionMenusDB[menuID]


class SDBExpansionsPicker(pagedReactionMenu.MultiPageOptionPicker):
    def __init__(self, msg: Message, expansionNamesCardCounts: Dict[str, Tuple[int, int]], timeout: timedTask.TimedTask = None, targetMember: Member = None, targetRole: Role = None, owningBasedUser: basedUser.BasedUser = None):
        numExpansions = len(expansionNamesCardCounts)
        expansionNames = list(expansionNamesCardCounts.keys())
        self.currentMaxPlayers = 0
        self.hasBlackCardsSelected = False
        self.expansionNamesCardCounts = expansionNamesCardCounts

        optionPages = {}
        embedKeys = []
        numPages = numExpansions // 5 + (0 if numExpansions % 5 == 0 else 1)
        
        for pageNum in range(numPages):
            embedKeys.append(lib.discordUtil.makeEmbed(titleTxt="Select Expansion Packs", desc="Which expansions would you like to use?",
                                                        footerTxt="Page " + str(pageNum + 1) + " of " + str(numPages) + \
                                                            " | This menu will expire in " + lib.timeUtil.td_format_noYM(timeout.expiryDelta)))
            embedKeys[-1].add_field(name="Currently selected:", value="​", inline=False)
            embedKeys[-1].add_field(name="Max players:", value="0", inline=False)
            optionPages[embedKeys[-1]] = {}

        for expansionNum in range(numExpansions):
            pageNum = expansionNum // 5
            pageEmbed = embedKeys[pageNum]
            optionEmoji = cfg.defaultEmojis.menuOptions[expansionNum % 5]
            expansionName = expansionNames[expansionNum]
            pageEmbed.add_field(name=optionEmoji.sendable + " : " + expansionName, value="`" + str(expansionNamesCardCounts[expansionName][0]) + " white cards | " + str(expansionNamesCardCounts[expansionName][1]) + " black cards`", inline=False)
            optionPages[pageEmbed][optionEmoji] = reactionMenu.NonSaveableSelecterMenuOption(expansionName, optionEmoji, msg.id)

        for page in embedKeys:
            page.add_field(name=cfg.defaultEmojis.accept.sendable + " : Submit", value="​", inline=False)
            page.add_field(name=cfg.defaultEmojis.cancel.sendable + " : Cancel", value="​", inline=False)
            page.add_field(name=cfg.defaultEmojis.spiral.sendable + " : Toggle all", value="​", inline=False)
            optionPages[page][cfg.defaultEmojis.cancel] = reactionMenu.NonSaveableReactionMenuOption("Cancel", cfg.defaultEmojis.cancel, addFunc=cancelGame, addArgs=msg.id)

        super().__init__(msg, pages=optionPages, timeout=timeout, targetMember=targetMember, targetRole=targetRole, owningBasedUser=owningBasedUser)


    async def updateSelectionsField(self):
        self.currentMaxPlayers = 0
        for option in self.selectedOptions:
            if self.selectedOptions[option]:
                self.currentMaxPlayers += self.expansionNamesCardCounts[option.name][0]
                if not self.hasBlackCardsSelected and self.expansionNamesCardCounts[option.name][1] > 0:
                    self.hasBlackCardsSelected = True
                
        self.currentMaxPlayers = self.currentMaxPlayers // cfg.cardsPerHand

        for pageEmbed in self.pages:
            pageEmbed.set_field_at(1, name=pageEmbed.fields[1].name, value=str(self.currentMaxPlayers), inline=False)
        
        # for pageEmbed in self.pages:
        #     for fieldIndex in range(len(pageEmbed.fields)):
        #         field = pageEmbed.fields[fieldIndex]
        #         if field.name == "Max players:":
        #             pageEmbed.set_field_at(fieldIndex, name=field.name, value=str(self.currentMaxPlayers))
        #         break

        await super().updateSelectionsField()
