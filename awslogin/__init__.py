__version__ = '0.1.0'

def awscli_initialize(cli):
  from awslogin.saml import initialize as login_saml
  login_saml(cli)
