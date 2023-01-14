"""SyncResults class for osxphotos sync command"""

from __future__ import annotations

import datetime
import json

from osxphotos.photoinfo import PhotoInfo

SYNC_PROPERTIES = [
    "albums",
    "description",
    "favorite",
    "keywords",
    "title",
]


class SyncResults:
    """Results of sync set/merge"""

    def __init__(self):
        self._results = {}
        self._datetime = datetime.datetime.now()

    def add_result(
        self,
        uuid: str,
        filename: str,
        fingerprint: str,
        property: str,
        updated: bool,
        before: str | list[str] | bool | None,
        after: str | list[str] | bool | None,
    ):
        """Add result for a single photo"""
        if uuid not in self._results:
            self._results[uuid] = {
                "filename": filename,
                "fingerprint": fingerprint,
                "properties": {
                    property: {
                        "updated": updated,
                        "datetime": datetime.datetime.now().isoformat(),
                        "before": before,
                        "after": after,
                    },
                },
            }
        else:
            self._results[uuid]["properties"][property] = {
                "updated": updated,
                "datetime": datetime.datetime.now().isoformat(),
                "before": before,
                "after": after,
            }

    @property
    def results(self):
        """Return results"""
        return self._results

    @property
    def results_list(self):
        """Return results as list lists where each sublist is values for a single photo"""
        results = []
        for uuid, record in self._results.items():
            row = [
                uuid,
                record["filename"],
                record["fingerprint"],
                self._any_updated(uuid),
            ]
            for property in SYNC_PROPERTIES:
                if property in record["properties"]:
                    row.extend(
                        record["properties"][property][column]
                        for column in ["updated", "datetime", "before", "after"]
                    )
                else:
                    row.extend([False, "", "", ""])
            results.append(row)
        return results

    @property
    def results_header(self):
        """Return headers for results_list"""
        header = ["uuid", "filename", "fingerprint", "updated"]
        for property in SYNC_PROPERTIES:
            header.extend(
                f"{property}_{column}"
                for column in ["updated", "datetime", "before", "after"]
            )
        return header

    @property
    def results_dict(self):
        """Return dictionary of results"""
        results = {}
        for uuid, record in self._results.items():
            results[uuid] = {
                "uuid": uuid,
                "filename": record["filename"],
                "fingerprint": record["fingerprint"],
                "updated": self._any_updated(uuid),
            }
            for property in SYNC_PROPERTIES:
                if property in record["properties"]:
                    results[uuid][property] = record["properties"][property]
                else:
                    results[uuid][property] = {
                        "updated": False,
                        "datetime": None,
                        "before": None,
                        "after": None,
                    }
        return results

    def results_summary(self):
        """Get summary of results"""
        updated = sum(bool(self._any_updated(uuid)) for uuid in self._results.keys())
        property_updated = {}
        for property in SYNC_PROPERTIES:
            property_updated[property] = 0
            for uuid in self._results.keys():
                if self._results[uuid]["properties"].get(property, {"updated": False})[
                    "updated"
                ]:
                    property_updated[property] += 1
        return {
            "total": len(self._results),
            "updated": updated,
        } | property_updated

    def _any_updated(self, uuid: str) -> bool:
        """Return True if any property was updated for this photo"""
        return any(
            self._results[uuid]["properties"].get(property, {"updated": False})[
                "updated"
            ]
            for property in SYNC_PROPERTIES
        )

    def __add__(self, other):
        """Add results from another SyncResults"""
        for uuid in other._results.keys():
            for property, values in other._results[uuid]["properties"].items():
                self.add_result(
                    uuid,
                    other._results[uuid]["filename"],
                    other._results[uuid]["fingerprint"],
                    property,
                    values["updated"],
                    values["before"],
                    values["after"],
                )
        return self

    def __iadd__(self, other):
        """Add results from another SyncResults"""
        for uuid in other._results.keys():
            for property, values in other._results[uuid]["properties"].items():
                self.add_result(
                    uuid,
                    other._results[uuid]["filename"],
                    other._results[uuid]["fingerprint"],
                    property,
                    values["updated"],
                    values["before"],
                    values["after"],
                )
        return self

    def __str__(self):
        return json.dumps(self._results, indent=2)
