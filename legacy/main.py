import requests
import json
import sys
import datetime
import pytz
import csv
from pathlib import Path

postalCode = "1747"

start_date = '2026-08-13'
end_date = '2026-08-16'

start_hour = "13"
end_hour = "18"

name = f"{postalCode}_{start_date}_{end_date}"
file = f"{Path.home()}/Desktop/{name}.csv"

url = 'https://api.tibber.com/v1-beta/gql'
token = '8vsiJTQcUlQc5a4CLIAFo-g-h-niQJD3lBAB7VK_Op0'
timezone = pytz.timezone('Europe/Oslo')

query = """{
viewer {
    homes {
      address {
        postalCode
      }
      consumption(resolution: HOURLY, last: 1) {
        nodes {
          from
          to
          cost
          unitPrice
          unitPriceVAT
          consumption
          consumptionUnit
        }
      }
    }
  }
}"""

def get_diff_hours(start):
    now = timezone.localize(datetime.datetime.now())
    diff = now - start
    return (diff.days * 24) + (diff.seconds / 3600)


def get_date(date_time_str):
    return timezone.localize(datetime.datetime.strptime(date_time_str, '%Y-%m-%dT%H:%M:%S'))


def get_vat_cost(node):
    price = node['unitPrice'] + node['unitPriceVAT']
    return node['consumption'] * price


def trunc(float):
    return "{:.2f}".format(float)


def main():
    start = get_date(f'{start_date}T{start_hour}:00:00')
    end = get_date(f'{end_date}T{end_hour}:00:00')

    diff_hours = int(get_diff_hours(start))
    #print(diff_hours)

    q = query.replace('last: 1', f'last: {diff_hours}')
    #print(q)

    response = requests.post(url, headers={'Authorization': f'Bearer {token}'}, json={'query': q})
    status_code = response.status_code

    if status_code != 200:
        print(status_code)
        sys.exit(1)

    data = json.loads(response.text)
    #print(data)

    # nodes = data['data']['viewer']['homes'][0]['consumption']['nodes']

    homes = data['data']['viewer']['homes']
    nodes = []
    for home in homes:
        if home['address']['postalCode'] == postalCode:
            nodes = home['consumption']['nodes']

    #print(nodes)

    total_consumption = 0
    total_vat = 0
    total_cost = 0

    with open(file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Periode', 'Forbruk (kWt)', 'Pris inkl MVA', 'Pris eks MVA', 'MVA'])

        for node in nodes:
            f = get_date(node['from'].split('.')[0])
            t = get_date(node['to'].split('.')[0])

            if f < start:
                print(f'Early node skipped: {node}')
            elif t > end:
                print(f'Late node skipped: {node}')
            else:
                consumption = node['consumption']
                if consumption == None:
                    consumption = 0

                cost = node['cost']
                if cost == None:
                    cost = 0

                vat = node['unitPriceVAT'] * consumption

                writer.writerow([f'{f} - {t}', trunc(consumption), trunc(cost + vat), trunc(cost), trunc(vat)])

                total_consumption += consumption
                total_cost += cost
                total_vat += vat

        writer.writerow(['', '', '', '', ''])
        writer.writerow([f'{start} - {end}', trunc(total_consumption), trunc(total_cost + total_vat), trunc(total_cost), trunc(total_vat)])


if __name__ == '__main__':
    main()


