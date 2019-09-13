import itertools, functools, copy

class CardQuality(int):
    names         = ('bronze', 'silver', 'gold')
    numberOfNames = len(names)
    __repr__      = lambda x: x.__class__.names[x]

    def __new__(cls, value):
        if isinstance(value, str):
            return int.__new__(cls, cls.names.index(value))
        if value < 0 or value > cls.numberOfNames:
            raise ValueError(f"value not in range 0 - {cls.numberOfNames}")
        return int.__new__(cls, value)

    @classmethod
    def all(cls):
        return [cls(indx) for indx in range(cls.numberOfNames)]

Bronze, Silver, Gold = CardQuality.all()


class Vat(dict):
    members     = ()
    __str__     = lambda x: str(x.contents())
    __repr__    = lambda x: " ".join([x.__class__.__name__, str(x.idNumber)])
    __eq__      = lambda x, y: x is y
    __getitem__ = lambda x, y: getattr(x, y)
    contents    = lambda x: dict([(member, x[member]) for member in x.__class__.members if hasattr(x, member)])
    items       = lambda x: x.contents().items()
    lastIdNumb  = 0

    def __init__(self, *arguments, **keywordArguments):
        dict.__init__(self)
        [setattr(self, self.__class__.members[indx], argument) for indx, argument in enumerate(arguments)]
        [setattr(self, argName, argVal) for argName, argVal in keywordArguments if argName in self.__class__.members]
        self.idNumber = Vat._counter()

    @staticmethod
    def _counter():
        Vat.lastIdNumb += 1
        return Vat.lastIdNumb


class ListVat(Vat):
    def __init__(self, *arguments, **keywordArguments):
        Vat.__init__(self, *arguments, **keywordArguments)
        [setattr(self, argName, []) for argName in self.__class__.members if not hasattr(self, argName)]


class DictionaryWithDefault(dict):
    default = 0

    def __getitem__(self, item):
        if item not in self:
            self[item] = DictionaryWithDefault.default
        return dict.__getitem__(self, item)


@functools.total_ordering
class Card(Vat):
    members = ('quality', 'contest', 'ownedBy', 'tiebreak')

    def __lt__(self, other):
        return (self.quality < other.quality) or ((self.quality == other.quality) and (self.tiebreak < other.tiebreak))

    def _setOwner(self, newOwner):
        if hasattr(self, 'ownedBy') and self.ownedBy is not None and newOwner is not None:
            self.ownedBy.unassignCard(self)
        self.ownedBy = newOwner
    owner = property(lambda x: x.ownedBy, _setOwner)

    @staticmethod
    def setTiebreaks(cardList):
        lastTiebreaks = DictionaryWithDefault()
        for card in cardList:
            lastTiebreaks[card.contest.idNumber] += 1
            card.tiebreak = lastTiebreaks[card.contest.idNumber]

    @staticmethod
    def extendWhereNew(newList, existingList):
        if isinstance(newList, list):
            [existingList.append(card) for card in newList if card not in existingList]


