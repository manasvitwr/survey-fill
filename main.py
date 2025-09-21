#!/usr/bin/env python3

import logging
import multiprocessing
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright, Page, Browser
from typing import Optional, List, Dict


SAMPLE_FIRST_NAMES = [
    "Aarav", "Aditya", "Arjun", "Arnav", "Aryan", "Ashwin", "Ayush", "Chirag", "Deepak", "Dev",
    "Dhruv", "Gaurav", "Harsh", "Jatin", "Karan", "Krishna", "Lakshay", "Madhav", "Naveen", "Om",
    "Pranav", "Rahul", "Rajesh", "Sanjay", "Tarun", "Udayan", "Varun", "Yash", "Zubin",
    "Aanya", "Aditi", "Anjali", "Bhavya", "Chitra", "Deepika", "Esha", "Fatima", "Geeta", "Hema",
    "Indira", "Jaya", "Kavita", "Lakshmi", "Meera", "Neha", "Ojaswini", "Priya", "Rani", "Sangeeta",
    "Tanvi", "Uma", "Vidya", "Yamini", "Zara"
]

SAMPLE_LAST_NAMES = [
    "Agarwal", "Ahuja", "Bansal", "Chauhan", "Desai", "Gandhi", "Gupta", "Iyer", "Jain", "Kapoor",
    "Kumar", "Malhotra", "Mehta", "Nair", "Patel", "Rao", "Sharma", "Singh", "Tiwari", "Verma",
    "Yadav", "Zaveri"
]

