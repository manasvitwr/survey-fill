#!/usr/bin/env python3

import logging
import multiprocessing
import random
import sys
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright, Page, Browser
from typing import Optional, List, Dict

SAMPLE_FIRST_NAMES = [
    "Avinash", "Aditya", "Arjun", "Atharva", "Aryan", "Shubhi", "Ayush", "Chinmay", "Durga", "Dev",
    "Dhruv", "Deepanshu", "Harsh", "Jatin", "Manjot", "Neerja", "Lakshay", "Madhav", "Gauri", "Ananya",
    "Pranav", "Rohan", "Pratham", "Tanaya", "Sneha", "Udayan", "Varun", "Yash", "Kirti",
    "Avandhika", "Aditi", "Anjali", "Bhavya", "Devishi", "Vaishnavi", "Esha", "Vidhur", "Pratham", "Ishita",
    "Indira", "Nishita", "Kavita", "Lakshmi", "Meera", "Neha", "Ojas", "Priyanshu", "Jasmine", "Khushi",
    "Tanvi", "Urvashi", "Anushka", "Yamini", "Sara"
]

SAMPLE_LAST_NAMES = [
    "Agarwal", "Ahuja", "Bansal", "Chauhan", "Desai", "Gandhi", "Gupta", "Iyer", "Jain", "Kapoor",
    "Kumar", "Malhotra", "Mehta", "Nair", "Patel", "Tiwari", "Sharma", "Singh", "Shah", "Verma",
    "Yadav", "Zaveri"
]

