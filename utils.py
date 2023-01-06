import json
import sqlite3
from collections import defaultdict

import xlsxwriter

import player


def writeplayerstojson(tournamentsquery, playersquery, path):
    """Creates a dictionary consisting of all players and various info and writes it to JSON a dictionary
    in the following format: { "playerid": [playertag, countrycode, isactive, character, numberoftournaments, state] }.
    Needed for storing & accessing player info during rank calcclations."""
    idtagdict = {}
    tournamentsin2022 = gettournamentsin2022(tournamentsquery)
    with open(path, "w", encoding="UTF-8") as f:
        players = getdatafromdatabase(playersquery)
        for currentplayer in players.fetchall():
            playerplacings = []
            placings = json.loads(currentplayer[3])
            for placing in placings:
                # only consider tournaments the player did not DQ from
                if not placing["dq"]:
                    playerplacings.append(placing["key"])

            numberoftourneys = len(set(playerplacings).intersection(tournamentsin2022))
            # at least 3 tournaments with 48+ entrants are needed to be "active" in a year
            isactive = numberoftourneys >= 3
            characters = json.loads(currentplayer[4])
            character = getmaincharacter(characters)
            # Format: { "2528159" : (Tarik, "DE", True, Greninja, 21, "SH") }
            idtagdict[currentplayer[0]] = (
                currentplayer[1], currentplayer[2], isactive, character, numberoftourneys, currentplayer[5])
        jsonfile = json.dumps(idtagdict)
        f.write(jsonfile)


def writesetstojson(query, path):
    """Creates a list containing all non-DQed sets in chronological order and writes it into a JSON file.
    Needed for elo calculation for each player."""
    tournaments = getdatafromdatabase(query)
    sets = []
    for tournament in tournaments.fetchall():
        print("Processing tournament", tournament[0])
        tourneykey = tournament[1]
        tourneysets = gettournamentsets(tourneykey)
        grandfinal = ()
        reset = ()
        for tourneyset in tourneysets.fetchall():
            p1score, p2score = tourneyset[3], tourneyset[4]
            # skip DQ sets
            if p1score == -1 or p2score == -1:
                continue
            # A, B, C, ... , AA, AB, AC, ... 0_ for grands/reset
            setorder = tourneyset[5]
            # fix chronological order to make sure grands/a potential reset are at the end of the tourney
            if setorder[0] == "0":
                if grandfinal:
                    reset = tourneyset
                else:
                    grandfinal = tourneyset
                continue

            sets.append(tourneyset)

        if grandfinal:
            sets.append(grandfinal)
        if reset:
            sets.append(reset)
    print("Number of all sets:", len(sets))
    jsonsets = json.dumps(sets)
    with open(path, "w", encoding="UTF-8") as f:
        f.write(jsonsets)


def writerankingtojson(playerelodict, path, countrycode):
    """Writes the collected ranking information into .txt and .xlsx files with proper formatting."""
    count = 1
    with open(path, "w", encoding="UTF-8") as f:
        excelrows = []
        f.write(
            "{:<4} {:<13} {:<13} {:<13} {:<13} {:<15} {:<25} {:<25} {:<20} {:<20} {:<20} {:<10} {:<10} {:<10}"
            .format("No.", "Tag", "Elo", "Sets", "Win %", "Character", "Best Win", "Worst Loss", "Elo Gain in 2022",
                    "Tournaments in 2022", "Elo Gain/Tournament", "State", "Upsets", "Upsets/Tournament"))
        f.write("\n")
        for playerid, currentplayer in playerelodict.items():
            # Skip some austrian/swiss people
            if playerid == "1022947" or playerid == "215346":
                continue
            gainin2022 = round(currentplayer.elogain, 2)
            gainin2022string = "{0:+g}".format(gainin2022, 2)
            tag = currentplayer.tag
            elo = round(currentplayer.elo, 2)
            winrate = currentplayer.getwinrate()
            setcountstring = currentplayer.getsetcount()
            country = currentplayer.country
            state = currentplayer.state
            isactive = currentplayer.isactive
            character = currentplayer.maincharacter
            numberoftourneys = currentplayer.numberoftournaments
            elogainpertourney = currentplayer.getelogainpertournament()
            winstring = currentplayer.getbestwin()
            lossstring = currentplayer.getworstloss()
            upsets = currentplayer.upsets
            upsetspertournament = currentplayer.getupsetspertournament()
            excelrow = [str(count) + ".", tag, elo, setcountstring, winrate, character, winstring, gainin2022,
                        numberoftourneys, elogainpertourney, state, upsets, upsetspertournament]

            eulist = ["DE", "GB", "NL", "FR", "IT", "BE", "LU", "ES", "AT", "IT", "DK", "CH", "SE", "NO", "FI", "IE",
                      "GR"]
            # only print players for certain country + if they are classified as active
            if country == countrycode and isactive:
                formatlist = [str(count) + ".", str(tag), str(elo), str(setcountstring), str(winrate), str(character),
                              str(winstring), str(lossstring), str(gainin2022string), str(numberoftourneys),
                              str(elogainpertourney), str(state), str(upsets), upsetspertournament]
                line = "{:<4} {:<13} {:<13} {:<13} {:<13} {:<15} {:<25} {:<25} {:<20} {:<20} {:<20} {:<10} {:<10} " \
                       "{:<10}".format(*formatlist)
                excelrows.append(excelrow)

                # printhtmltags(str(count), str(tag), str(elo), gainin2022string, character)
                f.write(line + "\n")
                count += 1
        writeexcelfile(excelrows, countrycode)


