class Player:
    # Example: Tag: Tarik; Elo: 1923,15; Elogain: +255,56; maincharacter: Greninja, country: "DE", state: "SH",
    # isactive: True, bestwin: [+40.63, "Raflow"]; worstloss: [-40.28, "RobinGG"]; wins: 142; losses: 31;
    # numberoftournaments: 22; upsets: 5
    def __init__(self, tag, elo, elogain, maincharacter, country, state, isactive, bestwin, worstloss, wins, losses,
                 numberoftournaments, upsets):
        self.tag = tag
        self.elo = elo
        self.elogain = elogain
        self.maincharacter = maincharacter
        self.country = country
        self.state = state
        self.isactive = isactive
        self.bestwin = bestwin
        self.worstloss = worstloss
        self.wins = wins
        self.losses = losses
        self.numberoftournaments = numberoftournaments
        self.upsets = upsets
        self.isalreadyfilled = False

    def getwinrate(self):
        winpercentage = "0%"
        games = self.gettotalgames()
        if games:
            winpercentage = str(round((self.wins / self.gettotalgames()) * 100, 2)) + "%"
        return winpercentage

    def gettotalgames(self):
        return self.wins + self.losses

    def getelogainpertournament(self):
        elogainpertournament = 0
        if self.numberoftournaments:
            elogainpertournament = round(self.elogain / self.numberoftournaments, 2)
        return elogainpertournament

    def getsetcount(self):
        return str(self.wins) + "-" + str(self.losses)

    def getbestwin(self):
        return str(self.bestwin[1]) + " (+ " + str(round(self.bestwin[0], 2)) + ")"

    def getworstloss(self):
        return str(self.worstloss[1]) + " (" + str(round(self.worstloss[0], 2)) + ")"

    def getupsetspertournament(self):
        upsetspertournament = 0
        if self.numberoftournaments:
            upsetspertournament = round(self.upsets / self.numberoftournaments, 2)
        return upsetspertournament
