import sys
import argparse
import requests
import urllib3
import time
import getpass
import keyring

from panopto_oauth2 import PanoptoOAuth2


panopto_server = "cornell.hosted.panopto.com"

panopto_clientid = getpass.getpass("Enter panopto client id :\n")
keyring.set_password("panopto_clientid", "panopto", panopto_clientid)

panopto_clientsecret = getpass.getpass("Enter panopto client secret:\n")
keyring.set_password("panopto_clientsecret", "panopto", panopto_clientsecret)


panopto_clientid = keyring.get_password("panopto_clientid", "panopto")
panopto_clientsecret = keyring.get_password("panopto_clientsecret", "panopto")


oauth2 = PanoptoOAuth2(panopto_server, panopto_clientid, panopto_clientsecret, False)


def authorization(requests_session, oauth2):
    # Go through authorization
    access_token = oauth2.get_access_token_authorization_code_grant()
    # Set the token as the header of requests
    requests_session.headers.update({'Authorization': 'Bearer ' + access_token})

requests_session = requests.Session()
requests_session.verify = False

authorization(requests_session, oauth2)


folder_id = '00000000-0000-0000-0000-000000000000' # represent top level folder
url = 'https://{0}/Panopto/api/v1/folders/{1}/children'.format(panopto_server, folder_id)
resp = requests_session.get(url = url)
if response.status_code // 100 != 2:
    print("shit")

data = resp.json() # parse JSON format response
for folder in data['Results']:
    print('  {0}: {1}'.format(folder['Id'], folder['Name']))



url = 'https://{0}/Panopto/api/v1/folders/{1}/sessions'.format(panopto_server, "51829b83-654f-4228-a1e2-abba00eb4664")
resp = requests_session.get(url = url)


url = 'https://{0}/Panopto/api/v1/sessions/{1}'.format(panopto_server, 'c1f581bf-66ce-4142-b5a7-ac16000867ce')
resp = requests_session.get(url = url)


