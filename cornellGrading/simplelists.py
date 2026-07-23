"""Wrapper class for interacting with the SimpleLists v2 REST API.

Provides authentication against per-list API keys stored in a local JSON
credentials file, plus basic contact operations (retrieve, create, delete)
against SimpleLists mailing lists"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


class simplelists:
    """Class for io methods for the SimpleLists v2 API."""

    def __init__(self, server: str = "https://lists.cornell.edu/api/2/") -> None:
        """Load per-list API keys and validate them against the live API.

        Args:
            server (str):
                Base URL of the SimpleLists API, including trailing slash
                and version path. Defaults to
                'https://lists.cornell.edu/api/2/'.
        """

        self.baseurl = server

        cdir = "simplelists"

        if os.name == "nt":
            config_dir = Path(os.environ["APPDATA"], cdir)
        else:
            config_dir = Path(Path.home(), ".config", cdir)

        credfile = config_dir / "credentials.json"

        assert credfile.exists(), f"Cannot locate credentials file at {credfile}."
        assert os.access(credfile, os.R_OK), (
            f"Credentials file at {credfile} exists but is not readable."
        )

        self.keys: Dict[str, str] = json.loads(credfile.read_text())

        for account, apikey in self.keys.items():
            server_response = requests.get(
                f"{self.baseurl}contacts/", params={"limit": 1}, auth=(apikey, "")
            )
            assert server_response.status_code == 200, (
                f"Could not authenticate SimpleLists API key for '{account}'."
            )

    def _get_api_key(self, list_name: str) -> str:
        """Look up the API key associated with a mailing list name.

        Args:
            list_name (str):
                Name of the list (e.g. 'MAEFIELDFACULTY-L'), matching the
                list-name portion of a '<list_name>-account' key in the
                loaded credentials file.

        Returns:
            str:
                API key for the requested list.
        """

        account = f"{list_name}-account"
        assert account in self.keys, (
            f"No API key found for list '{list_name}' "
            f"(expected key '{account}' in credentials.json)."
        )

        return self.keys[account]

    def get_contacts(self, list_name: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve all contacts belonging to a mailing list.

        Args:
            list_name (str):
                Name of the list to query (e.g. 'MAEFIELDFACULTY-L').
            limit (int):
                Maximum number of records to request per page (SimpleLists
                API allows up to 1000). Defaults to 1000.

        Returns:
            list:
                Raw contact objects (as returned by the API, one dict per
                contact) for every contact on the list.
        """

        apikey = self._get_api_key(list_name)
        url = f"{self.baseurl}contacts/"

        records: List[Dict[str, Any]] = []
        page = 1
        while True:
            server_response = requests.get(
                url,
                params={"list": list_name, "page": page, "limit": limit},
                auth=(apikey, ""),
            )
            assert server_response.status_code == 200, (
                f"Could not retrieve contacts for list '{list_name}' (page {page})."
            )
            payload = server_response.json()
            records.extend(payload["data"])

            if not payload["data"] or page * limit >= payload["count"]:
                break
            page += 1

        return records

    def create_contact(
        self,
        list_name: str,
        email: str,
        firstname: Optional[str] = None,
        surname: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new contact and add them to a mailing list.

        Args:
            list_name (str):
                Name of the list to add the new contact to.
            email (str):
                Primary email address for the new contact.
            firstname (str, optional):
                Contact's first name. Defaults to None (omitted).
            surname (str, optional):
                Contact's surname. Defaults to None (omitted).
            notes (str, optional):
                Free-text notes for the contact. Defaults to None (omitted).

        Returns:
            dict:
                Parsed JSON response describing the created contact.
        """

        apikey = self._get_api_key(list_name)
        url = f"{self.baseurl}contacts/"

        payload: Dict[str, Any] = {
            "emails": email,
            "lists": list_name,
        }
        if firstname is not None:
            payload["firstname"] = firstname
        if surname is not None:
            payload["surname"] = surname
        if notes is not None:
            payload["notes"] = notes

        server_response = requests.post(url, data=payload, auth=(apikey, ""))
        assert server_response.status_code == 200, (
            f"Could not create contact '{email}' on list '{list_name}'."
        )

        return server_response.json()

    def update_contact(
        self,
        list_name: str,
        contact_id: int,
        firstname: Optional[str] = None,
        surname: Optional[str] = None,
        notes: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing contact.

        Args:
            list_name (str):
                Name of the list the API key belongs to (used only to
                resolve the API key; SimpleLists contact ids are global,
                not scoped to a single list).
            contact_id (int):
                SimpleLists internal id of the contact to update.
            firstname (str, optional):
                New first name. Defaults to None (left unchanged).
            surname (str, optional):
                New surname. Defaults to None (left unchanged).
            notes (str, optional):
                New free-text notes. Defaults to None (left unchanged).
            email (str, optional):
                New list of email addresses. Defaults to None (left
                unchanged).

        Returns:
            dict:
                Parsed JSON response describing the updated contact.
        """

        apikey = self._get_api_key(list_name)
        url = f"{self.baseurl}contacts/{contact_id}/"

        payload: Dict[str, Any] = {}
        if firstname is not None:
            payload["firstname"] = firstname
        if surname is not None:
            payload["surname"] = surname
        if notes is not None:
            payload["notes"] = notes
        if email is not None:
            payload["emails"] = email

        assert payload, "At least one contact property must be provided to update."

        server_response = requests.put(url, data=payload, auth=(apikey, ""))
        assert server_response.status_code == 200, (
            f"Could not update contact id {contact_id} (list '{list_name}')."
        )

        return server_response.json()

    def delete_contact(self, list_name: str, contact_id: int) -> bool:
        """Delete a contact from SimpleLists.

        Args:
            list_name (str):
                Name of the list the API key belongs to (used only to
                resolve the API key; SimpleLists contact ids are global,
                not scoped to a single list).
            contact_id (int):
                SimpleLists internal id of the contact to delete.

        Returns:
            bool:
                True if the API reported successful deletion.
        """

        apikey = self._get_api_key(list_name)
        url = f"{self.baseurl}contacts/{contact_id}/"

        server_response = requests.delete(url, auth=(apikey, ""))
        assert server_response.status_code == 200, (
            f"Could not delete contact id {contact_id} (list '{list_name}')."
        )

        return server_response.json().get("success", False)