def writetournamentsin2022tojson(query, path):
    """Gets 2022 tournaments from the DB and writes them into a JSON file. Needed for rank calculation."""
    tournamentsin2022 = getdatafromdatabase(query)
    jsontournaments = json.dumps(tournamentsin2022.fetchall())
    with open(path, "w", encoding="UTF-8") as f:
        f.write(jsontournaments)


def writeexcelfile(excelrows, countrycode):
    """Writes info into an ugly excel file. Just copy paste it into a nice Google Sheet."""
    workbook = xlsxwriter.Workbook("data/rankings/updated_ranking_" + countrycode + ".xlsx")
    worksheet = workbook.add_worksheet()
    mainformat = workbook.add_format()
    mainformat.set_bg_color("dde8cb")
    mainformat.set_border(1)
    mainformat.set_center_across()
    titleformat = workbook.add_format()
    titleformat.set_bg_color("afd095")
    titleformat.set_border(1)
    titleformat.set_bold(1)
    titleformat.set_center_across()
    title = ["No.", "Tag", "Elo", "Set Count", "Win %", "Character", "Best Win", "Elo Gain in 2022",
             "Tournaments in 2022", "Elo Gain/Tournament", "State", "Upsets", "Upsets/Tournament"]
    row = 1
    col = 0

    for n in title:
        worksheet.write_string(0, col + title.index(n), n, titleformat)

    for [no, tag, elo, setcount, winrate, character, bestwin, gainin2022, numoftournaments, elogainpertourney,
         state, upsets, upsetspertournament] in excelrows:
        worksheet.write_string(row, col, no, mainformat)
        worksheet.write_string(row, col + 1, tag, mainformat)
        worksheet.write_number(row, col + 2, elo, mainformat)
        worksheet.write_string(row, col + 3, setcount, mainformat)
        worksheet.write_string(row, col + 4, winrate, mainformat)
        worksheet.write_string(row, col + 5, character, mainformat)
        worksheet.write_string(row, col + 6, bestwin, mainformat)
        worksheet.write_number(row, col + 7, gainin2022, mainformat)
        worksheet.write_number(row, col + 8, numoftournaments, mainformat)
        worksheet.write_number(row, col + 9, elogainpertourney, mainformat)
        worksheet.write_string(row, col + 10, state, mainformat)
        worksheet.write_number(row, col + 11, upsets, mainformat)
        worksheet.write_number(row, col + 12, upsetspertournament, mainformat)
        row += 1

    workbook.close()


# Example: Tag: Tarik; Elo: 1923,15; Elogain: +255,56; maincharacter: Greninja, country: "DE", state: "SH",
# isactive: True, bestwin: [+40.63, "Raflow"]; worstloss: [-40.28, "RobinGG"]; wins: 142; losses: 31;
# numberoftournaments: 22; upsets: 5
def createnewplayer():
    """Creates a new Player instance with all necessary info. Some fields are only filled at a later time."""
    newplayer = player.Player("", 1000, 0, "", "", "", False, [0, ""], [0, ""], 0, 0, 0, 0)
    return newplayer


