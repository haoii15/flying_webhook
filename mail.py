import email
import imaplib
from time import sleep
import requests
from bs4 import BeautifulSoup
from envs import *


max_id = None


while True:

    while True:
        try:
            mail = imaplib.IMAP4_SSL(SERVER)
            mail.login(EMAIL, PASSWORD)
            mail.select("inbox")
            status, data = mail.search(None, "FROM", f'"Secret Flying"')
            break
        except:
            sleep(10)
            print("error while loging in")
            continue

    mail_ids = []
    for block in data:
        mail_ids += block.split()

    mails = len(mail_ids)
    if not max_id:
        max_id = len(mail_ids)
        mail.logout()
        sleep(900)
        continue
    elif mails == max_id:
        mail.logout()
        sleep(900)
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

                # Title is now in u_column_6 (the only occurrence) inside an h2
                title_col = soup.find(id="u_column_6")
                title_text = ""
                if title_col:
                    h2 = title_col.find("h2")
                    if h2:
                        title_text = h2.get_text(strip=True)

                # Deal content is now in u_column_5
                wanted_data = soup.find(id="u_column_5")
                if not wanted_data:
                    continue

                with open("mail.html", "w") as f:
                    f.write(wanted_data.prettify())

                ps = wanted_data.find_all("p")
                for p in ps:
                    text = p.get_text(separator="\n", strip=True)
                    if text.startswith("DEPART"):
                        depart = ""
                        cities = text.split("\n")[1:]
                        multicity = True if len(cities) > 1 else False
                        multilist = []
                        for city in cities:
                            if "/" in city:
                                for c in city.split("/"):
                                    multilist.append(c)
                            else:
                                multilist.append(city)
                            depart += city + "\n"
                    if text.startswith("ARRIVE"):
                        arrive = ""
                        for city in text.split("\n")[1:]:
                            arrive += city + "\n"
                    if text.startswith("DATES"):
                        # New format: "DATES:\nAvailability in\nMarch 2027"
                        lines = text.split("\n")
                        # Join everything after "DATES:" as the date_info
                        date_info = " ".join(lines[1:]).strip()
                    if text.startswith("AIRLINES"):
                        airlines = text.split("\n")[1] if len(text.split("\n")) > 1 else ""

                if multicity:
                    resp = requests.get(PEXELSURL + arrive, headers=HEADERS)
                    try:
                        image = resp.json()["photos"][0]["src"]["original"]
                    except:
                        image = DEFAULT_IMAGE
                    item = {
                        "embeds": [
                            {
                                "title": title_text,
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
                            text = p.get_text(separator="\n", strip=True)
                            if text.startswith(city):
                                chops = text.split("\n")
                                date_string = ""
                                date_num = 0
                                for idx, chop in enumerate(chops):
                                    if idx == 0:
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
                    # New format: all deal links share the same href, grab it from "GO TO DEAL"
                    dates = wanted_data.find_all("a")
                    date_num = 0
                    for date in dates:
                        try:
                            if date_num == 10:
                                date_string += "..."
                                break
                            if date.text.strip() == "GO TO DEAL":
                                url = date["href"]
                            if date.text.strip() and date.text.strip()[0] in "1234567890":
                                date_string += date.text.strip() + "\n"
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
                                "title": title_text,
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
                        ],
                    }
                item["content"] = "<@&1285299461785931397>" + (
                    " <@&1285299507642368130>"
                    if "business" in title_text.lower()
                    else ""
                )

                r = requests.post(WEBHOOK, json=item)

    max_id = mails
    mail.logout()
    sleep(900)
