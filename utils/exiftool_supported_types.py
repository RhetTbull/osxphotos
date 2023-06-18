"""Read the "Supported File Types" table from exiftool.org and build a json file from the table"""

import json
import sys

import requests
from bs4 import BeautifulSoup

if __name__ == "__main__":
    url = "https://www.exiftool.org/"
    json_file = "exiftool_filetypes.json"

    html_content = requests.get(url).text

    soup = BeautifulSoup(html_content, "html.parser")

    # uncomment to see all table classes
    # print("Classes of each table:")
    # for table in soup.find_all("table"):
    #     print(table.get("class"))

    # strip footnotes in <span> tags
    for span_tag in soup.findAll("span"):
        span_tag.replace_with("")

    # find the table for Supported File Types
    table = soup.find("table", class_="sticky tight sm bm")

    # get table headers
    table_headers = [tx.text.lower() for tx in table.find_all("th")]

    # get table data
    table_data = []
    for tr in table.find_all("tr"):
        if row := [td.text for td in tr.find_all("td")]:
            table_data.append(row)

    # make a dictionary of the table data
    supported_filetypes = {}
    for row in table_data:
        row_dict = dict(zip(table_headers, row))
        for key, value in row_dict.items():
            if value == "-":
                row_dict[key] = None
        row_dict["file type"] = row_dict["file type"].split(",")
        row_dict["file type"] = [ft.strip() for ft in row_dict["file type"]]
        row_dict["read"] = "R" in row_dict["support"]
        row_dict["write"] = "W" in row_dict["support"]
        row_dict["create"] = "C" in row_dict["support"]
        filetypes = [ft.lower() for ft in row_dict["file type"]]
        for filetype in filetypes:
            supported_filetypes[filetype] = {"extension": filetype, **row_dict}

    with open(json_file, "w") as jsonfile:
        print(f"Writing {json_file}...")
        json.dump(supported_filetypes, jsonfile, indent=4)
