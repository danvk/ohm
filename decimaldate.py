"""
decimaldate.py
https://github.com/OpenHistoricalMap/decimaldate-python
"""

import re
import math


DECIMALPLACES = 5;
RE_YEARMONTHDAY = re.compile(r'^(\-?\+?)(\d+)\-(\d\d)\-(\d\d)$')


def iso2dec(isodate):
    # parse the date into 3 integers and maybe a minus sign
    # validate that it's a valid date
    datepieces = RE_YEARMONTHDAY.match(isodate)
    if not datepieces:
        raise ValueError(f"iso2dec() malformed date {isodate}")

    (plusminus, yearstring, monthstring, daystring) = datepieces.groups()
    monthint = int(monthstring)
    dayint = int(daystring)
    if plusminus == '-':
        yearint = -1 * int(yearstring)
    else:
        yearint = int(yearstring)

    if yearint <= 0:  # ISO 8601 shift year<=0 by 1, 0=1BCE, -1=2BCE; we want proper negative integer
        yearint -= 1

    if not isvalidmonthday(yearint, monthint, dayint):
        raise ValueError(f"iso2dec() invalid date {isodate}")

    # number of days passed = decimal portion
    # if BCE <=0 then count backward from the end of the year, instead of forward from January
    decbit = proportionofdayspassed(yearint, monthint, dayint)

    if yearint < 0:
        # ISO 8601 shift year<=0 by 1, 0=1BCE, -1=2BCE; we want string version
        # so it's 1 to get from the artificially-inflated integer (string 0000 => -1 for math, +1 to get back to 0)
        decimaloutput = 1 + 1 + yearint - (1 - decbit)
    else:
        decimaloutput = yearint + decbit

    # round to standardized number of decimals
    decimaloutput = round(decimaloutput, DECIMALPLACES)
    return decimaloutput


def dec2iso(decdate):
    # remove the artificial +1 that we add to make positive dates look intuitive
    truedecdate = decdate - 1;
    ispositive = truedecdate > 0;

    # get the integer year
    if ispositive:
        yearint = math.floor(truedecdate) + 1
    else:
        yearint = -abs(math.floor(truedecdate))

    # how many days in year X decimal portion = number of days into the year
    # if it's <0 then we count backward from the end of the year, instead of forward into the year
    dty = daysinyear(yearint)
    targetday = dty * (abs(truedecdate) % 1)
    if ispositive:
        targetday = math.ceil(targetday)
    else:
        targetday = dty - math.floor(targetday)

    # count up days months at a time, until we reach our target month
    # then the remainder (days) is the day of that month
    dayspassed = 0
    monthint = 1
    while monthint <= 12:
        dtm = daysinmonth(yearint, monthint)
        if dayspassed + dtm < targetday:
            dayspassed += dtm
        else:
            break
        monthint += 1
    dayint = targetday - dayspassed

    # make string output
    # months and day as 2 digits
    # ISO 8601 shift year<=0 by 1, 0=1BCE, -1=2BCE
    monthstring = f"{monthint:02}"
    daystring = f"{dayint:02}"
    if yearint > 0:
        yearstring = f"{yearint:04}"  # just the year as 4 digits
    elif yearint == -1:
        yearstring = f"{abs(yearint + 1):04}"  # BCE offset by 1 but do not add a - sign
    else:
        yearstring = '-' + f"{abs(yearint + 1):04}"  # BCE offset by 1 and add  - sign

    return f"{yearstring}-{monthstring}-{daystring}"


def daysinyear(yearint):
    dty = 366 if isleapyear(yearint) else 365
    return dty


def isleapyear(yearint):
    if yearint != int(yearint) or yearint == 0:
        raise ValueError(f"isleapyear() invalid year {yearint}")

    # don't forget BCE; there is no 0 so leap years are -1, -5, -9, ..., -2001, -2005, ...
    # just add 1 to the year to correct for this, for this purpose
    yearnumber = yearint if yearint > 0 else yearint + 1

    isleap = yearnumber % 4 == 0 and (yearnumber % 100 != 0 or yearnumber % 400 == 0)
    return isleap


def daysinmonth(yearint, monthint):
    monthdaycounts = {
        1: 31,
        2: 28,  # February
        3: 31,
        4: 30,
        5: 31,
        6: 30,
        7: 31,
        8: 31,
        9: 30,
        10: 31,
        11: 30,
        12: 31,
    }

    if isleapyear(yearint):
        monthdaycounts[2] = 29

    return monthdaycounts[monthint]


def isvalidmonthday(yearint, monthint, dayint):
    if type(yearint) != int:
        return False
    if type(monthint) != int:
        return False
    if type(dayint) != int:
        return False

    if monthint < 1 or monthint > 12:
        return False
    if dayint < 1:
        return False

    dtm = daysinmonth(yearint, monthint)
    if not dtm:
        return False
    if dayint > dtm:
        return False

    return True


def proportionofdayspassed(yearint, monthint, dayint):
    if type(yearint) != int:
        raise ValueError(f"proportionofdayspassed() invalid yearint {yearint}")
    if type(monthint) != int:
        raise ValueError(f"proportionofdayspassed() invalid monthint {monthint}")
    if type(dayint) != int:
        raise ValueError(f"proportionofdayspassed() invalid dayint {dayint}")

    # tally the days...
    dayspassed = 0

    # count the number of days to get through the prior months
    m = 1
    while m < monthint:
        dtm = daysinmonth(yearint, m)
        dayspassed += dtm
        m += 1

    # add the leftover days not in a prior month
    # but minus 0.5 to get us to noon of the target day, as opposed to the end of the day
    dayspassed = dayspassed + dayint - 0.5

    # divide by days in year, to get decimal portion
    # even January 1 is 0.5 days in since we snap to 12 noon
    dty = daysinyear(yearint)
    return dayspassed / dty
