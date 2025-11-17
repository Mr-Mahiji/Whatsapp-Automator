from driver import Bot, Fore, Style
import sys
import os
from pathlib import Path
import time

PREFIX = "91"  # The national prefix without the +

class Menu:
    def __init__(self):
        self.bot = None
        self.choices = {
            "1": self.send_message,
            "2": self.send_with_media,
            "3": self.quit,
        }
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)

    def display(self):
        try:
            assert PREFIX and "+" not in PREFIX, "Invalid PREFIX: must be non-empty and without '+'"
            self.clear()
            print(Fore.CYAN + "="*60)
            print(Fore.WHITE + "    WHATSAPP AUTOMATOR")
            print(Fore.YELLOW + f"    Prefix: +{PREFIX}")
            print(Fore.CYAN + "="*60 + Style.RESET_ALL)
            print("""
                1. Send messages
                2. Send messages with media
                3. Quit
            """)
        except AssertionError as e:
            print(Fore.RED + f"ERROR: {e}" + Style.RESET_ALL)
            input("Press ENTER to exit...")
            sys.exit(1)

    def settings(self):
        print(Fore.CYAN + "\n--- Configuration ---" + Style.RESET_ALL)
        txt = self.load_file("txt", "message template")
        csv = self.load_file("csv", "phone numbers list")
        
        include_names = None
        while include_names not in ["y", "n"]:
            include_names = input(Fore.YELLOW + "- Include names in messages? (y/n): " + Style.RESET_ALL).strip().lower()
        include_names = include_names == "y"
        
        return csv, txt, include_names

    def send_message(self):
        print(Fore.GREEN + "\nSEND TEXT MESSAGES" + Style.RESET_ALL)
        csv, txt, include_names = self.settings()
        self.start_bot(csv, txt, include_names, has_media=False)

    def send_with_media(self):
        print(Fore.GREEN + "\nSEND MESSAGES WITH MEDIA" + Style.RESET_ALL)
        print(Fore.YELLOW + "\nINSTRUCTION: Open media file, COPY it (Ctrl+C), then return here." + Style.RESET_ALL)
        input(Fore.MAGENTA + "Press ENTER when media is copied..." + Style.RESET_ALL)
        csv, txt, include_names = self.settings()
        self.start_bot(csv, txt, include_names, has_media=True)

    def start_bot(self, csv, txt, include_names, has_media):
        print(Fore.GREEN + "\nInitializing bot..." + Style.RESET_ALL)
        self.bot = Bot()
        self.bot.csv_numbers = self.data_dir / csv
        self.bot.message = self.data_dir / txt
        self.bot.options = [include_names, has_media]

        failed_numbers = []

        self.bot.on_send_failure = lambda name, number, reason, *_: failed_numbers.append(f"{name},{number},{reason}")

        #self.bot.on_send_failure = on_failure

        print(Fore.YELLOW + "\nStarting WhatsApp Web login..." + Style.RESET_ALL)
        print(Fore.CYAN + "Scan the QR code in WhatsApp Web!" + Style.RESET_ALL)

        try:
            self.bot.login(PREFIX)
            print(Fore.GREEN + "\nSending completed!" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"\nError: {e}" + Style.RESET_ALL)
        finally:
            failed_file = self.data_dir / "failed_numbers.txt"
            if failed_numbers:
                with open(failed_file, "w", encoding="utf-8") as f:
                    f.write("Name,Number,Reason\n")
                    f.write("\n".join(failed_numbers))
                print(Fore.RED + f"\n{len(failed_numbers)} messages failed → saved to: {failed_file.name}" + Style.RESET_ALL)
            else:
                print(Fore.GREEN + "\nAll messages sent successfully!" + Style.RESET_ALL)

            self.show_post_send_menu(failed_file if failed_numbers else None)

    def show_post_send_menu(self, failed_file=None):
        self.clear()
        print(Fore.CYAN + "="*60)
        print(Fore.YELLOW + "  WHAT WOULD YOU LIKE TO DO NEXT?")
        print(Fore.CYAN + "="*60 + Style.RESET_ALL)
        print("    1. Return to Main Menu")
        if failed_file:
            print("    2. Retry Failed Numbers")
        print("    3. Exit")
        print()

        while True:
            choice = input(Fore.WHITE + "> " + Style.RESET_ALL).strip()
            if choice == "1":
                return
            elif choice == "2" and failed_file:
                self.retry_failed_numbers(failed_file)
                return
            elif choice == "3":
                self.quit()
            else:
                print(Fore.RED + "Invalid choice! Try again." + Style.RESET_ALL)
                time.sleep(1)

    def retry_failed_numbers(self, failed_file):
        print(Fore.GREEN + f"\nRetrying failed numbers from: {failed_file.name}" + Style.RESET_ALL)
        input(Fore.YELLOW + "Press ENTER to continue..." + Style.RESET_ALL)

        txt = self.bot.message.name
        include_names = self.bot.options[0]
        has_media = self.bot.options[1]

        self.start_bot(failed_file.name, txt, include_names, has_media)

    def load_file(self, ext, desc):
        files = sorted([f for f in self.data_dir.iterdir() if f.suffix.lower() == f".{ext}"])
        if not files:
            print(Fore.RED + f"No .{ext} files found in 'data/' folder!" + Style.RESET_ALL)
            print(Fore.YELLOW + f"Please add a {desc} file (.{ext}) and try again." + Style.RESET_ALL)
            input("Press ENTER to continue...")
            return self.load_file(ext, desc)

        print(f"\nSelect {desc} file:")
        for i, f in enumerate(files, 1):
            print(f"  {i}) {f.name}")
        
        while True:
            try:
                choice = int(input("> ").strip())
                if 1 <= choice <= len(files):
                    return files[choice-1].name
                else:
                    print(Fore.RED + "Invalid selection!" + Style.RESET_ALL)
            except ValueError:
                print(Fore.RED + "Please enter a number!" + Style.RESET_ALL)

    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def ending_screen(self):
        self.clear()
        print(Fore.CYAN + "=" * 60)
        print(Fore.GREEN + """
          ████╗  ███╗   ███╗ █████╗ ██╗  ███╗ ██╗
          ████║  ████╗ ████║██╔══██╗██║  ███║ ██║
          ████║  ██╔████╔██║███████║████████║ ██║
          ████║  ██║╚██╔╝██║██╔══██║██╔═╗███║ ██║
          ████║  ██║ ╚═╝ ██║██║  ██║██║ ║███║ ██║
          ╚═══╝  ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝ ╚══╝ ╚═╝
        """)
        print(Fore.YELLOW + " THANK YOU FOR USING WHATSAPP AUTOMATOR!")
        print(Fore.CYAN + "=" * 60 + Style.RESET_ALL)
        input(Fore.MAGENTA + "\nPress ENTER to exit..." + Style.RESET_ALL)
        sys.exit(0)

    def quit(self):
        self.ending_screen()

    def run(self):
        while True:
            self.display()
            choice = input(Fore.WHITE + "Enter option (1-3): " + Style.RESET_ALL).strip()
            action = self.choices.get(choice)
            if action:
                action()
            else:
                print(Fore.RED + f"'{choice}' is not a valid option!" + Style.RESET_ALL)
                time.sleep(1)


if __name__ == "__main__":
    m = Menu()
    m.run()
