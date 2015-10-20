__author__ = 'sadams'

import getpass

class InteractivePrompter(object):

  def get_value(self, prompt_text='', current_value=None, hide=False):
    prompt = '{} [{}]: '.format(prompt_text, current_value)
    if hide:
      response = getpass.getpass(prompt)
    else:
      response = raw_input(prompt)
    if not response:
      response = current_value
    return response