class FormFiller:
    def __init__(self, form_url: str, submission_count: int, names: List[str], start_name_index: int = 0):
        self.form_url = form_url
        self.submission_count = submission_count
        self.successful_submissions = 0
        self.failed_submissions = 0
        self.names = names
        self.current_name_index = start_name_index
        self.setup_browser()

    def setup_browser(self):
        """Initialize Playwright browser with appropriate options."""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage']
            )
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = self.context.new_page()
            
            self.page.set_default_timeout(30000)
        except Exception as e:
            logging.error(f"Error setting up browser: {str(e)}")
            raise

    def wait_for_form_load(self):
        """Wait for the Google Form to load completely."""
        try:
            
            self.page.wait_for_load_state("networkidle", timeout=30000)
            
         
            form_selectors = [
                ".freebirdFormviewerViewFormCard",
                ".freebirdFormviewerViewCenteredContent",
                ".freebirdFormviewerViewFormContent",
                "form.freebirdFormviewerViewFormForm"
            ]
            
            form_found = False
            for selector in form_selectors:
                try:
                    element = self.page.wait_for_selector(selector, timeout=5000, state="visible")
                    if element:
                        form_found = True
                        logging.info(f"Found form using selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not form_found:
                # If no form container found, look for visible question elements
                visible_element_selector = "div[role='listitem']:visible, .freebirdFormviewerComponentsQuestionBaseRoot:visible"
                self.page.wait_for_selector(visible_element_selector, timeout=30000, state="visible")
                logging.info("Found visible form elements")
            
            # Wait a bit for all elements to be fully loaded
            time.sleep(2)
            logging.info("Form loaded successfully")
        except Exception as e:
            logging.error(f"Error waiting for form to load: {str(e)}")
            raise

    def get_question_text(self, question) -> str:
        """Extract the question text from a form element."""
        try:
            # Try different selectors for question text
            selectors = [
                "div[role='heading']",
                ".freebirdFormviewerComponentsQuestionBaseTitle",
                ".freebirdFormviewerViewItemsItemItemTitle",
                "span[class*='Title']"
            ]
            
            for selector in selectors:
                element = question.locator(selector).first
                if element:
                    text = element.inner_text().strip()
                    if text:
                        return text
            
            return "Unknown Question"
        except Exception as e:
            logging.debug(f"Error getting question text: {str(e)}")
            return "Unknown Question"

    def identify_question_type(self, question) -> str:
        """Identify the type of question based on its elements."""
        try:
            # Check for multiple choice (radio buttons)
            radio_count = question.query_selector_all("div[role='radio']")
            if radio_count:
                return "multiple_choice"
            
            # Check for checkboxes
            checkbox_count = question.query_selector_all("div[role='checkbox']")
            if checkbox_count:
                return "checkbox"
            
            # Check for text input
            text_input = question.query_selector("input[type='text']")
            if text_input:
                return "short_answer"
            
            # Check for textarea
            textarea = question.query_selector("textarea")
            if textarea:
                return "paragraph"
            
            return "unknown"
        except Exception as e:
            logging.debug(f"Error identifying question type: {str(e)}")
            return "unknown"

    def get_next_name(self) -> str:
        """Get the next name from the list."""
        if not self.names:
            return f"{random.choice(SAMPLE_FIRST_NAMES)} {random.choice(SAMPLE_LAST_NAMES)}"
        
        name = self.names[self.current_name_index]
        self.current_name_index = (self.current_name_index + 1) % len(self.names)
        return name

    def get_random_response(self, question_type: str) -> str:
        """Generate a random response based on question type."""
        if question_type == "short_answer":
            responses = [
                "Yes", "No", "Maybe", "Sometimes", "Often", "Rarely",
                "Good", "Bad", "Excellent", "Fair", "Poor", "Average",
                "High", "Low", "Medium", "Fast", "Slow", "Normal",
                "Happy", "Sad", "Excited", "Bored", "Tired", "Energetic",
                "Hot", "Cold", "Warm", "Cool", "Dry", "Wet"
            ]
            return random.choice(responses)
        elif question_type == "paragraph":
            responses = [
                "This is a detailed response that provides comprehensive information about the topic.",
                "Based on my experience and knowledge, I believe this is the best approach.",
                "The situation requires careful consideration of multiple factors and perspectives.",
                "I have thoroughly analyzed the options and reached this conclusion.",
                "This solution takes into account various aspects and potential outcomes.",
                "After careful evaluation, I recommend this particular approach.",
                "The data suggests that this is the most effective solution.",
                "Based on current trends and patterns, this seems to be the optimal choice.",
                "This approach aligns well with established best practices.",
                "The evidence supports this particular course of action."
            ]
            return random.choice(responses)
        return ""

    def fill_form(self) -> bool:
        """Fill a single form with responses."""
        try:
            # Navigate to the form with increased timeout
            self.page.goto(self.form_url, wait_until="networkidle", timeout=60000)
            self.wait_for_form_load()

            # Get the name for this submission
            current_name = self.get_next_name()
            logging.info(f"Using name for this submission: {current_name}")

            # Try to find questions using Google Forms specific structure
            questions = []
            question_selectors = [
                "div[role='listitem']",
                ".freebirdFormviewerComponentsQuestionBaseRoot",
                ".freebirdFormviewerViewItemsItemItem"
            ]

            for selector in question_selectors:
                try:
                    found_questions = self.page.query_selector_all(selector)
                    if found_questions and len(found_questions) > 0:
                        questions = found_questions
                        logging.info(f"Found {len(questions)} questions using selector: {selector}")
                        break
                except Exception as e:
                    logging.debug(f"Selector {selector} failed: {str(e)}")
                    continue

            if not questions:
                logging.error("No questions found on the form")
                return False

            # Process each question
            for i, question in enumerate(questions, 1):
                try:
                    # Make sure question is visible
                    if not question.is_visible():
                        continue

                    # Scroll question into view
                    question.scroll_into_view_if_needed()
                    time.sleep(0.5)  # Small delay for stability

                    question_text = self.get_question_text(question)
                    logging.info(f"Processing question {i}: {question_text}")

                    # For the first question, assume it's the name field
                    if i == 1:
                        input_element = question.query_selector("input[type='text']")
                        if input_element and input_element.is_visible():
                            input_element.fill(current_name)
                            time.sleep(1)
                            continue

                    question_type = self.identify_question_type(question)
                    logging.info(f"Question type: {question_type}")

                    if question_type == "multiple_choice":
                        # Get all radio options
                        options = question.query_selector_all("div[role='radio']")
                        visible_options = [opt for opt in options if opt.is_visible()]
                        
                        if visible_options:
                            # Filter out "Other" options if present
                            filtered_options = [
                                opt for opt in visible_options
                                if opt.get_attribute("data-value") != "__other_option__"
                            ]
                            
                            # Choose a random option
                            chosen_option = random.choice(filtered_options if filtered_options else visible_options)
                            
                            # Make sure the option is in view and clickable
                            chosen_option.scroll_into_view_if_needed()
                            time.sleep(0.5)
                            
                            # Click the option
                            chosen_option.click()
                            time.sleep(1)
                            
                            logging.info(f"Selected option for question {i}")
                        else:
                            logging.warning(f"No visible options found for question {i}")

                    elif question_type in ["short_answer", "paragraph"]:
                        input_element = None
                        if question_type == "short_answer":
                            input_element = question.query_selector("input[type='text']")
                            if not input_element:
                                input_element = question.query_selector("input:not([type='hidden'])")
                        else:
                            input_element = question.query_selector("textarea")

                        if input_element and input_element.is_visible():
                            if "name" not in question_text.lower():
                                response = self.get_random_response(question_type)
                                input_element.fill(response)
                                time.sleep(1)

                    elif question_type == "checkbox":
                        checkboxes = question.query_selector_all("div[role='checkbox']")
                        visible_checkboxes = [cb for cb in checkboxes if cb.is_visible()]
                        if visible_checkboxes:
                            num_to_select = random.randint(1, min(3, len(visible_checkboxes)))
                            selected = random.sample(visible_checkboxes, num_to_select)
                            for checkbox in selected:
                                checkbox.scroll_into_view_if_needed()
                                time.sleep(0.5)
                                checkbox.click()
                                time.sleep(1)

                except Exception as e:
                    logging.error(f"Error processing question {i}: {str(e)}")
                    continue

            # Submit the form
            submit_button = None
            submit_button_selectors = [
                "div[role='button']:has-text('Submit')",
                ".freebirdFormviewerViewNavigationSubmitButton",
                "div[jsname='M2UYVd']"
            ]

            for selector in submit_button_selectors:
                try:
                    button = self.page.query_selector(selector)
                    if button and button.is_visible():
                        submit_button = button
                        logging.info(f"Found submit button using selector: {selector}")
                        break
                except Exception as e:
                    continue

            if submit_button:
                submit_button.scroll_into_view_if_needed()
                submit_button.click()
                time.sleep(3)

                try:
                    # Wait for form submission confirmation
                    success_selectors = [
                        "text=Your response has been recorded",
                        ".freebirdFormviewerViewResponseConfirmationMessage",
                        "**/formResponse*"
                    ]
                    
                    for selector in success_selectors:
                        try:
                            if selector.startswith("**/"):
                                self.page.wait_for_url(selector, timeout=30000)
                            else:
                                self.page.wait_for_selector(selector, timeout=30000)
                            logging.info("Form submitted successfully")
                            return True
                        except Exception:
                            continue
                    
                    return False
                except Exception as e:
                    logging.error(f"Error waiting for submission confirmation: {str(e)}")
                    return False
            else:
                logging.error("Could not find submit button")
                return False

        except Exception as e:
            logging.error(f"Error filling form: {str(e)}")
            return False

    def run(self):
        """Run a single form submission."""
        success = self.fill_form()
        if success:
            self.successful_submissions += 1
        else:
            self.failed_submissions += 1
        self.cleanup()
        return success

    def log_summary(self, duration: float):
        """Log the summary of the form filling process."""
        logging.info(
            f"""
Form submission completed:
- Total submissions attempted: {self.submission_count}
- Successful submissions: {self.successful_submissions}
- Failed submissions: {self.failed_submissions}
- Time taken: {duration:.2f} seconds
- Average rate: {self.successful_submissions / duration:.2f} submissions/second
"""
        )

    def cleanup(self):
        """Clean up resources."""
        try:
            self.context.close()
            self.browser.close()
            self.playwright.stop()
        except Exception as e:
            logging.error(f"Error during cleanup: {str(e)}")


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def submission_worker(form_url: str, names: List[str], start_name_index: int) -> bool:
    """Worker function for handling a single form submission in a separate thread."""
    try:
        form_filler = FormFiller(form_url, submission_count=1, names=names, start_name_index=start_name_index)
        return form_filler.run()
    except Exception as e:
        logging.error(f"Worker thread error: {str(e)}")
        return False


def run_threaded_submissions(
    form_url: str, submission_count: int, names: List[str], max_workers: int = None
):
    """Run form submissions using multiple threads."""
    successful_submissions = 0
    failed_submissions = 0
    start_time = time.time()

    # Use CPU count for optimal number of workers
    cpu_count = multiprocessing.cpu_count()
    usable_cpu_count = max(cpu_count // 2, 1)  # Use only half of the available cores
    if max_workers is None:
        max_workers = min(usable_cpu_count, submission_count)

    logging.info(
        f"Starting {submission_count} threaded submissions with {max_workers} workers "
        f"(System has {cpu_count} CPU cores)"
    )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks and store futures
        futures = [
            executor.submit(submission_worker, form_url, names, i % len(names) if names else 0)
            for i in range(submission_count)
        ]

        # Process completed futures as they finish
        for i, future in enumerate(as_completed(futures), 1):
            try:
                if future.result():
                    successful_submissions += 1
                else:
                    failed_submissions += 1

                # Log progress every 5 submissions
                if i % 5 == 0:
                    current_rate = i / (time.time() - start_time)
                    logging.info(
                        f"Completed {i}/{submission_count} submissions. "
                        f"Current rate: {current_rate:.2f}/sec"
                    )

            except Exception as e:
                failed_submissions += 1
                logging.error(f"Future error: {str(e)}")

    # Log final summary
    duration = time.time() - start_time
    logging.info(
        f"""
Thread pool submission completed:
- Total submissions attempted: {submission_count}
- Successful submissions: {successful_submissions}
- Failed submissions: {failed_submissions}
- Time taken: {duration:.2f} seconds
- Average rate: {successful_submissions / duration:.2f} submissions/second
"""
    )


def get_names_from_user() -> List[str]:
    """Get list of names from user input."""
    print("\nEnter names for each submission (one per line). Press Enter twice when done.")
    print("If you don't enter enough names, random Indian names will be used for remaining submissions.")
    names = []
    while True:
        name = input().strip()
        if not name:
            break
        names.append(name)
    return names


def main():
    """Main entry point of the script."""
    setup_logging()

    form_url = input("Enter the Google Form URL: ")
    while True:
        try:
            submission_count = int(input("Enter the number of submissions to make: "))
            if submission_count > 0:
                break
            print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")

    # Get names from user
    print("\nEnter the names to use for submissions:")
    names = get_names_from_user()
    print(f"\nUsing {len(names)} names for submissions")
    if len(names) < submission_count:
        print(f"Will use random Indian names for the remaining {submission_count - len(names)} submissions")

    try:
        run_threaded_submissions(form_url, submission_count, names)
    except KeyboardInterrupt:
        logging.info("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()