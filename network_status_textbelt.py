# External Imports
import datetime
import functools
import os
import ping3
import requests
import signal
import sys
import time

ping3.EXCEPTIONS = True

# From Imports
from dotenv import load_dotenv
from pydantic import ValidationError
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import HTTPError
from textbelt_py import SMSRequest, TextbeltClient, TextbeltException

class GracefulKiller:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self, signum, frame):
    self.kill_now = True

def textbelt_send(textbelt_client, message):
    print("Prepping to send message: " + message)

    while True:
        # try/except textbelt client methods and handle exceptions accordingly
        try:
            # create request
            sms_request = SMSRequest(phone=os.getenv('textbelt_phone_number'), sender=f'{os.getenv('textbelt_organization_name')}', message=f'{os.getenv('textbelt_organization_name')} - {message}')

            # send text message via textbelt
            sms_response = textbelt_client.send_sms(sms_request)

            # check response
            print("Message sent successfully: " + str(sms_response.success))
        except TextbeltException as err:
            if err.ex_type is HTTPError:
                # handle requests http error
                print(">>> Http error occurred: " + err)
            elif err.ex_type is ValidationError:
                # handle pydantic validation error
                print(">>> Validation error occurred: " + err)
            else:
                # handle all other exceptions
                print(f">>> Exception type {err.ex_type} | Exception: {err.exception} | Message: {err.message}")
            # Using "continue" to retry on exception
            continue
        # Exception didn't process, so we are done looping
        break

def check_env_validity():
    if not os.getenv('successful_timer').isdigit():
        print("successful timer value is not a numeric value. Exiting")
        exit(1)
    if not os.getenv('error_timer').isdigit():
        print("error timer value is not a numeric value. Exiting")
        exit(1)

def successful_timer():
    for i in range (1, int(os.getenv('successful_timer'))):
        if killer.kill_now:
            sys.exit();
        time.sleep(1)

def error_timer():
    for i in range (1, int(os.getenv('error_timer'))):
        if killer.kill_now:
            sys.exit();
        time.sleep(1)

if __name__ == '__main__':

    # key-value pairs from .env get loaded into the os environment
    load_dotenv()
    check_env_validity()

    # setup Requests Session for use with the Textbelt Client
    retry = Retry(total=3, backoff_factor=1)
    retry_adapter = HTTPAdapter(max_retries=retry)
    requests_session = requests.Session()
    requests_session.mount("http://", retry_adapter)
    requests_session.mount("https://", retry_adapter)
    requests_session.request = functools.partial(requests_session.request, timeout=5)

    # setup Textbelt Client with api key
    textbelt_client = TextbeltClient(os.getenv('textbelt_api_token'), requests_session)

    # Print remaining credit balance for textbelt account
    print("Remaining Textbelt credit balance: " + str(textbelt_client.check_credit_balance().quota_remaining))

    # initialize GracefulKiller
    killer = GracefulKiller()

    last_connection_state = True # True = up, False = down

    while not killer.kill_now:
        try:
            print(f'{datetime.datetime.now().strftime('%y.%m.%d %H:%M:%S')} - {os.getenv('network_monitor_target')}: {int(ping3.ping(os.getenv('network_monitor_target'), ttl=1, unit="ms"))} ms')
            if last_connection_state == False:
                textbelt_send(textbelt_client,'Network Up')
                last_connection_state = True
            successful_timer()
        except ping3.errors.PingError as err: # Ping failed
            print(f'{datetime.datetime.now().strftime('%Y.%m.%d %H:%M:%S')} - Ping Error: {err}')
            if last_connection_state == True:
                textbelt_send(textbelt_client,'Network Down')
                last_connection_state = False
            error_timer()