# functions.py
#
# Includes all non-messaging functionality of baxterbot
import traceback

import datetime
from dateutil.parser import parse
from pytz import timezone
import random
import json
import requests
import math
import mammoth
import re
from bs4 import BeautifulSoup

from bot.settings import OFFICER_PSIDS, PAGE_ACCESS_TOKEN

import bot.models as models
import bot.extract as extract


# ====== Specific functions ===== #
def find_dinner(message):
    search = ["dinner", "diner", "supper", "tonight", "dinenr", "night"]
    return any([term in message for term in search])
def find_breakfast(message):
    search = ["breakfast", "brekfast", "brekkie", "beakfast", "this morning"]
    return any([term in message for term in search])
def find_lunch(message):
    search = ["lunch", "lunc", "launch"]
    return any([term in message for term in search])
def findMeal(message):
    if find_dinner(message):
        return "dinner"
    if find_breakfast(message):
        return "breakfast"
    if find_lunch(message):
        return "lunch"
    return None

def findTime(message):

    addTime = datetime.timedelta(hours=0)

    today = datetime.datetime.now(timezone("Australia/Sydney"))
    days = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    if "tomorrow" in message or "tommorow" in message:
        addTime += datetime.timedelta(hours=24)

    for day in days:
        if day in message:  # if the day is mentioned
            dayDiff = days[day] - today.weekday()  # get difference between days
            if dayDiff < 0:  # if the day is "behind" current day, make day next week
                dayDiff += 7
            elif "next" in message:
                addTime += datetime.timedelta(hours=24 * 7)  # add this day next week

            addTime += datetime.timedelta(hours=24 * dayDiff)

    return addTime

def get_meal(meal, time) -> models.Meal:
    try:
        dino = (
            models.Meal.select()
            .where(models.Meal.date == time.date())
            .where(models.Meal.type == meal)
            .get()
        )
        return dino
    except Exception:
        return None

def get_current_meal():

    time = datetime.datetime.now(timezone('Australia/Sydney'))
    #breakfast = today.replace(hour=7, minute=0)
    lunch = time.replace(hour=11, minute=0) #people asking for dino at 11 are probably talking about lunch
    dinner = time.replace(
        hour=16, minute=0
    )  # just to make sure (starting at 4 so people can ask what's dino earlier for dinner)
    if time < lunch:
        # for today's breakfast
        return "breakfast"
    elif time < dinner:
        # for today's lunch
        return "lunch"
    else:
        # for today's dinner
        return "dinner"

def dinoRequest(meal, addTime):
    # meal is "dinner", "lunch" or "breakfast"
    dino = dinoRequestObj(meal, addTime)

    if dino is None:
        return None

    return "{} at dino is:\n{}".format(meal, dino.description)

def dinoRequestObj(meal, addTime) -> models.Meal:
    # meal is "dinner", "lunch" or "breakfast"
    today_AEST = datetime.datetime.now(timezone("Australia/Sydney"))

    today_AEST += addTime  # if no add time, timedelta will be 0 hours so no effect

    print("Date is: {}".format(today_AEST.date().strftime("%Y-%m-%d")))

    return get_meal(meal, today_AEST)

def getCurrentDino() -> models.Meal:

    time = datetime.datetime.now(timezone('Australia/Sydney'))

    meal = get_current_meal()
    return get_meal(meal, time)

def makeDinoVote(vote):

    dino = getCurrentDino()

    if vote == "goodvote":
        print("the meal has: {} likes".format(dino.likes))
        dino.likes = dino.likes + 1
    elif vote == "badvote":
        print("the meal has: {} likes".format(dino.dislikes))
        dino.dislikes = dino.likes + 1

    dino.save()


def dinoPoll():

    dino = getCurrentDino()

    if dino.likes == 0 and dino.dislikes == 0:
        message = "No one has voted for {}! 😢\nYou can be the first to vote with 'dinovote'".format(
            dino.type
        )

    elif dino.likes < dino.dislikes:
        perc = (dino.dislikes / (dino.dislikes + dino.likes)) * 100
        message = "{}% of people disliked {}.".format(perc, dino.type)

    elif dino.likes > dino.dislikes:
        perc = (dino.likes / (dino.dislikes + dino.likes)) * 100
        message = "{}% of people enjoyed {}!!!".format(perc, dino.type)

    else:
        message = "The crowd is split! Dino is a polarising meal.\nLet me know your thoughts with 'dinovote'"

    return message


# ======== J&D ========== #


# def set_jd(rs, switch):

#     jd_desc = ""

#     try:
#         if switch[1]:
#             message.bot.set_variable("jd_loc", switch[1])
#             jd_desc = " in the {}".format(switch[1])
#     except:
#         message.bot.set_variable("jd_loc", None)

#     if switch[0].lower() == "on":
#         message.bot.set_variable("jd", True)
#         # jd = True
#         return "COFFEE TIME!!! ☕️\nJ&D is ON" + jd_desc
#     else:
#         message.bot.set_variable("jd", None)
#         message.bot.set_variable("jd_loc", None)
#         return "No more coff! 😭"


# def get_jd(rs, args):

#     jd = message.bot.get_variable("jd")
#     jd_loc = message.bot.get_variable("jd_loc")