SAMPLE_EMAIL_DOMAINS = [ "@gmail.com", "@outlook.com"]
SAMPLE_AGES = list(range(17, 25))

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
            time.sleep(3) 
            logging.info("Form loaded successfully")
        except Exception as e:
            logging.error(f"Error waiting for form to load: {str(e)}")
            raise

    def get_question_text(self, question) -> str:
        """Extract the question text from a form element."""
        try:
            # Try multiple selectors for question text
            selectors = [
                "div[role='heading'] span",
                ".freebirdFormviewerComponentsQuestionBaseTitle",
                ".freebirdFormviewerViewItemsItemItemTitle",
                ".docssharedWizToggleLabeledLabelText",
                ".M7eMe",
                "label",
                "span[aria-label]"
            ]
           
            for selector in selectors:
                try:
                    element = question.locator(selector).first
                    if element:
                        text = element.inner_text().strip()
                        if text and text != "":
                            return text
                except Exception:
                    continue
           
            # Fallback: try to get any text content from the question container
            try:
                all_text = question.inner_text().strip()
                if all_text:
                    # Take first line as question text
                    lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                    if lines:
                        return lines[0]
            except Exception:
                pass
           
            return "Unknown Question"
        except Exception as e:
            logging.debug(f"Error getting question text: {str(e)}")
            return "Unknown Question"

    def identify_question_type(self, question) -> str:
        """Identify the type of question based on its elements."""
        try:
            # Check for dropdown
            dropdown = question.query_selector("select, div[role='listbox']")
            if dropdown and dropdown.is_visible():
                return "dropdown"
           
            # Check for multiple choice (radio buttons)
            radio_count = question.query_selector_all("div[role='radio'], input[type='radio']")
            visible_radios = [r for r in radio_count if r.is_visible()]
            if visible_radios:
                return "multiple_choice"
           
            # Check for checkboxes
            checkbox_count = question.query_selector_all("div[role='checkbox'], input[type='checkbox']")
            visible_checkboxes = [cb for cb in checkbox_count if cb.is_visible()]
            if visible_checkboxes:
                return "checkbox"
           
            # Check for text input
            text_input = question.query_selector("input[type='text'], input[type='email']")
            if text_input and text_input.is_visible():
                return "short_answer"
           
            # Check for textarea
            textarea = question.query_selector("textarea")
            if textarea and textarea.is_visible():
                return "paragraph"
           
            return "unknown"
        except Exception as e:
            logging.debug(f"Error identifying question type: {str(e)}")
            return "unknown"

    def parse_custom_name(self, custom_input: str) -> Dict[str, str]:
        """Parse custom name input in format name+age+gender(F/M)"""
        try:
            # Clean the input
            custom_input = custom_input.strip()
            
            # Simple parsing: extract name (letters), age (digits), gender (F/M)
            name_part = re.findall(r'[a-zA-Z]+', custom_input)
            age_part = re.findall(r'\d+', custom_input)
            gender_part = re.findall(r'[FMfm]', custom_input)
            
            if name_part and age_part and gender_part:
                name = name_part[0]
                age = age_part[0]
                gender_code = gender_part[0].upper()
            else:
                # Fallback if parsing fails
                name = custom_input
                age = str(random.choice(SAMPLE_AGES))
                gender_code = random.choice(['F', 'M'])
            
            # Map gender code to full gender and MCQ options
            gender_map = {
                'F': {'full': 'Female', 'options': ['Female', 'F', 'Girl', 'Woman', 'female']},
                'M': {'full': 'Male', 'options': ['Male', 'M', 'Boy', 'Man', 'male']}
            }
            
            gender_info = gender_map.get(gender_code, {'full': 'Other', 'options': ['Other', 'Prefer not to say', 'other']})
            
            return {
                'name': name,
                'age': age,
                'gender_code': gender_code,
                'gender_full': gender_info['full'],
                'gender_options': gender_info['options'],
                'original_input': custom_input
            }
        except Exception as e:
            logging.error(f"Error parsing custom name '{custom_input}': {str(e)}")
            # Fallback to random values
            return {
                'name': f"{random.choice(SAMPLE_FIRST_NAMES)}",
                'age': str(random.choice(SAMPLE_AGES)),
                'gender_code': random.choice(['F', 'M']),
                'gender_full': random.choice(['Female', 'Male']),
                'gender_options': ['Female', 'Male', 'Other', 'female', 'male'],
                'original_input': custom_input
            }

    def get_next_name(self) -> Dict[str, str]:
        """Get the next name from the list and parse it."""
        if not self.names:
            # Generate a random name in the required format
            random_name = f"{random.choice(SAMPLE_FIRST_NAMES)}{random.choice(SAMPLE_AGES)}{random.choice(['F', 'M'])}"
            return self.parse_custom_name(random_name)
       
        custom_input = self.names[self.current_name_index]
        self.current_name_index = (self.current_name_index + 1) % len(self.names)
        return self.parse_custom_name(custom_input)

    def generate_email(self, name: str, domain: str = None) -> str:
        """Generate email from name with specified domain."""
        # Clean the name for email (remove spaces and special chars)
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', name.split()[0] if ' ' in name else name).lower()
        if not domain:
            domain = random.choice(SAMPLE_EMAIL_DOMAINS)
        
        # Add random number to avoid duplicates
        random_num = random.randint(1, 999)
        return f"{clean_name}{random_num}{domain}"

    def detect_field_type(self, question_text: str) -> str:
        """Detect the field type based on question text keywords."""
        if question_text == "Unknown Question":
            return "general"
            
        text_lower = question_text.lower()
        
        if any(keyword in text_lower for keyword in ['email', 'e-mail', 'email address', 'e-mail address']):
            return "email"
        elif any(keyword in text_lower for keyword in ['name', 'full name', 'first name', 'last name', 'your name']):
            return "name"
        elif any(keyword in text_lower for keyword in ['age', 'how old', 'year of birth', 'birth year', 'your age']):
            return "age"
        elif any(keyword in text_lower for keyword in ['gender', 'sex', 'male/female', 'man/woman', 'select gender']):
            return "gender"
        
        return "general"

    def fill_dropdown(self, question, field_type: str, user_data: Dict[str, str]):
        """Handle dropdown question type with random selection."""
        try:
            # Try different dropdown selectors
            dropdown_selectors = [
                "select",
                "div[role='listbox']",
                ".quantumWizMenuPaperselectOptionList"
            ]
            
            for selector in dropdown_selectors:
                dropdown = question.query_selector(selector)
                if dropdown and dropdown.is_visible():
                    dropdown.click()
                    time.sleep(1)
                    
                    # Get options
                    option_selectors = [
                        "div[role='option']",
                        "option",
                        ".quantumWizMenuPaperselectOption"
                    ]
                    
                    for opt_selector in option_selectors:
                        options = self.page.query_selector_all(opt_selector)
                        visible_options = [opt for opt in options if opt.is_visible() and opt.inner_text().strip()]
                        
                        if visible_options:
                            # Skip first option if it's a placeholder
                            if len(visible_options) > 1 and not visible_options[0].inner_text().strip():
                                visible_options = visible_options[1:]
                            
                            if visible_options:
                                chosen_option = random.choice(visible_options)
                                chosen_option.click()
                                time.sleep(0.5)
                                return
                    
                    # If no options found, try to select by value
                    select_element = question.query_selector("select")
                    if select_element:
                        options = select_element.query_selector_all("option:not([disabled])")
                        if len(options) > 1:
                            select_element.select_option(index=random.randint(1, len(options)-1))
                            time.sleep(0.5)
                    return
                        
        except Exception as e:
            logging.error(f"Error filling dropdown: {str(e)}")

    def fill_checkboxes(self, question, field_type: str, user_data: Dict[str, str]):
        """Handle checkbox question type with random selection of multiple options."""
        try:
            checkboxes = question.query_selector_all("div[role='checkbox'], input[type='checkbox']")
            visible_checkboxes = [cb for cb in checkboxes if cb.is_visible()]
            
            if not visible_checkboxes:
                logging.warning("No visible checkboxes found")
                return
            
            # Determine how many checkboxes to select (at least 1, at most all)
            max_to_select = len(visible_checkboxes)
            min_to_select = min(1, max_to_select)
            
            # Randomly decide how many to select (between min and max)
            num_to_select = random.randint(min_to_select, max_to_select)
            
            # Randomly select which checkboxes to click
            checkboxes_to_select = random.sample(visible_checkboxes, num_to_select)
            
            logging.info(f"Selecting {num_to_select} out of {len(visible_checkboxes)} checkboxes")
            
            # Click the selected checkboxes
            for checkbox in checkboxes_to_select:
                try:
                    checkbox.click()
                    time.sleep(0.3)
                except Exception as e:
                    logging.warning(f"Could not click one checkbox: {str(e)}")
                    continue
                    
        except Exception as e:
            logging.error(f"Error filling checkboxes: {str(e)}")

    def fill_multiple_dropdowns(self, question, field_type: str, user_data: Dict[str, str]):
        """Handle multiple dropdowns in a single question (like multi-select dropdowns)."""
        try:
            # Look for multiple dropdown elements within the question
            dropdowns = question.query_selector_all("select, div[role='listbox']")
            visible_dropdowns = [dd for dd in dropdowns if dd.is_visible()]
            
            if not visible_dropdowns:
                logging.warning("No visible dropdowns found for multiple dropdown handling")
                return
            
            logging.info(f"Found {len(visible_dropdowns)} dropdowns in this question")
            
            # Process each dropdown
            for i, dropdown in enumerate(visible_dropdowns):
                try:
                    dropdown.click()
                    time.sleep(1)
                    
                    # Get options for this dropdown
                    option_selectors = [
                        "div[role='option']",
                        "option",
                        ".quantumWizMenuPaperselectOption"
                    ]
                    
                    options_found = False
                    for opt_selector in option_selectors:
                        options = self.page.query_selector_all(opt_selector)
                        visible_options = [opt for opt in options if opt.is_visible() and opt.inner_text().strip()]
                        
                        if visible_options:
                            # Skip first option if it's a placeholder
                            if len(visible_options) > 1 and not visible_options[0].inner_text().strip():
                                visible_options = visible_options[1:]
                            
                            if visible_options:
                                chosen_option = random.choice(visible_options)
                                chosen_option.click()
                                time.sleep(0.5)
                                options_found = True
                                break
                    
                    if not options_found:
                        # Fallback: try select element
                        select_element = dropdown if dropdown.tag_name == "select" else None
                        if not select_element:
                            select_element = dropdown.query_selector("select")
                        
                        if select_element:
                            options = select_element.query_selector_all("option:not([disabled])")
                            if len(options) > 1:
                                select_element.select_option(index=random.randint(1, len(options)-1))
                                time.sleep(0.5)
                                
                except Exception as e:
                    logging.warning(f"Error processing dropdown {i+1}: {str(e)}")
                    continue
                    
        except Exception as e:
            logging.error(f"Error filling multiple dropdowns: {str(e)}")

    def get_real_questions(self):
        """Get only real form questions, not decorative elements."""
        try:
            # More specific selectors for actual questions
            question_selectors = [
                ".freebirdFormviewerComponentsQuestionBaseRoot",
                ".freebirdFormviewerViewItemsItemItem",
                "div[role='listitem']",  # But filter these more carefully
                ".quantumWizTextinputPaperinputMainContent",
                ".freebirdFormviewerComponentsQuestionRadioRoot",
                ".freebirdFormviewerComponentsQuestionCheckboxRoot"
            ]
            
            all_elements = []
            for selector in question_selectors:
                elements = self.page.query_selector_all(selector)
                all_elements.extend(elements)
            
            # Remove duplicates and filter visible elements
            unique_elements = []
            seen = set()
            for element in all_elements:
                if element in seen:
                    continue
                seen.add(element)
                
                if element.is_visible():
                    # Additional filtering for listitems - they should contain form controls
                    if "listitem" in str(element.get_attribute("role") or ""):
                        has_controls = element.query_selector("input, textarea, select, [role='radio'], [role='checkbox']")
                        if has_controls:
                            unique_elements.append(element)
                    else:
                        unique_elements.append(element)
            
            logging.info(f"Found {len(unique_elements)} real questions after filtering")
            return unique_elements
            
        except Exception as e:
            logging.error(f"Error getting real questions: {str(e)}")
            return []

    def fill_form(self) -> bool:
        """Fill a single form with responses."""
        try:
            self.page.goto(self.form_url, wait_until="networkidle", timeout=60000)
            self.wait_for_form_load()

            # Get parsed user data
            user_data = self.get_next_name()
            logging.info(f"Using data for this submission: {user_data}")

            # Get real questions with better filtering
            questions = self.get_real_questions()
            
            if not questions:
                logging.error("No real questions found on the form")
                # Fallback to original method
                question_selectors = ["div[role='listitem']", ".freebirdFormviewerComponentsQuestionBaseRoot"]
                for selector in question_selectors:
                    questions = self.page.query_selector_all(selector)
                    if questions:
                        break

            if not questions:
                logging.error("No questions found at all")
                return False

            logging.info(f"Processing {len(questions)} questions")

            # Process each question
            for i, question in enumerate(questions, 1):
                try:
                    if not question.is_visible():
                        continue

                    question.scroll_into_view_if_needed()
                    time.sleep(0.3)

                    question_text = self.get_question_text(question)
                    logging.info(f"Processing question {i}: '{question_text}'")

                    # Detect field type based on question text
                    field_type = self.detect_field_type(question_text)
                    question_type = self.identify_question_type(question)
                    
                    logging.info(f"Field type: {field_type}, Question type: {question_type}")

                    if question_type == "dropdown":
                        self.fill_dropdown(question, field_type, user_data)
                        
                    elif question_type == "multiple_choice":
                        options = question.query_selector_all("div[role='radio'], input[type='radio']")
                        visible_options = [opt for opt in options if opt.is_visible()]
                       
                        if visible_options:
                            # For gender questions, try to select matching option
                            if field_type == "gender":
                                matched = False
                                for option in visible_options:
                                    # Try to get option text from various places
                                    option_text = ""
                                    try:
                                        # Get text from parent or sibling elements
                                        parent = option.query_selector("xpath=..")
                                        if parent:
                                            option_text = parent.inner_text().lower()
                                        else:
                                            option_text = option.get_attribute("aria-label") or ""
                                    except:
                                        pass
                                    
                                    for gender_option in user_data['gender_options']:
                                        if gender_option.lower() in option_text.lower():
                                            option.click()
                                            time.sleep(0.5)
                                            logging.info(f"Selected gender option: {gender_option}")
                                            matched = True
                                            break
                                    if matched:
                                        break
                                
                                if not matched:
                                    # If no gender match found, select random option
                                    chosen_option = random.choice(visible_options)
                                    chosen_option.click()
                                    time.sleep(0.5)
                            else:
                                # For non-gender MCQ, select random option
                                chosen_option = random.choice(visible_options)
                                chosen_option.click()
                                time.sleep(0.5)
                           
                            logging.info(f"Selected option for question {i}")
                        else:
                            logging.warning(f"No visible options found for question {i}")

                    elif question_type in ["short_answer", "paragraph"]:
                        input_element = None
                        if question_type == "short_answer":
                            input_element = question.query_selector("input[type='text'], input[type='email']")
                        else:
                            input_element = question.query_selector("textarea")
                       
                        if input_element and input_element.is_visible():
                            if field_type == "name":
                                input_element.fill(user_data['name'])
                                logging.info(f"Filled name: {user_data['name']}")
                            elif field_type == "email":
                                email = self.generate_email(user_data['name'])
                                input_element.fill(email)
                                logging.info(f"Filled email: {email}")
                            elif field_type == "age":
                                input_element.fill(user_data['age'])
                                logging.info(f"Filled age: {user_data['age']}")
                            else:
                                # For general text fields
                                if question_type == "short_answer":
                                    responses = ["Yes", "No", "Maybe", "Sometimes", "Often"]
                                    response = random.choice(responses)
                                    input_element.fill(response)
                                    logging.info(f"Filled short answer: {response}")
                                else:
                                    responses = [
                                        "This is a detailed response.",
                                        "Based on my experience, this is the best approach."
                                    ]
                                    response = random.choice(responses)
                                    input_element.fill(response)
                                    logging.info(f"Filled paragraph: {response}")
                            time.sleep(0.3)

                    elif question_type == "checkbox":
                        # Use the enhanced checkbox filling method
                        self.fill_checkboxes(question, field_type, user_data)

                    # Handle multiple dropdowns in a single question
                    elif question_type == "dropdown" and question.query_selector_all("select, div[role='listbox']").count() > 1:
                        self.fill_multiple_dropdowns(question, field_type, user_data)

                except Exception as e:
                    logging.error(f"Error processing question {i}: {str(e)}")
                    continue

            # Submit the form
            submit_button = None
            submit_button_selectors = [
                "div[role='button']:has-text('Submit')",
                "button:has-text('Submit')",
                ".freebirdFormviewerViewNavigationSubmitButton",
                "div[jsname='M2UYVd']",
                "input[type='submit']"
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
                time.sleep(1)
                submit_button.click()
                time.sleep(5)

                # Check for success
                try:
                    success_indicators = [
                        "Your response has been recorded",
                        "Thank you for completing",
                        "Form submitted successfully",
                        "responseConfirmationHeader"
                    ]
                    
                    page_text = self.page.inner_text("body").lower()
                    if any(indicator.lower() in page_text for indicator in success_indicators):
                        logging.info("Form submitted successfully")
                        return True
                    else:
                    
                        current_url = self.page.url
                        if "formResponse" in current_url or "thankyou" in current_url:
                            logging.info("Form submitted successfully (URL change detected)")
                            return True
                        
                        logging.warning("Submission success not confirmed")
                        return False
                        
                except Exception as e:
                    logging.error(f"Error checking submission status: {str(e)}")
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

    cpu_count = multiprocessing.cpu_count()
    usable_cpu_count = max(cpu_count // 2, 1)
    if max_workers is None:
        max_workers = min(usable_cpu_count, submission_count)

    logging.info(
        f"Starting {submission_count} threaded submissions with {max_workers} workers "
        f"(System has {cpu_count} CPU cores)"
    )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(submission_worker, form_url, names, i % len(names) if names else 0)
            for i in range(submission_count)
        ]

        for i, future in enumerate(as_completed(futures), 1):
            try:
                if future.result():
                    successful_submissions += 1
                else:
                    failed_submissions += 1

                if i % 5 == 0:
                    current_rate = i / (time.time() - start_time)
                    logging.info(
                        f"Completed {i}/{submission_count} submissions. "
                        f"Current rate: {current_rate:.2f}/sec"
                    )

            except Exception as e:
                failed_submissions += 1
                logging.error(f"Future error: {str(e)}")

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
    print("\nEnter names for each submission in format: name+age+gender(F/M)")
    print("Example: Zuck41M")
    print("Press Enter twice when done.")
    print("If you don't enter enough names, random names will be used for remaining submissions.")
    names = []
    while True:
        name = input().strip()
        if not name:
            if names: 
                break
            else:
                print("Please enter at least one name or press Enter again to use random names.")
                continue
        names.append(name)
    return names

def main():
    """Main entry point of the script."""
    setup_logging()

    form_url = input("Enter the Google Form URL: ").strip()
    while True:
        try:
            submission_count = int(input("Enter the number of submissions to make: "))
            if submission_count > 0:
                break
            print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")

    print("\nEnter the names to use for submissions (format: name+age+gender):")
    names = get_names_from_user()
    print(f"\nUsing {len(names)} names for submissions")
    if len(names) < submission_count:
        print(f"Will use random names for the remaining {submission_count - len(names)} submissions")

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