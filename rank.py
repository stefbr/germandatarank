import sqlite3

import elo
import utils
from collections import defaultdict
import time


def createranking(playersjson, setsjson, rankingname, tourneysin2022json, k_value, k_dynamic, countrycode):
    """Creates the elo-based ranking for all players with various statistics."""
    idtagdict = utils.getdictfromjson(playersjson)
    sets = utils.getdictfromjson(setsjson)
    tournamentsin2022 = utils.gettournamentsin2022(tourneysin2022json)

    playerelodict = defaultdict(lambda: utils.createnewplayer())
    # iterate over all sets, calculate elo/stats and save them to playerelodict
    for tourneyset in sets:
        winner = tourneyset[0]
        p1, p2 = tourneyset[1], tourneyset[2]
        loser = p1 if winner == p2 else p2

        tourneykey = tourneyset[6]
        setin2022 = tourneykey in tournamentsin2022

        # fill player class with information from idtagdict (tag, country, state, isactive, main, numoftourneys)
        playerelodict[winner] = utils.fillplayerinformation(idtagdict, playerelodict, winner)
        playerelodict[loser] = utils.fillplayerinformation(idtagdict, playerelodict, loser)

        winnerelo, loserelo = playerelodict[winner].elo, playerelodict[loser].elo
        newwinnerelo = updateelo(winnerelo, loserelo, 1, setin2022, k_value, k_dynamic)
        newloserelo = updateelo(loserelo, winnerelo, 0, setin2022, k_value, k_dynamic)
        # get best win in 2022
        if setin2022:
            # gain/loss for the current match
            winnergain = newwinnerelo - winnerelo
            loserloss = (loserelo - newloserelo) * -1

            # rating gain of the current best win
            bestwin = playerelodict[winner].bestwin[0]
            worstloss = playerelodict[loser].worstloss[0]
            if winnergain > bestwin:
                playerelodict[winner].bestwin = (winnergain, idtagdict[loser][0])
            if loserloss < worstloss:
                playerelodict[loser].worstloss = (loserloss, idtagdict[winner][0])

            # collect rating gain in 2022
            playerelodict[winner].elogain += winnergain
            playerelodict[loser].elogain += loserloss

            # collect set counts
            playerelodict[winner].wins += 1
            playerelodict[loser].losses += 1

            # collect upsets (= beating a higher elo player)
            if winnerelo < loserelo:
                playerelodict[winner].upsets += 1

        # update elo
        playerelodict[winner].elo = newwinnerelo
        playerelodict[loser].elo = newloserelo

        # debug for analysis
        # if p1 == "421694" or p2 == "421694":
        #     utils.printdebug(tourneyset, idtagdict, winner, winnerelo, newwinnerelo, loser, loserelo, newloserelo,
        #                      setin2022)

    # sort by Elo
    playerelodict = dict(sorted(playerelodict.items(), key=lambda x: x[1].elo, reverse=True))

    # playelodict: player info, rankingname: file name of ranking, countrycode: region the ranking is for (e.g. "DE")
    utils.writerankingtojson(playerelodict, rankingname, countrycode)


def updateelo(oldelo, opponentelo, result, setin2022, k_value, k_dynamic):
    # favour sets in 2022
    if setin2022:
        return elo.elo(oldelo, elo.expected(oldelo, opponentelo), result, k_dynamic)
    else:
        return elo.elo(oldelo, elo.expected(oldelo, opponentelo), result, k_value)


# TODO: very ugly, refactor maybe
def createh2hs(players, tournaments, sets):
    """Create h2h set counts between the given players (Top 150) for the current year"""
    idtagdict = utils.getdictfromjson(players)
    tournamentsin2022 = utils.gettournamentsin2022(tournaments)

    with open(sets, 'r', encoding="UTF-8") as f:
        setquery = f.read()
    with open("data/players/top150players.txt", "r") as f:
        top150players = f.read().splitlines()
    with open("data/players/top10players.txt", "r") as f:
        top10players = f.read().splitlines()
    h2hdict = defaultdict(lambda: [0, 0])
    # create h2h FOR these players
    for playerid in top150players:
        h2hdict[playerid] = [0, 0]
        # create h2h AGAINST these players
        for opponentid in top10players:
            # get set scores for playerid in "p1" and "p2" positions
            currentsetsasp1 = getset(setquery, playerid, opponentid)
            currentsetsasp2 = getset(setquery, opponentid, playerid)
            h2hdict = getscore(playerid, opponentid, currentsetsasp1, tournamentsin2022, h2hdict, idtagdict)
            h2hdict = getscore(playerid, opponentid, currentsetsasp2, tournamentsin2022, h2hdict, idtagdict)

    # output
    with open("data/rankings/h2hs.txt", "w", encoding="UTF-8") as f:
        for playerid, [wins, losses] in h2hdict.items():
            games = wins + losses
            percentage = "0%"
            if games:
                percentage = str(round((wins / games) * 100, 2)) + "%"
            h2hstring = str(wins) + "-" + str(losses) + " (" + percentage + ")"
            f.write(h2hstring + "\n")


def getscore(playerid, opponentid, currentsets, tournamentsin2022, h2hdict, idtagdict):
    """Gets the score from the given tournament set and sets it as value in our h2hdict"""
    for tourneyset in currentsets:
        # skip tourneys no in 2022
        if tourneyset[5] not in tournamentsin2022:
            # print(tourneyset[5], "is not in 2022, skipping...")
            continue
        # skip dqs
        if tourneyset[3] == -1 or tourneyset[4] == -1:
            continue
        winnerid = tourneyset[0]
        if winnerid == playerid:
            h2hdict[playerid][0] += 1
            print(idtagdict[playerid][0], "wins vs", idtagdict[opponentid][0])
        else:
            h2hdict[playerid][1] += 1
            print(idtagdict[playerid][0], "loses vs", idtagdict[opponentid][0])
    return h2hdict


def getset(query, player, opponent):
    """Gets the set with the given player IDs from the database"""
    query = query.replace("<P1>", player).replace("<P2>", opponent)
    con = sqlite3.connect("data/ultimate_player_database_updated.db")
    cur = con.cursor()
    sets = cur.execute(query)
    return sets.fetchall()


if __name__ == '__main__':
    startTime = time.time()
    playerspath = "data/players/playersglobal.json"
    setpath = "data/sets/globalsetseurope_48entrants.json"
    rankingpath = "data/rankings/updated_global_alltime_k30-45_entrants48_active48(3)_DE"
    tourneysin2022path = "data/tournaments/globaltournamentsin2022.json"
    k = 30
    # dynamic k value to value sets in the current more
    k_2022 = 45

    # Step 1: write all 2022 tournaments to json
    # utils.writetournamentsin2022tojson("data/sql/globaltournamentsin2022query.txt",
    #                                    "data/tournaments/globaltournamentsin2022.json")

    # Step 2: get all players and write to file with various stats
    # utils.writeplayerstojson("data/tournaments/globaltournamentsin2022.json",
    #                          "data/sql/allplayersquery.txt",
    #                          "data/players/playersglobal.json")

    # Step 3: crawl all tournament sets played
    # utils.writesetstojson("data/sql/globaltournamentsquery.txt", "data/sets/globalsetseurope_48entrants.json")

    # Step 4: create ranking by iterating over all sets and calculating elo, stats and save to file
    # createranking(playerspath, setpath, rankingpath, tourneysin2022path, k, k_2022, "DE")

    print("Runtime: {0} seconds".format(time.time() - startTime))
