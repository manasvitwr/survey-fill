# Survey-filler
A Python script that automatically fills and submits google forms multiple times using randomized answers for selectable questions. It uses playwright to simulate browser interactions and can run multiple submissions concurrently.

## Main Features
* Automatically detects and answers multiple choice (MCQs), checkbox, linear scale, and grid questions with random selections
* Fills name fields with custom names or random names if not provided
* Supports multiple concurrent submissions using thread pooling
* Skips all text-based questions except name fields
* Maintains detailed logging of submission progress and results

## How To Use
1. Install dependencies  
```bash
  pip install playwright
  playwright install chromium
  ```
2. Execute the script  
```bash
python main.py
```

3. Enter the Google Form URL when prompted.
4. Specify how many submissions you want to make.
5. Enter names for each submission (one per line, then press Enter twice when done).
6. The script will automatically process all submissions and show progress.
7. View the final summary showing successful and failed submissions.

## Disclaimer

- This tool is meant only for Google Forms that contain only objective multiple choice, checkbox, or other fully selectable questions. It will not work correctly on forms requiring text or paragraph answers, or with 'next' or multi-step question navigation and dropdowns (nake sure they are not marked as required in the form).
- Make sure the form accepts multiple submissions before running this tool.
- If you want to submit custom names, enter them manually when prompted; if you skip this, random names will be filled in automatically by the script.
- Inappropriate use or spamming of forms is strictly discouraged and can result in errors or your responses being ignored.
- Errors will occur if you use the tool on forms not matching the above requirements.

## Demo

```text
Enter the Google Form URL: [pasted form link]
Enter the number of submissions to make: 3

Enter the names to use for submissions:

Enter names for each submission (one per line). Press Enter twice when done.
If you don't enter enough names, random Indian names will be used for remaining submissions.
testname1
testname2
testname3

Using 3 names for submissions
```