class Player(ListVat):
    members = ('cards', 'contests')
    distinct = lambda x, y, z: x._distinctPlayers(y, z)

    def __init__(self, *arguments, **keywordArguments):
        ListVat.__init__(self, *arguments, **keywordArguments)
        [setattr(card, 'owner', self) for card in self.cards]

    def __call__(self, other, contest=None, quality=None):
        for card in self.cards:
            if card.contest in other.contests:
                if (contest is None) or (contest is card.contest):
                    if (quality is None) or (quality >= card.quality):
                        return True
        return False

    def _distinctPlayers(self, allPlayers, level):
        if level == 0:
            yield from self._getPair(sorted(allPlayers, key=lambda x: len(x.cards)))
        else:
            for players in self._distinctPlayers(allPlayers, level - 1):
                yield from self._addNewPlayer(allPlayers, players)

    def _getPair(self, allPlayers):
        for p in allPlayers:
            if p is not self:
                for q in allPlayers:
                    if (q is not self) and (p is not q):
                        yield [p, q]

    def _addNewPlayer(self, allPlayers, players):
        for newPlayer in allPlayers:
            if newPlayer is not self:
                newFlag = True
                for oldPlayer in players:
                    if newPlayer is oldPlayer:
                        newFlag = False
                        break
                if newFlag:
                    yield players + [newPlayer]

    def assignCard(self, card):
        card.owner = self
        if card not in self.cards:
            self.cards.append(card)

    def unassignCard(self, card):
        card.owner = None
        while card in self.cards:
            self.cards.remove(card)

    def solvedForBronze(self, bronzePlayers, contest):
        for p, q in self.distinct(bronzePlayers, 0):
            if self(q) and p(self, contest, Bronze) and q(p) and not self(p) and not p(q) and not q(self):
                return True
        return False

    def solvedForSilver(self, silverPlayers, contest):
        for p, q, r in self.distinct(silverPlayers, 1):
            if self(r) and p(self, contest, Silver) and q(p) and r(q) and not self(p) and not self(q) and not p(q) \
                    and not p(r) and not q(r) and not q(self) and not r(self) and not r(p):
                return True
        return False

    def solvedForGold(self, goldPlayers, contest):
        for p, q, r, s in self.distinct(goldPlayers, 2):
            if self(s) and p(self, contest, Gold) and q(p) and r(q) and s(r) and not self(p) and not self(q) \
                    and not self(r) and not p(q) and not p(r) and not p(s) and not q(r) and not q(s) and not q(self) \
                    and not r(s) and not r(self) and not r(p) and not s(self) and not s(p) and not s(q):
                return True
        return False


