import email
import imaplib
from time import sleep
import requests
import requests
from bs4 import BeautifulSoup
from envs import *


max_id = None

mail = imaplib.IMAP4_SSL(SERVER)

while True:
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")
    status, data = mail.search(None, "FROM", '"Secret Flying"')

    mail_ids = []
    for block in data:
        mail_ids += block.split()

    mails = len(mail_ids)
    if not max_id:
        max_id = len(mail_ids)
        sleep(60)
        continue
    elif mails == max_id:
        sleep(60)
        continue

    mail_ids = mail_ids[max_id:]

    for i in mail_ids:
        status, data = mail.fetch(i, "(RFC822)")
        for response_part in data:
            if isinstance(response_part, tuple):
                message = email.message_from_bytes(response_part[1])
                mail_subject = message["subject"]
                if message.is_multipart():
                    mail_content = ""
                    for part in message.get_payload():
                        if part.get_content_type() == "text/html":
                            mail_content += part.get_payload(decode=True).decode()
                else:
                    mail_content = message.get_payload()

                url = ""
                depart = ""
                arrive = ""
                date_info = ""
                date_string = ""
                airlines = ""
                multicity = False

                soup = BeautifulSoup(mail_content, "html.parser")
                results = soup.find_all(id="u_column_6")
                wanted_data = results[1]
                with open("mail.html", "w") as f:
                    f.write(wanted_data.prettify())
                ps = wanted_data.find_all("p")
                for p in ps:
                    if p.text.startswith("DEPART"):
                        depart = ""
                        cities = p.text.split("\n")[1:]
                        multicity = True if len(cities) > 1 else False
                        multilist = []
                        for city in cities:
                            if "/" in city:
                                for c in city.split("/"):
                                    multilist.append(c)
                            else:
                                multilist.append(city)
                            depart += city + "\n"
                    if p.text.startswith("ARRIVE"):
                        arrive = ""
                        for city in p.text.split("\n")[1:]:
                            arrive += city + "\n"
                    if p.text.startswith("DATES"):
                        date_info = p.text.split("\n")[1]
                    if p.text.startswith("AIRLINES"):
                        airlines = p.text.split("\n")[1]

                if multicity:
                    resp = requests.get(PEXELSURL + arrive, headers=HEADERS)
                    try:
                        image = resp.json()["photos"][0]["src"]["original"]
                    except:
                        image = DEFAULT_IMAGE
                    item = {
                        "embeds": [
                            {
                                "title": ps[0].text,
                                "description": date_info,
                                "color": 15844367,
                                "url": url,
                                "image": {"url": image},
                                "fields": [
                                    {
                                        "name": "From",
                                        "value": depart,
                                        "inline": True,
                                    },
                                    {
                                        "name": "To",
                                        "value": arrive,
                                        "inline": True,
                                    },
                                    {
                                        "name": "Airlines",
                                        "value": airlines,
                                        "inline": True,
                                    },
                                ],
                            }
                        ]
                    }

                    for p in ps:
                        for city in multilist:
                            city = city.split(",")[0]
                            if p.text.startswith(city):
                                chops = p.text.split("\n")
                                date_string = ""
                                date_num = 0
                                for i, chop in enumerate(chops):
                                    if i == 0:
                                        title = chop
                                        continue
                                    try:
                                        if chop[0] in "1234567890":
                                            date_string += chop + "\n"
                                            date_num += 1
                                        if date_num == 3:
                                            break
                                    except:
                                        pass
                                item["embeds"][0]["fields"].insert(
                                    len(item["embeds"][0]["fields"]) - 1,
                                    {
                                        "name": title,
                                        "value": date_string,
                                        "inline": True,
                                    },
                                )
                else:
                    dates = wanted_data.find_all("a")
                    date_num = 0
                    for date in dates:
                        try:
                            if date_num == 10:
                                date_string += "..."
                                break
                            if date.text.startswith("GO TO DEAL"):
                                url = date["href"]
                            if date.text[0] in "1234567890":
                                date_string += date.text + "\n"
                                date_num += 1
                        except:
                            pass

                    resp = requests.get(PEXELSURL + arrive, headers=HEADERS)
                    try:
                        image = resp.json()["photos"][0]["src"]["original"]
                    except:
                        image = DEFAULT_IMAGE

                    item = {
                        "embeds": [
                            {
                                "title": ps[0].text,
                                "description": date_info,
                                "color": 15844367,
                                "url": url,
                                "image": {"url": image},
                                "fields": [
                                    {
                                        "name": "From",
                                        "value": depart,
                                        "inline": True,
                                    },
                                    {
                                        "name": "To",
                                        "value": arrive,
                                        "inline": True,
                                    },
                                    {
                                        "name": "Example Dates",
                                        "value": date_string,
                                        "inline": True,
                                    },
                                    {
                                        "name": "Airlines",
                                        "value": airlines,
                                        "inline": True,
                                    },
                                ],
                            }
                        ]
                    }

                r = requests.post(WEBHOOK, json=item)
    max_id = mails
    sleep(60)
