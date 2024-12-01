import csv
import json
import logging
from venv import logger

import requests
from pydantic import BaseModel, Field
from typing import List, Any, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Activity(BaseModel):
    """ "activity": {
        "key": "bicycle-dh",
        "value": "DH",
        "lookupId": "21"
    },
    """

    key: str
    value: str


class TrailItem(BaseModel):
    """Represents a trail item with only the 'id' field."""

    id: str = Field(..., description="The unique identifier for the trail.")
    objectClass: str
    content: Any
    properties: Any
    networkId: str

    @property
    def network_id(self) -> str:
        return self.networkId

    @property
    def activity(self) -> Dict[str, Any]:
        logger.debug("activity: running")
        if self.content:
            return self.content.get("activity", {})
        else:
            raise ValueError("no self.content")

    @property
    def activity_key(self):
        logger.debug("activity_key: running")
        if self.activity:
            return self.activity.get("key", "")
        else:
            return ""

    @property
    def has_running_activity(self) -> bool:
        if "running" in self.activity_key:
            return True
        return False

    @property
    def has_riding_activity(self) -> bool:
        if "riding" in self.activity_key:
            return True
        return False

    @property
    def has_hike_activity(self) -> bool:
        if "hiking" in self.activity_key:
            return True
        return False

    @property
    def has_bike_activity(self) -> bool:
        if "bicycle" or "gravel" in self.activity_key:
            return True
        return False

    @property
    def is_multitrail(self) -> bool:
        return self.properties["isMultiTrail"]

    @property
    def url(self):
        return f"https://www.aretrails.com/trail/{self.id}"

    @property
    def title(self):
        return self.content["title"]

    @property
    def length(self):
        if self.properties["trailDistanceMeter"]:
            return int(float(self.properties["trailDistanceMeter"]))
        else:
            return 0

    @property
    def length_in_km(self):
        if self.properties["trailDistanceMeter"]:
            return round(float(self.properties["trailDistanceMeter"]) / 1000, 1)
        else:
            return 0

    @property
    def number(self) -> str:
        return self.properties.get("trailNumber", "")

    @property
    def class_(self):
        return self.objectClass

    @property
    def gpx_url(self):
        return f"https://func-gaiaplaces-aretrails.azurewebsites.net/api/ContentItem/geo/{self.id}/gpx?networkId={self.network_id}&draft=0&code="


class AreTrailsData(BaseModel):
    """Represents the AreTrails API response."""

    # language: str
    items: List[TrailItem] = []
    data: Any = None  # Raw JSON data storage (optional, for additional use cases)

    def fetch_aretrails_json(self) -> None:
        url = "https://func-gaiaplaces-aretrails.azurewebsites.net/api/ContentItem/cms"
        params = {
            "networkId": "2472c3e3-97f3-4ba2-88bc-f854cd2d98ee",
            "lang": "sv_se",
            "draft": "0",
            "code": "BUSCKN5Xo/OT8C6BQEI8bniVuMODzyvq2WHS7L1aoqPcxDJLcYYuIA==",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Authorization": "Bearer undefined",
            "userId": "portal",
            "Origin": "https://www.aretrails.com",
            "DNT": "1",
            "Connection": "keep-alive",
            "Referer": "https://www.aretrails.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an error for bad HTTP responses
        json_data = response.json()
        self.data = json_data
        # self.language = json_data["language"]

    def parse_items(self):
        self.items = [TrailItem(**item) for item in self.data["items"]]

    def save_json_to_disk(self, filename: str = "aretrails.json"):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.dict(), indent=4, ensure_ascii=False))
        print(f"JSON saved successfully to '{filename}'.")

    @property
    def trails(self):
        return [item for item in self.items if item.class_ == "trail"]

    @property
    def multitrails(self):
        return [
            item for item in self.items if item.class_ == "trail" and item.is_multitrail
        ]

    @property
    def riding_trails(self):
        return [
            item
            for item in self.items
            if item.class_ == "trail" and item.has_riding_activity
        ]

    @property
    def bicycle_trails(self):
        return [
            item
            for item in self.items
            if item.class_ == "trail" and item.has_bike_activity
        ]

    @property
    def hiking_trails(self):
        return [
            item
            for item in self.items
            if item.class_ == "trail" and item.has_hike_activity
        ]

    @property
    def running_trails(self):
        return [
            item
            for item in self.items
            if item.class_ == "trail" and item.has_running_activity
        ]

    @property
    def trails_with_activity(self):
        return [
            item
            for item in self.items
            if item.class_ == "trail" and item.activity != {}
        ]

    @property
    def trails_without_activity(self):
        return [
            item
            for item in self.items
            if item.class_ == "trail" and item.activity == {}
        ]

    @property
    def trails_with_unsupported_activity(self):
        return [
            item
            for item in self.items
            if item.class_ == "trail"
            and not (
                item.has_hike_activity
                or item.has_riding_activity
                or item.has_bike_activity
                or item.has_running_activity
            )
        ]

    def export_trails_to_csv(self, filename: str = "trails.csv"):
        """Export trail items to a CSV file with specified columns."""
        with open(filename, mode="w", encoding="utf-8", newline="") as csvfile:
            fieldnames = ["title", "number", "activity_key", "multitrail", "length", "url", "gpx"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for trail in self.trails:
                writer.writerow({
                    "title": trail.title,
                    "number": trail.number,
                    "activity_key": trail.activity_key,
                    "multitrail": trail.is_multitrail,
                    "length": trail.length,
                    "url": trail.url,
                    "gpx": trail.gpx_url
                })
        print(f"Trail items exported successfully to '{filename}'.")


if __name__ == "__main__":
    try:
        atd = AreTrailsData(language="", items=[])
        atd.fetch_aretrails_json()
        atd.parse_items()
        # atd.save_json_to_disk()
        print(f"number of Trail items: {len(atd.trails)}")
        print(f"number of multitrail items: {len(atd.multitrails)}")
        print(f"number of hiking trail items: {len(atd.hiking_trails)}")
        print(f"number of bicycle trail items: {len(atd.bicycle_trails)}")
        print(f"number of riding trail items: {len(atd.riding_trails)}")
        print(f"number of running trail items: {len(atd.running_trails)}")
        print(
            f"number of trail items without activity: {len(atd.trails_without_activity)}"
        )
        print(f"number of trail items with activity: {len(atd.trails_with_activity)}")
        print(
            f"number of trail items with unsupported activity: {len(atd.trails_with_unsupported_activity)}"
        )
        atd.export_trails_to_csv()
        # first trail
        # print(repr(atd.items[0]))
        # for item in atd.trails_with_unsupported_activity:
        #     print(item.title)
        #     print(item.url)
        #     # print(f"bicycle: {item.has_bike_activity}")
        #     # print(f"hiking: {item.has_hike_activity}")
        #     # print(f"riding: {item.has_riding_activity}")
        #     print(item.activity_key)
        #     exit()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