class Contest(ListVat):
    members = ('participants',)
    __eq__ = lambda x, y: set([p.idNumber for p in x.participants]) == set([q.idNumber for q in y.participants])

    def __init__(self, *arguments, **keywordArguments):
        ListVat.__init__(self, *arguments, **keywordArguments)
        [player.contests.append(self) for player in self.participants if self not in player.contests]

    @property
    def positions(self):
        result = []
        for player in self.participants:
            qualities = [card.quality for card in player.cards if card.contest is self]
            if qualities:
                result.append((max(qualities), player),)
        result.sort()
        result.reverse()
        return result

    @property
    def winner(self):
        positions = self.positions
        if positions:
            return positions[0]
        return None

    @staticmethod
    def assignCards(cuts, method='assignCard'):
        [getattr(caller, method)(assigned) for caller, _, assigned in cuts]

    @staticmethod
    def _distinctResults(cuts, contest, level, contestLevel=1):
        if level == contestLevel:
            cuts[level][2].contest = contest
            return Contest._assignCuts(contest, cuts, level)
        lenCuts = len(cuts)
        for cutContest in cuts[(level - 1) % lenCuts][0].contests:
            cuts[level][2].contest = cutContest
            return Contest._assignCuts(contest, cuts, level)

    @staticmethod
    def _assignCuts(contest, cuts, level):
        if level == (len(cuts) - 1):
            return
        return Contest._distinctResults(cuts, contest, level + 1)

    @staticmethod
    def distinct(cuts, contest):
        yield Contest._distinctResults(cuts, contest, 0)

    @staticmethod
    def solve(playerList, method='bronzeForPlayer'):
        result     = []
        playerList = sorted(playerList, key=lambda x: len(x.cards))
        for a in playerList:
            for aCon in a.contests:
                newCards = getattr(Contest, method)(a, playerList, aCon)
                if newCards is False:
                    [card.owner.unassignCard(card) for card in result]
                    return False
                Card.extendWhereNew(newCards, result)
        return result

    @staticmethod
    def addContests(allPlayers, numberOfContests, sizeOfContests, method='bronzeForPlayer', batchSize=3):
        result   = []
        draw     = batchSize * sizeOfContests
        allCards = []
        oldCards = []
        solved   = True
        for _ in range(0, numberOfContests, batchSize):
            if not solved:
                break
            left    = copy.copy(allPlayers)
            numLeft = len(left)
            while numLeft >= sizeOfContests:
                if draw > numLeft:
                    draw = batchSize * (numLeft // batchSize)
                solved = False
                for combination in itertools.permutations(left, draw):
                    playerLists = [combination[indx: indx + batchSize] for indx in range(0, draw, batchSize)]
                    newContests = [Contest(playList) for playList in playerLists]
                    strikeList  = copy.copy(newContests)
                    unique      = Contest._removeDuplicates(newContests, result, strikeList)
                    if unique:
                        cards = Contest.solve(allPlayers, method)
                        if cards:
                            solved = True
                            break
                        Contest._removeContests(newContests)
                    else:
                        Contest._removeContests(strikeList)
                    newContests = None
                if solved:
                    result   += newContests
                    allCards += cards
                    oldCards  = copy.copy(cards)
                    [left.remove(player) for player in combination]
                    numLeft = len(left)
                else:
                    print(f"Can't add any more batches of {batchSize} contests")
                    cards = oldCards
                    break
        return result, allCards

    @staticmethod
    def _removeDuplicates(contestList, target, strikeList):
        unique = True
        for contest in contestList:
            if contest in target:
                unique = False
                while contest in strikeList:
                    strikeList.remove(contest)
        return unique

    @staticmethod
    def _removeContests(contestList):
        for contest in contestList:
            for play in contest.participants:
                if contest in play.contests:
                    play.contests.remove(contest)

    @staticmethod
    def _solveByShortCuts(shortCuts, result, contest):
        Contest.assignCards(shortCuts)
        for _ in Contest.distinct(shortCuts, contest):
            if Contest._checkAssignment(shortCuts):
                Contest._tryToUseExistingCards(result)
                return True
        Contest.assignCards(shortCuts, 'unassignCard')
        return False

    @staticmethod
    def bronzeForPlayer(a, playerList, aCon):
        """Getting a bronze card takes the least effort.
        For every player, p1, there exist two distinct other players, p2, p3, such that:
        p1 has no cards p2 wants,
        p1 has a bronze card p3 wants,
        p2 has no cards p3 wants,
        p2 has a bronze card p1 wants,
        p3 has no cards p1 wants,
        p3 has a bronze card p2 wants.

        p1 can get a bronze card by first swapping the card p3 wants to p3 in exchange
        for the card p2 wants, then swapping the card p2 wants to p2 for the card p1
        wants."""

        if a.solvedForBronze(playerList, aCon):
            return True
        result = aCard, bCard, cCard = [Card(Bronze), Card(Bronze), Card(Bronze)]
        for b, c in a.distinct(playerList, 0):
            shortCuts = ((a, (b,), cCard), (b, (c,), aCard), (c, (a,), bCard),)
            if Contest._solveByShortCuts(shortCuts, result, aCon):
                return result
        return False

    @staticmethod
    def silverForPlayer(a, playerList, aCon):
        """Getting a silver card takes the next least effort.
        For every player, p1, there exist three distinct other players, p2, p3, p4, such that:
        p1 has a silver card p4 wants,
        p1 has no cards p2 wants,
        p1 has no cards p3 wants,
        p2 has a silver card p1 wants,
        p2 has no cards p3 wants,
        p2 has no cards p4 wants,
        p3 has a silver card p2 wants,
        p3 has no cards p4 wants,
        p3 has no cards p1 wants,
        p4 has a silver card p3 wants,
        p4 has no cards p1 wants,
        p4 has no cards p2 wants.

        p1 can get a silver card by first swapping the card p4 wants to p4 in exchange
        for the card p3 wants, then swapping the card p3 wants to p3 for the card p2
        wants, then swapping the card p2 wants to p2 for the card p1 wants."""

        if a.solvedForSilver(playerList, aCon):
            return True
        result = aCard, bCard, cCard, dCard = [Card(Silver), Card(Silver), Card(Silver), Card(Silver)]
        for b, c, d in a.distinct(playerList, 1):
            shortCuts = ((a, (b, c,), dCard,), (b, (c, d,), aCard,), (c, (d, a,), bCard,), (d, (a, b,), cCard,),)
            if Contest._solveByShortCuts(shortCuts, result, aCon):
                return result
        return False

    @staticmethod
    def goldForPlayer(a, playerList, aCon):
        """Getting a gold card takes the most effort.
        For every player, p1, there exist four distinct other players, p2, p3, p4, p5, such that:
        p1 has a gold card p5 wants,
        p1 has no cards p2 wants,
        p1 has no cards p3 wants,
        p1 has no cards p4 wants,
        p2 has a gold card p1 wants,
        p2 has no cards p3 wants,
        p2 has no cards p4 wants,
        p2 has no cards p5 wants,
        p3 has a gold card p2 wants,
        p3 has no cards p4 wants,
        p3 has no cards p5 wants,
        p3 has no cards p1 wants,
        p4 has a gold card p3 wants,
        p4 has no cards p5 wants,
        p4 has no cards p1 wants,
        p4 has no cards p2 wants,
        p5 has a gold card p4 wants,
        p5 has no cards p1 wants,
        p5 has no cards p2 wants,
        p5 has no cards p3 wants.

        p1 can get a gold card by first swapping the card p5 wants to p45 in exchange
        for the card p4 wants, then swapping the card p4 wants to p4 for the card p3
        wants, then swapping the card p3 wants to p3 for the card p2 wants, then
        swapping the card p2 wants to p2 for the card p1 wants."""

        if a.solvedForGold(playerList, aCon):
            return True
        result = aCard, bCard, cCard, dCard, eCard = [Card(Gold), Card(Gold), Card(Gold), Card(Gold), Card(Gold)]
        for b, c, d, e in a.distinct(playerList, 2):
            shortCuts = ((a, (b, c, d,), eCard,), (b, (c, d, e,), aCard,), (c, (d, e, a,), bCard,),
                         (d, (e, a, b,), cCard,), (e, (a, b, c,), dCard,),)
            if Contest._solveByShortCuts(shortCuts, result, aCon):
                return result
        return False

    @staticmethod
    def _checkAssignment(shortCuts):
        for helper, helpList, _ in shortCuts:
            for helped in helpList:
                if helper(helped):
                    return False
        return True

    @staticmethod
    def _tryToUseExistingCards(result):
        removeList = []
        for card in copy.copy(result):
            [Contest._markDouble(card, oldCard, removeList) for oldCard in card.owner.cards if oldCard is not card]
        for card in removeList:
            while card in result:
                result.remove(card)

    @staticmethod
    def _markDouble(newCard, oldCard, removeList):
        if oldCard.quality == newCard.quality:
            if oldCard.contest == newCard.contest:
                if oldCard.owner == newCard.owner:
                    newCard.owner.unassignCard(newCard)
                    removeList.append(newCard)


if __name__ == '__main__':
    p1 = Player()
    p2 = Player()
    p3 = Player()
    p4 = Player()
    p5 = Player()
    p6 = Player()
    p7 = Player()
    p8 = Player()
    p9 = Player()
    allPlayers = [p1, p2, p3, p4, p5, p6, p7, p8, p9, ]

    allContests, allCards = Contest.addContests(allPlayers, 6, 3)

    """
    c1 = Contest((p1, p2, p3,),)
    c2 = Contest((p4, p5, p6,),)
    c3 = Contest((p7, p8, p9,),)
    c4 = Contest((p1, p4, p7,),)
    c5 = Contest((p2, p5, p8,),)
    c6 = Contest((p3, p6, p9,),)
    c10 = Contest((p2, p6, p9,),)
    c11 = Contest((p4, p7, p8,),)
    c12 = Contest((p1, p3, p5,),)
    allContests = [c1, c2, c3, c4, c5, c6, c10, c11, c12,]
    
    allCards = Contest.solve(allPlayers)
    """

    Card.setTiebreaks(allCards)

    print()
    for thingList in (allPlayers, allContests, allCards):
        for thing in thingList:
            print(repr(thing), thing)
        print()