# (Tarik, "DE", True, Greninja, 21, "SH") }
def fillplayerinformation(idtagdict, playerelodict, playerid):
    """Transports various information between the two dictionaries such that we do not need idtagdict anymore later."""
    currentplayer = playerelodict[playerid]
    if not currentplayer.isalreadyfilled and playerid is not None:
        currentplayer.tag = idtagdict[playerid][0]
        currentplayer.country = idtagdict[playerid][1]
        currentplayer.isactive = idtagdict[playerid][2]
        currentplayer.maincharacter = idtagdict[playerid][3]
        currentplayer.numberoftournaments = idtagdict[playerid][4]
        currentplayer.state = idtagdict[playerid][5]
        currentplayer.isalreadyfilled = True
    return currentplayer


def gettournamentsin2022(path):
    """Reads the 2022 tournaments from a given JSON file path and returns them as a list."""
    tournaments = getdictfromjson(path)
    tourneys2022 = []
    for tournament in tournaments:
        tourneys2022.append(tournament[1])
    return tourneys2022


def getmaincharacter(characters):
    """Gets the player's main character according to the Smashdata DB. Might often be badly formatted and/or wrong."""
    character = ""
    if characters:
        characters = dict(sorted(characters.items(), key=lambda x: x[1], reverse=True))
        # {"ultimate/falco" : 100, ...} -> Falco
        if characters:
            character = list(characters)[0].split("/")[1].title()
    return character


def getdatafromdatabase(path):
    """Reads in a SQL query from the given file path and executes it to retrieve information from the Smashdata database,
    then returns the result."""
    with open(path, 'r', encoding="UTF-8") as f:
        query = f.read()
    con = sqlite3.connect("data/ultimate_player_database_updated.db")
    cur = con.cursor()
    result = cur.execute(query)
    return result


def gettournamentsets(tourneykey):
    """Reads in a SQL query from tournamentsetsquery.txt, replaces the tournament key with the given tourneykey
     and returns all the sets played in that tournament."""
    with open('data/sql/tournamentsetsquery.txt', 'r', encoding="UTF-8") as f:
        tournamentsetsquery = f.read().replace("<TOURNAMENT_KEY>", tourneykey)
    con = sqlite3.connect("data/ultimate_player_database_updated.db")
    cur = con.cursor()
    tourneysets = cur.execute(tournamentsetsquery)
    return tourneysets


def getdictfromjson(path):
    """Reads in a JSON file and returns the content as a dictionary."""
    with open(path, encoding="UTF-8") as f:
        jsondict = json.load(f)
    print("Number of all", path, len(jsondict))
    return jsondict


def printdebug(tourneyset, idtagdict, winner, winnerelo, newwinnerelo, loser, loserelo, newloserelo, setin2022):
    """Prints out various information for debugging purposes."""
    print("Tournament:", tourneyset[6])
    print(idtagdict[winner][0], "vs.", idtagdict[loser][0])
    print("Winner:", idtagdict[winner][0], ". Old Elo:", winnerelo, "New Elo:", newwinnerelo,
          "Difference: +", newwinnerelo - winnerelo)
    print("Loser:", idtagdict[loser][0], ". Old Elo:", loserelo, "New Elo:", newloserelo, "Difference: -",
          loserelo - newloserelo)
    print("SET IN 2022:", setin2022)
    print("-----------------------------------------------------------------------------------------------")


def printhtmltags(count, tag, elo, gainin2022string, character):
    htmlstring = "<tr> \n \
            <td class=\"rank-cell\">" + str(count) + "</td> \n \
            <td class=\"tag-cell\">" + tag + "</td> \n \
            <td class=\"main-cell\"><img src=\"" + character.replace(" ", "") + ".webp\", height=\"80px\", width=\"80px\", align=\"left\"></td> \n \
            <td class=\"rating-cell\">" + elo + "</td> \n \
            <td class=\"rating-gain-cell\">" + gainin2022string + "</td> \n \
            </tr>"
    print(htmlstring)
