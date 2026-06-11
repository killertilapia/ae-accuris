import csv
import json
import logging
from pathlib import Path

import scrapy
from accuris_spider.items import AccurisSpiderItem


class AccurisBSpider(scrapy.Spider):
    name = "accuris_b"
    allowed_domains = ["4donline.ihs.com"]
    alternates_url = "https://4donline.ihs.com/partsapi/search/parts/{id}/alternates"
    target_manufacturers = {"Chemi-Con", "Panasonic", "Rubycon"}
    custom_settings = {
        "FEEDS": {
            "accuris_b_result.csv": {
                "format": "csv",
                "overwrite": True,
            },
        },
        "FEED_EXPORT_FIELDS": [
            "part_number",
            "cross_part_number",
            "cross_manufacturer",
            "cross_type",
            "notes",
        ],
    }

    token_path = Path(__file__).parent.parent / "token.txt"
    bearer_token = token_path.read_text(encoding="utf-8").strip()

    async def start(self):
        csv_path = Path(__file__).with_name("pe-1.csv")

        with csv_path.open("r", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                part_number = row["Part Number"]

                logging.info(f"Processing part number: {part_number}")

                yield scrapy.Request(
                    "https://4donline.ihs.com/partsapi/parts",
                    method="POST",
                    body=json.dumps(self._parts_payload(part_number)),
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self.bearer_token}",
                        "Content-Type": "application/json",
                    },
                    callback=self.parse_parts,
                    meta={"part_number": part_number},
                )

    def parse_parts(self, response):
        part_number = response.meta["part_number"]
        response_json = response.json()

        if response_json:
            part_id = response_json[0].get("id")

            if part_id:
                yield scrapy.Request(
                    self.alternates_url.format(id=part_id),
                    method="POST",
                    body=json.dumps(self._alternates_payload()),
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self.bearer_token}",
                        "Content-Type": "application/json",
                    },
                    callback=self.parse_alternates,
                    meta={"part_number": part_number},
                )
            else:
                yield self._no_match_item(part_number)
        else:
            yield self._no_match_item(part_number)

    def parse_alternates(self, response):
        part_number = response.meta["part_number"]
        response_json = response.json()

        if not response_json:
            yield self._no_match_item(part_number)
            return

        matched_alternates = [
            alternate
            for alternate in response_json
            if alternate.get("MfrShortName") in self.target_manufacturers
        ]

        if not matched_alternates:
            yield self._no_match_item(part_number)
            return

        for alternate in matched_alternates:
            manufacturer = alternate.get("MfrShortName")
            yield AccurisSpiderItem(
                part_number=part_number,
                cross_part_number=alternate.get("PrtNbr", ""),
                cross_manufacturer=manufacturer,
                cross_type=alternate.get("AltType", ""),
                notes="",
            )

    def _parts_payload(self, part_number):
        return {
            "take": 500,
            "skip": 0,
            "count": False,
            "meta": False,
            "request": False,
            "mod": {
                "operator": "equals",
                "searchfields": ["V_STRIPPED_PN"],
                "layout": "3901637792",
                "matchcpl": False,
            },
            "facet": [],
            "keyword": [],
            "state": "",
            "fields": [],
            "orderby": [],
            "q": part_number,
        }

    def _alternates_payload(self):
        return {
            "take": 500,
            "skip": 0,
            "count": False,
            "meta": False,
            "request": False,
            "mod": {"matchcpl": False},
            "facet": [
                {
                    "field": "PrtStatus",
                    "values": ["Active", "Active-Unconfirmed", "NRFND", "EOL"],
                },
                {"field": "AltType", "values": ["F=", "FFF"]},
            ],
            "keyword": [],
            "state": "",
            "fields": ["*"],
            "orderby": [],
            "q": "",
        }

    def _no_match_item(self, part_number):
        return AccurisSpiderItem(
            part_number=part_number,
            cross_part_number="",
            cross_manufacturer="",
            cross_type="",
            notes="No crossmatch",
        )
