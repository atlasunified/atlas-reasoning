# atlas-reasoning

This Python code is a comprehensive program that utilizes the OpenAI GPT-3 model to generate reasoning tasks based on provided topics and subtopics, and then format and store the generated tasks.

## Functionalities

The program reads topics and subtopics from a JSONL (JSON Lines text format) file. Each line of the JSONL file should represent a JSON object with a topic and its corresponding subtopics.

For each topic and subtopic pair, the program makes a request to the OpenAI GPT-3 model to generate reasoning tasks. The request instructs the model to produce 10 high-complexity tasks, each consisting of a prompt, step-by-step reasoning, and a solution.

The responses from the model are then written to individual text files in an output directory. Each file is named according to its topic and subtopic.

In case of an error or exception during a request, the program includes a retry mechanism with a set maximum number of retries.

Once all tasks are generated and saved, the program cleanses and formats the text within these files to maintain a consistent, readable format. The cleaning operations include removing leading numbers and periods, replacing names and ids, and more.

After the cleaning process, the program compiles all text files into a CSV file, with each entry in the CSV file representing a task. The columns of the CSV file are 'Prompt', 'Step-by-step reasoning', and 'Solution'. The corresponding text files are deleted after being converted to CSV entries to avoid redundancy.

The entire process is initiated by calling the main() function, which sequentially calls the generate_text_files() and text_to_csv() functions.

When you run this script, it starts generating reasoning tasks based on the topics and subtopics provided in the 'topics_subtopics.jsonl' file, writing the results to individual text files, and finally compiles all these files into a CSV file.

## Note

This script is designed to handle topics and subtopics in a specific format. It also expects certain key files like 'apikey.txt' and 'topics_subtopics.jsonl' to be available. Please ensure these files are in place before running the script.
