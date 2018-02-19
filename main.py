import time
import os
import sys

from urllib.request import urlopen, build_opener, install_opener, HTTPCookieProcessor
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import smtplib
import argparse
import http
import datetime
from user_data import targets, API_TOKEN

parser = argparse.ArgumentParser()
parser.add_argument('--local', action='store_true')
args = parser.parse_args()

page_url = 'https://horsemanager.se/lessons_daylist?farm_id=405&plant_id=95'

TIME_START_END = {
    'mon': [datetime.time(13, 55), datetime.time(18, 0)],
    'tue': [datetime.time(13, 55), datetime.time(18, 0)],
    'wed': [datetime.time(13, 55), datetime.time(18, 0)],
    'thu': [datetime.time(13, 55), datetime.time(18, 0)],
    'fri': [datetime.time(13, 55), datetime.time(18, 0)],
    'sat': [datetime.time(11, 55), datetime.time(16, 0)],
    'sun': [datetime.time(11, 55), datetime.time(16, 0)],
}

sleep_hour = 3600
sleep_10_min = 600

day_polled = ''

def push(msg, user_keys):
    print('Trying to push!')
    for user_key in user_keys:
        try:
            conn = http.client.HTTPSConnection("api.pushover.net:443")
            conn.request("POST", "/1/messages.json",
                urlencode({
                    "token": API_TOKEN ,
                    "user": user_key,
                    "message":  msg,
                    "url": page_url,
                    "url_title": 'Dagens hästlista',
                }), { "Content-type": "application/x-www-form-urlencoded" })
            conn.getresponse()
        except:
            print('Failed!')
        else:
            print('Success!')

def parse_page(url):
    print('Parsing page')
    if args.local:
        page = open('Horsemanager.html')
    else:
        page = urlopen(url)
    soup = BeautifulSoup(page.read(), 'html.parser')

    alert = soup.find('p', {'class': 'alert'})
    if alert:
        print(alert.text)
        return None
    else:
        return soup

def find_pupil(soup, target):
    horses = {}
    my_horse = None
    for lesson in soup.find_all('div', {'id': 'lesson'}):
        header = lesson.find('div', {'id': 'lesson_header'})
        time = header.find('div', {'id': 'time'}).text.strip()
        group = header.find('div', {'id': 'group'}).text.strip()
        track = header.find('div', {'id': 'track'}).text.strip()
        teacher = header.find('div', {'id': 'admin'}).text.strip()
        subject = header.find('div', {'id': 'subject'}).text.strip()

        for entry in lesson.find_all('div', {'id': 'lesson_pupil'}):
            pupil_name = entry.find('div', {'id': 'pupil'}).text.strip()
            horse = entry.find('div', {'id': 'horse'}).text.strip()
            box = entry.find('div', {'id': 'box'}).text.strip()
            status = entry.find('div', {'id': 'fetch_leave'}).text.strip()

            horses[horse] = horses.get(horse, []) + [[time, group, track, teacher, subject, pupil_name, horse, box, status]]

            if target == pupil_name:
                my_horse = horse

    if my_horse is None:
        return None, None
    return my_horse, horses[my_horse]

def poll_page():
    global day_polled
    print('Polling page')

    pushed_today = False

    sleep_time = sleep_10_min

    while True:
        weekday = time.strftime('%a').lower()
        time_start, time_end = TIME_START_END[weekday]

        now = datetime.datetime.now().time()
        if time_start <= now <= time_end:
            print('In time frame!')
            today = time.strftime('%m-%d')

            if day_polled == today:
                print('Already polled today')
                sleep_time = sleep_hour
            else:
                soup = parse_page(page_url)
                if soup is not None:
                    day_polled = today
                    return soup
        else:
            sleep_time = sleep_10_min
            print('Not in time frame.')
            print('Start: {}, end: {}, now: {}'.format(time_start, time_end, now.strftime("%H:%M:%S")))
        # Sleep
        print()
        for sec in range(sleep_time):
            print('\033[F\033[KSleeping, polling in: {}'.format(sleep_time-sec))
            time.sleep(1)
        print()

def main():
    soup = poll_page()

    for target, user_keys in targets.items():
        print('TARGET: {}'.format(target))
        my_horse, result = find_pupil(soup, target)
        if result is None:
            print('Failed for name: {}'.format(target))
        else:
            my_lesson_msg = ''
            other_lessons_msg = []
            for entry in result:
                time, group, track, teacher, subject, pupil_name, horse, box, status = entry

                if pupil_name == target:
                    my_lesson_msg = '{}, {}\n{}'.format(horse, status if status else 'mitten', subject if subject else 'Okänd lektion')
                other_lessons_msg.append('{}, {} - {}, {}'.format(time, status if status else 'mitten', pupil_name, track))

            print(my_lesson_msg)
            print()
            for lesson in other_lessons_msg:
                print(lesson)

            msg = '{} \n\n{}'.format(my_lesson_msg, '\n'.join(other_lessons_msg))
            push(msg, user_keys)

if __name__ == '__main__':
    for user in targets.keys():
        print('Users: {}'.format(user))
    while True:
        main()
