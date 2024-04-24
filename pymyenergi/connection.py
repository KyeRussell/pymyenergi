#  SPDX-License-Identifier: Apache-2.0
"""
Python Package for connecting to myenergi API.

"""

import logging
import sys

import httpx
from pycognito import Cognito

from .exceptions import MyenergiError, MyenergiTimeoutError, WrongCredentialsError

_LOGGER = logging.getLogger(__name__)
_USER_POOL_ID = "eu-west-2_E57cCJB20"
_CLIENT_ID = "2fup0dhufn5vurmprjkj599041"


class Connection:
    """Connection to myenergi API."""

    def __init__(
        self,
        username: str = None,
        password: str = None,
        app_password: str = None,
        app_email: str = None,
        timeout: int = 20,
    ) -> None:
        """Initialize connection object."""
        self.timeout = timeout
        self.director_url = "https://director.myenergi.net"
        self.base_url = None
        self.oauth_base_url = "https://myaccount.myenergi.com"
        self.username = username
        self.password = password
        self.app_password = app_password
        self.app_email = app_email
        self.auth = httpx.DigestAuth(self.username, self.password)
        self.headers = {"User-Agent": "Wget/1.14 (linux-gnu)"}
        if self.app_email and app_password:
            self.oauth = Cognito(_USER_POOL_ID, _CLIENT_ID, username=self.app_email)
            self.oauth.authenticate(password=self.app_password)
            self.oauth_headers = {"Authorization": f"Bearer {self.oauth.access_token}"}
        self.do_query_asn = True
        self.invitation_id = ""
        _LOGGER.debug("New connection created")

    def _check_myenergi_server_url(self, response_header):
        if "X_MYENERGI-asn" in response_header:
            new_url = "https://" + response_header["X_MYENERGI-asn"]
            if new_url != self.base_url:
                _LOGGER.info("Updated myenergi active server to %s", new_url)
            self.base_url = new_url
        else:
            _LOGGER.debug("Myenergi ASN not found in Myenergi header, assume auth failure (bad username)")
            raise WrongCredentialsError

    async def discover_locations(self):
        locs = await self.get("/api/Location", oauth=True)
        # check if guest location - use the first location by default
        if locs["content"][0]["isGuestLocation"] is True:
            self.invitation_id = locs["content"][0]["invitationData"]["invitationId"]

    def check_and_update_token(self):
        # check if we have oauth credentials
        if self.app_email and self.app_password:
            # check if we have to renew out token
            self.oauth.check_token()
            self.oauth_headers = {"Authorization": f"Bearer {self.oauth.access_token}"}

    async def send(self, method, url, json=None, oauth=False):
        # Use OAuth for myaccount.myenergi.com
        if oauth:
            # check if we have oauth credentials
            if self.app_email and self.app_password:
                async with httpx.AsyncClient(headers=self.oauth_headers, timeout=self.timeout) as httpclient:
                    the_url = self.oauth_base_url + url
                    # if we have an invitiation id, we need to add that to the query
                    if self.invitation_id != "":
                        if "?" in the_url:
                            the_url = the_url + "&invitationId=" + self.invitation_id
                        else:
                            the_url = the_url + "?invitationId=" + self.invitation_id
                    try:
                        _LOGGER.debug("%s %s %s", method, url, the_url)
                        response = await httpclient.request(method, the_url, json=json)
                    except httpx.ReadTimeout as e:
                        raise MyenergiTimeoutError from e
                    else:
                        _LOGGER.debug("%s status %s", method, response.status_code)
                        if response.status_code == 200:
                            return response.json()
                        elif response.status_code == 401:
                            raise WrongCredentialsError
                        raise MyenergiError(response.status_code)
            else:
                _LOGGER.error("Trying to use OAuth without app credentials")

        # Use Digest Auth for director.myenergi.net and s18.myenergi.net
        else:
            # If base URL has not been set, make a request to director to fetch it
            async with httpx.AsyncClient(auth=self.auth, headers=self.headers, timeout=self.timeout) as httpclient:
                if self.base_url is None or self.do_query_asn:
                    _LOGGER.debug("Get Myenergi base url from director")
                    try:
                        director_url = self.director_url + "/cgi-jstatus-E"
                        response = await httpclient.get(director_url)
                    except Exception:
                        _LOGGER.error("Myenergi server request problem")
                        _LOGGER.debug(sys.exc_info()[0])
                    else:
                        self.do_query_asn = False
                        self._check_myenergi_server_url(response.headers)
                the_url = self.base_url + url
                try:
                    _LOGGER.debug("%s %s %s", method, url, the_url)
                    response = await httpclient.request(method, the_url, json=json)
                except httpx.ReadTimeout as e:
                    # Make sure to query for ASN next request, might be a server problem
                    self.do_query_asn = True
                    raise MyenergiTimeoutError from e
                else:
                    _LOGGER.debug("GET status %s", response.status_code)
                    self._check_myenergi_server_url(response.headers)
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 401:
                        raise WrongCredentialsError
                    # Make sure to query for ASN next request, might be a server problem
                    self.do_query_asn = True
                    raise MyenergiError(response.status_code)

    async def get(self, url, data=None, oauth=False):
        return await self.send("GET", url, data, oauth)

    async def post(self, url, data=None, oauth=False):
        return await self.send("POST", url, data, oauth)

    async def put(self, url, data=None, oauth=False):
        return await self.send("PUT", url, data, oauth)

    async def delete(self, url, data=None, oauth=False):
        return await self.send("DELETE", url, data, oauth)