#     jd_desc = ""

#     if jd_loc:
#         jd_desc = " in the {}".format(jd_loc)

#     if jd:
#         return "J&D is ON" + jd_desc
#     else:
#         return "J&D is OFF 😭 😭 😭"


# # ===== Shopen ===== #

# # TODO: integrate this toggle action into a function so we are not duplicating functionality


# def set_shop(rs, switch):

#     if switch[0].lower() == "on":
#         message.bot.set_variable("shop", True)
#         return "Shopen!"
#     else:
#         message.bot.set_variable("shop", None)
#         return "Shclosed 😭"


# def get_shop(rs, args):

#     shop = message.bot.get_variable("shop")

#     return "Shopen!!!" if shop else "Shclosed 😭"


# ===== Baxter Events ===== #
# TODO: Move this into message module
def uploadAsset(assetUrl):

    r = requests.post(
        "https://graph.facebook.com/v2.6/me/message_attachments",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={
            "message": {
                "attachment": {
                    "type": "image",
                    "payload": {"is_reusable": True, "url": assetUrl},
                }
            }
        },
    )

    if r.status_code == 200:
        return r.json()
    else:
        print("Asset Upload has gone to shit -> ", r.status_code)
        return None


# ===== Hashbrowns ===== #

# def set_hashbrowns(rs, switch):

#     message.bot.set_variable('hashbrownsday', datetime.date.today())
#     if switch[0].lower() == 'on':
#         message.bot.set_variable('hashbrowns', True)
#         return "OMG best news ever! 😃 Your friends will arrive shortly..."
#     else:
#         message.bot.set_variable('hashbrowns', None)
#         return "N-n-n-noooooooo! 😭 Enjoy a lonely Dino, knowing you took one for the team..."

# def get_hashbrowns(rs, args):

#     if (message.bot.get_variable('hashbrownsday') == datetime.date.today()):
#         hashbrowns = message.bot.get_variable('hashbrowns')
#         return "Get out of bed! HASHBROWNS TODAY!!! 🥔🥔🎊🎉🎊🎉" if hashbrowns else "Bad news: no hashbrowns... stay in bed 😔"
#     else:
#         return "Nobody's been game to find out yet 🤔 Type 'sethashbrowns on' or 'sethashbrowns off' if you happen to get out of bed"


# ======= Semester In Progress ======= #
def semesterResponse():

    # is this hardcoded? yes.
    # do i give a shit? no. fuck you for judging me.
    semStart = datetime.date(2019, 5, 31)
    semEnd = datetime.date(2019, 9, 2)

    response = "{}\n\nThere are {} days left until the semester ends".format(
        progressBar(timeProgress(semStart, semEnd)), daysLeft(semEnd)
    )

    return response


def yearProgress():
    today = datetime.datetime.today() + datetime.timedelta(hours=11)  # to make it aest

    percentage = math.floor((today.timetuple().tm_yday / 365) * 100)

    return percentage


def timeProgress(start, end):
    today = datetime.datetime.today() + datetime.timedelta(hours=11)  # to make it aest

    totalDays = (end - start).days
    elapsedDays = (today.date() - start).days

    percentage = math.floor((elapsedDays / totalDays) * 100)

    return percentage


def daysLeft(end):
    today = datetime.datetime.today() + datetime.timedelta(hours=11)  # to make it aest

    return (end - today.date()).days


def progressBar(percentage):

    percBar = "0% "

    for i in range(10, 100, 10):
        percBar += "▓" if (i < percentage) else "░"

    percBar += " {}%".format(percentage)

    return percBar


# ===== Week Events ===== #
def getWeekEvents():

    today = datetime.datetime.today() + datetime.timedelta(hours=11)  # to make it aest
    # Take todays date. Subtract the number of days which already passed this week (this gets you 'last' monday).
    week_monday = today + datetime.timedelta(days=-today.weekday(), weeks=0)

    try:
        weekCal = (
            models.WeekCal.select()
            .where(models.WeekCal.week_start == week_monday.date())
            .get()
        )

        return weekCal.assetID
    except:
        return None


# ===== Get Room Number ===== #
def extractName(msg):
    half = msg.split("is", 1)[1].split()
    return " ".join(half[:2])


def getRoomNumber(name):

    try:
        gotName, confidence, ressie = models.Ressie.fuzzySearch(name)
        if confidence < 85:
            return "{} is in room {} (I'm {} percent sure I know who you're talking about)".format(
                gotName, ressie.room_number, confidence
            )
        return "{} is in room {}".format(gotName, ressie.room_number)
    except Exception as e:
        print(Exception, e)
        traceback.print_exc()
        return """I could not find a room number for '{}' ... are you sure they go to Baxter?
          \nPlease make sure you spell their full name correctly.\n\n (Fun fact: Some people use names that are not in fact their names. Nicknames won't work)""".format(
            " ".join(name).title()
        )

def dinoparse(lines):
    lines = extract.text_replace(lines)

    soup = BeautifulSoup(lines, features="html.parser")
    assert soup != None
    pretty = soup.prettify()
    
    rows = extract.get_rows(soup)

    mealsByDay = extract.get_meals(rows[1:])
    date, sucess = extract.extract_date(soup)
    return [date, sucess, mealsByDay, pretty]

