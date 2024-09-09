#! /usr/bin/python3

import collections
import datetime

import dateutil.parser
import dateutil.tz
import icalendar
from lxml import etree
import pytz
import requests

def get_html_element(url):
  response = requests.get(url)
  return etree.HTML(response.content)

def get_text_singleton_of_element(element):
  text_nodes = element.xpath('text()')
  if len(text_nodes) == 0:
    return None
  else:
    [text_node] = text_nodes
    return text_node

def extract_game_details_from_table_elements(table_elements):
  games_by_team = collections.defaultdict(list)

  for table_element in table_elements:
    is_bad_weather_event = 'badweathertable' in table_element.get('class').split()

    [table_body_element] = table_element.xpath('tbody')

    for tr_element in table_body_element.xpath('tr'):
      td_elements = tr_element.xpath('td')
      date_str, time_str, home_team, away_team, field = map(get_text_singleton_of_element, td_elements)

      # The separator rows in the table have no text nodes (datestr is None).
      if date_str is not None:
        games_by_team[home_team].append([date_str, time_str, home_team, away_team, is_bad_weather_event, field])
        games_by_team[away_team].append([date_str, time_str, home_team, away_team, is_bad_weather_event, field])

  return games_by_team

def make_icalendar_for_team(team_name, games_by_team, url, tz_name):
  tz = pytz.timezone(TZ_NAME)

  cal = icalendar.Calendar()

  cal.add('X-WR-CALNAME', 'BIS Academy: ' + team_name)
  cal.add('X-WR-CALDESC', 'extracted from ' + url)
  cal.add('X-WR-TIMEZONE', tz_name)

  for date_str, time_str, home_team, away_team, is_bad_weather_event, field in games_by_team[team_name]:
    dt = tz.localize(dateutil.parser.parse(date_str + ' ' + time_str))

    event = icalendar.Event()
    event.add('summary', f'⚽️ {away_team} @ {home_team}')
    event.add('dtstart', dt)
    event.add('dtend',   dt + datetime.timedelta(hours=1))

    location = {
      True:  'Boulder Indoor Soccer',
      False: 'Foothills Community Park'
    }[is_bad_weather_event]

    event.add('location', location)

    jersey_color = {
      home_team: 'blue',
      away_team: 'white'
    }[team_name]

    event.add('description', f'''field: {field}
jersey: {jersey_color}''')
  
    cal.add_component(event)

  return cal

if __name__ == '__main__':
  URL = 'https://boulderindoorsoccer.com/bis-academy/bis-schedules/'
  TZ_NAME = 'America/Denver'

  html_element = get_html_element(URL)

  # This XPath filter matches "tablexpress" while avoiding matching, e.g. "tableexpressFoo".
  table_elements = html_element.xpath("//table[contains(concat(' ', normalize-space(@class), ' '), ' tablepress ')]")

  games_by_team = extract_game_details_from_table_elements(table_elements)

  for team_name in games_by_team.keys():
    cal = make_icalendar_for_team(team_name, games_by_team, URL, TZ_NAME)

    filename = team_name + '.ics'

    print(f'writing "{filename}"')
    with open(filename, 'wb') as f:
      f.write(cal.to_ical())
