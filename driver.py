import csv
import os.path
import random
import time
from colorama import Fore, Style
from pathlib import Path
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
from undetected_chromedriver import Chrome
from webdriver_manager.chrome import ChromeDriverManager

# Define a timeout for waiting for elements to load
timeout = 12


class Bot:
    """
    Bot class that automates WhatsApp Web interactions using a Chrome driver.
    """
    def __init__(self):
        options = Options()
        profile_dir = Path.cwd() / "chrome-profile"  # profile location, same directory as script
        profile_dir.mkdir(exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        self.driver = Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options,
            headless=False,
            use_subprocess=True
        )
        self._message = None
        self._csv_numbers = None
        self._options = [False, False]  # [include_placeholders, include_media]
        self._start_time = None
        self.__prefix = None

        # NEW: For failure callback
        self.on_send_failure = None
        self._current_name = None
        self._current_number = None

        # Selectors may change in time
        self.__login_selector = "//div[@class='x1c4vz4f xs83m0k xdl72j9 x1g77sc7 x78zum5 xozqiw3 x1oa3qoh x12fk4p8 xeuugli x2lwn1j x1nhvcw1 xdt5ytf x1cy8zhl xh8yej3 x5yr21d']"
        self.__button_selector = "//button[@aria-label='Send']"
        self.__main_selector = (
            "//div[contains(@class,'lexical-rich-text-input')]"
            "//div[@role='textbox' and @contenteditable='true'"
            " and @data-lexical-editor='true'"
            " and @tabindex='10' and @data-tab='10'"
            " and @aria-owns='emoji-suggestion'"
            " and not(ancestor::*[@aria-hidden='true'])]"
        )
        self.__fallback_selector = (
            "//div[contains(@class,'lexical-rich-text-input')]"
            "//div[@role='textbox' and @contenteditable='true'"
            " and (@aria-label='Type a message' or @aria-placeholder='Type a message')"
            " and not(ancestor::*[@aria-hidden='true'])]"
        )
        self.__media_selector = "//div[@class='x1hx0egp x6ikm8r x1odjw0f x1k6rcq7 x1lkfr7t']//p[@class='selectable-text copyable-text x15bjb6t x1n2onr6']"
        self.__button_selector_media = "//div[@role='button' and @aria-label='Send']//span[@data-icon='wds-ic-send-filled']"

    def click_button(self, selector):
        """Clicks the send button (specified by its CSS selector)."""
        button = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, selector))
        )
        button.click()

    def construct_whatsapp_url(self, number):
        """Constructs the WhatsApp Web URL for opening a chat with a contact."""
        return f'https://web.whatsapp.com/send?phone={self.__prefix}{number.strip()}&type=phone_number&app_absent=0'

    def login(self, prefix):
        """Logs in to WhatsApp Web and starts sending messages."""
        self.__prefix = prefix
        logged_in = False
        page_load = False
        while not logged_in:
            try:
                if not page_load:
                    self.driver.get('https://web.whatsapp.com')
                print("\033[96m Preparing WhatsApp Web... \033[0m")
                print("\033[92m▰▰▰▰▰ Loading... ▰▰▰▰▰\033[0m")
                try:
                    WebDriverWait(self.driver, timeout).until(
                        EC.visibility_of_element_located((By.XPATH, self.__login_selector))
                    )
                    print(Fore.GREEN + "Logged in successfully!" + Style.RESET_ALL)
                    logged_in = True
                except TimeoutException:
                    print(Fore.RED + "Waiting for QR code to be scanned..." + Style.RESET_ALL)
                if logged_in:
                    break
            except Exception as e:
                page_load = True
                print(f"Error during login: {e}")
                print("Retrying login...")
            time.sleep(5)

        self._start_time = time.strftime("%d-%m-%Y_%H%M%S", time.localtime())
        self.send_messages_to_all_contacts()

    def log_result(self, number, error):
        """Logs the result of each message send attempt."""
        assert self._start_time is not None
        log_path = "logs/" + self._start_time + ("_notsent.txt" if error else "_sent.txt")
        Path("logs").mkdir(exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as logfile:
            logfile.write(number.strip() + "\n")

    def prepare_message(self, row):
        """Prepares the message, replacing placeholders like %NAME%, %EMPLOYEE_ID%, %DATE%."""
        message = self._message
        name = row[0] if len(row) > 0 else ""
        employee_id = row[2] if len(row) > 2 else ""
        date = row[3] if len(row) > 3 else ""

        if self._options[0]:
            if name:
                message = message.replace("%NAME%", name)
            if employee_id:
                message = message.replace("%EMPLOYEE_ID%", employee_id)
        if date:
            message = message.replace("%DATE%", date)

        return message

    def quit_driver(self):
        """Closes the WebDriver session and quits the browser."""
        if self.driver:
            self.driver.quit()
            print(Fore.YELLOW + "Driver closed successfully." + Style.RESET_ALL)

    def type_message(self, text_element, message):
        """Types the message into the appropriate text element."""
        multiline = "\n" in message
        if multiline:
            for line in message.split("\n"):
                text_element.send_keys(line)
                text_element.send_keys(Keys.LEFT_SHIFT + Keys.RETURN)
        else:
            text_element.send_keys(message)

    def send_message_to_contact(self, url, message):
        """Sends a message or media via WhatsApp Web."""
        try:
            self.driver.get(url)
            try:
                message_box = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, self.__main_selector))
                )
            except:
                message_box = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, self.__fallback_selector))
                )

            if self._options[1]:
                message_box.send_keys(Keys.CONTROL, 'v')
                sleep(random.uniform(2, 5))
                message_box = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, self.__media_selector))
                )
                self.__button_selector = self.__button_selector_media

            self.type_message(message_box, message)
            delay = random.uniform(2, 3)
            print(f"Sending in {delay:.2f} seconds...")
            try:
                self.click_button(self.__button_selector)
            except Exception:
                message_box.click()
                message_box.send_keys(Keys.ENTER)
            sleep(delay)
            print(Fore.GREEN + "Message sent successfully." + Style.RESET_ALL)
            return False
        except Exception as e:
            reason = "Unknown error"
            error_str = str(e).lower()
            if "timeout" in error_str:
                reason = "Timeout - User not on WhatsApp"
            elif "not found" in error_str or "no such element" in error_str:
                reason = "User not on WhatsApp"
            elif "invalid" in error_str:
                reason = "Invalid number"
            else:
                reason = str(e)[:50]

            print(Fore.RED + f"Failed: {reason}" + Style.RESET_ALL)

            # CALL FAILURE CALLBACK
            if self.on_send_failure and self._current_name and self._current_number:
                self.on_send_failure(self._current_name, self._current_number, reason)

            return True

    def send_messages_to_all_contacts(self):
        """Sends messages to all contacts listed in the provided CSV file."""
        if not os.path.isfile(self._csv_numbers):
            print(Fore.RED + "CSV file not found!" + Style.RESET_ALL)
            return
        try:
            with open(self._csv_numbers, mode="r", encoding="utf-8") as file:
                csv_reader = csv.reader(file)
                for row in csv_reader:
                    if len(row) < 2:
                        continue
                    name = row[0].strip()
                    number = row[1].strip()

                    # SET CONTEXT FOR CALLBACK
                    self._current_name = name
                    self._current_number = number

                    print(f"Sending to: {name} | {number}")
                    message = self.prepare_message(row)
                    url = self.construct_whatsapp_url(number)
                    error = self.send_message_to_contact(url, message)
                    self.log_result(number, error)
                    sleep(random.uniform(5, 10))  # Anti-ban delay
        finally:
            self.quit_driver()

    def wait_for_element_to_be_clickable(self, xpath, success_message=None, error_message=None, timeout=timeout):
        """Waits for an element to be clickable."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            if success_message:
                print(Fore.GREEN + success_message + Style.RESET_ALL)
            return True
        except TimeoutException:
            if error_message:
                print(Fore.RED + error_message + Style.RESET_ALL)
            return False

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, txt_file):
        with open(txt_file, "r", encoding="utf-8") as file:
            self._message = file.read()

    @property
    def csv_numbers(self):
        return self._csv_numbers

    @csv_numbers.setter
    def csv_numbers(self, csv_file):
        self._csv_numbers = csv_file

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, opt):
        self._options = opt
