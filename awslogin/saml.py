import botocore.session
from botocore.exceptions import ClientError, ProfileNotFound
from awscli.customizations.commands import BasicCommand
from awscli.customizations.configure import ConfigFileWriter
import requests
import base64
import logging
import xml.etree.ElementTree as ET
import re
from bs4 import BeautifulSoup
from urlparse import urlparse
from awslogin.utils import InteractivePrompter
import os

logger = logging.getLogger(__name__)

def initialize(cli):
  cli.register('building-command-table.sts', inject_commands)

def inject_commands(command_table, session, **kwargs):
  command_table['login-with-saml'] = LoginWithSAML(session)

class LoginWithSAML(BasicCommand):
  """
  """
  NAME = 'login-with-saml'
  DESCRIPTION = 'stores temporary credentials by logging into SAML provider'
  SYNOPSIS = ''
  EXAMPLES = ''

  ARG_TABLE = [
   # {'username': 'username', 'required': False, 'help_text': 'specify the username' }
  ]

  UPDATE = False
  QUEUE_SIZE = 10

  def __init__(self, session, prompter=None, config_writer=None):
    super(LoginWithSAML, self).__init__(session)
    if prompter is None:
      prompter = InteractivePrompter()
    self._prompter = prompter
    if config_writer is None:
      config_writer = ConfigFileWriter()
    self._config_writer = config_writer

  def _run_main(self, args, parsed_globals):
    try:
      config = self._session.get_scoped_config()
    except ProfileNotFound:
      config = {}

    saml_url = config.get('saml_url')
    if saml_url is None:
      saml_url = self._prompter.get_value('SAML URL'.format(
        parsed_globals.profile),
        None)

    saml_username = config.get('saml_username')
    new_saml_username = self._prompter.get_value('Username', saml_username)
    saml_password = self._prompter.get_value('Password', None, True)

    if new_saml_username is not None and new_saml_username != saml_username:
      saml_username = new_saml_username

    credentials = self._get_credentials(saml_url, saml_username,
                                        saml_password, parsed_globals.region)
    credentials['saml_url'] = saml_url
    credentials['saml_username'] = saml_username

    self._write_credentials(credentials, parsed_globals.profile)
    return 0

  def _get_credentials(self, saml_url, username, password, region):
    session = requests.Session()
    formresponse = session.get(saml_url, verify=True)
    saml_submit_url = formresponse.url

    formsoup = BeautifulSoup(formresponse.text.decode('utf-8'))
    payload = {}

    for inputtag in formsoup.find_all(re.compile('(INPUT|input)')):
      name = inputtag.get('name', '')
      value = inputtag.get('value', '')
      if 'username' in name.lower():
        payload[name] = username
      elif 'email' in name.lower():
        payload[name] = username
      elif 'password' in name.lower():
        payload[name] = password
      else:
        payload[name] = value

    for inputtag in formsoup.find_all(re.compile('(FORM|form)')):
      action = inputtag.get('action')
      if action:
        parsedurl = urlparse(saml_url)
        saml_submit_url = parsedurl.scheme + '://' + parsedurl.netloc + action

    response = session.post(
      saml_submit_url, params=payload, verify=True)

    del username
    del password

    soup = BeautifulSoup(response.text.decode('utf-8'))
    assertion = None

    for inputtag in soup.find_all('input'):
      if(inputtag.get('name') == 'SAMLResponse'):
        assertion = inputtag.get('value')

    if assertion is None:
      print('Response did not contain a valid SAML assertion!')
      return 1

    awsroles = []
    root = ET.fromstring(base64.b64decode(assertion))
    for saml2attribute in root.iter('{urn:oasis:names:tc:SAML:2.0:assertion}Attribute'):
      if (saml2attribute.get('Name') == 'https://aws.amazon.com/SAML/Attributes/Role'):
        for saml2attributevalue in saml2attribute.iter('{urn:oasis:names:tc:SAML:2.0:assertion}AttributeValue'):
          awsroles.append(saml2attributevalue.text)

    for awsrole in awsroles:
      chunks = awsrole.split(',')
      if'saml-provider' in chunks[0]:
        newawsrole = chunks[1] + ',' + chunks[0]
        index = awsroles.index(awsrole)
        awsroles.insert(index, newawsrole)
        awsroles.remove(awsrole)

    if len(awsroles) > 1:
      i = 0
      print('Please choose the role you would like to assume:')
      for awsrole in awsroles:
        print('[{}]: '.format(awsrole.split(',')[0]))
        i += 1
      selectedroleindex = raw_input()
      print('Selection: {}'.format(selectedroleindex))

      # Basic sanity check of input
      if int(selectedroleindex) > (len(awsroles) - 1):
        print('You selected an invalid role index, please try again')
        return 1

      role_arn = awsroles[int(selectedroleindex)].split(',')[0]
      principal_arn = awsroles[int(selectedroleindex)].split(',')[1]
    else:
      role_arn = awsroles[0].split(',')[0]
      principal_arn = awsroles[0].split(',')[1]

    sts = botocore.session.create_client('sts')
    token = sts.assume_role_with_saml(role_arn, principal_arn, assertion)

    credentials = {}
    credentials['aws_access_key_id'] = token.credentials.access_key
    credentials['aws_secret_access_key'] = token.credentials.secret_key
    credentials['aws_session_token'] = token.credentials.session_token

    return credentials


  def _write_credentials(self, values, profile_name):
    print("writing profile: {}".format(profile_name))
    valid_keys = ['aws_access_key_id', 'aws_secret_access_key',
                   'aws_session_token', 'saml_username', 'saml_url']
    credentials = {}
    for k in valid_keys:
      if k in values:
        v = values.pop(k)
        if v is not None:
          credentials[k] = v

    if credentials:
      if profile_name is not None:
        credentials['__section__'] = profile_name

      credentials_file = os.path.expanduser(
        self._session.get_config_variable('credentials_file'))

      self._config_writer.update_config(
        credentials, credentials_file)