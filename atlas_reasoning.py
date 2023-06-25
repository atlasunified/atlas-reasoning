import os
import openai
import json
import re
import concurrent.futures
import time
import csv

MAX_RETRIES = 5

def generate_text_files():
    # Read the API key from 'apikey.txt'
    with open('apikey.txt', 'r', encoding='utf-8') as f:
        openai.api_key = f.read().strip()

    # Open the JSONL file and load the topics and subtopics
    with open('topics_subtopics.jsonl', 'r') as f:
        lines = f.readlines()

    tasks = []
    task_set = set()  # Define the task_set as an empty set
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for line in lines:
            topic_data = json.loads(line)
            topic = topic_data["topic"]
            subtopics = topic_data["subtopics"]

            for subtopic in subtopics:
                task = {
                    "topic": topic,
                    "subtopic": subtopic,
                    "retries": MAX_RETRIES
                }
                tasks.append(task)

        for task in tasks:
            task_set.add(str(task))  # Add every task to the task_set
            futures.append(executor.submit(make_request, task))

        while futures:
            done, futures = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)

            for future in done:
                task = future.result()
                if "exception" in task:
                    if task["retries"] > 0:
                        task["retries"] -= 1
                        print(f"Error on topic '{task['topic']}' and subtopic '{task['subtopic']}', retrying. {task['retries']} retries left.")
                        futures.add(executor.submit(make_request, task))
                    else:
                        print(f"Error on topic '{task['topic']}' and subtopic '{task['subtopic']}', no retries left.")
                else:
                    task_set.remove(str(task))  # If the task was successful, remove it from the task_set
                    print(f"Completed topic '{task['topic']}' and subtopic '{task['subtopic']}'.")

    # Check if the set is empty at the end of processing
    if not task_set:
        print("All tasks have been completed successfully.")
    else:
        print(f"Following tasks were not completed: {task_set}")

    # Check the existence of the output files in the directory for each task.
    for task in tasks:
        topic = task["topic"]
        subtopic = task["subtopic"]
        if not os.path.isfile(f'output/{topic}_{subtopic}.txt'):
            print(f"Output file for task ({topic}, {subtopic}) does not exist.")
        else:
            print(f"Output file for task ({topic}, {subtopic}) is successfully written.")

def make_request(task):
    topic = task["topic"]
    subtopic = task["subtopic"]
    retries = task["retries"]

    # Check if the file exists, if yes, return the task and skip the rest
    output_file = f'output/{topic}_{subtopic}.txt'
    if os.path.isfile(output_file):
        print(f"File '{output_file}' already exists, skipping request.")
        return task

    print(f"\nInitiating request for topic '{topic}' and subtopic '{subtopic}' with {retries} retries left.")

    try:
        messages=[
            {
                "role": "system", 
                "content": "You are a language model capable of creating reasoning tasks. Each task should consist of a prompt, a step-by-step reasoning, and a final solution. Your strength is in brevity and answering directly, avoiding jargon such as 'sure, I can help, what would you like to know'."
            },
            {
                "role": "user", 
                "content": f"Generate 10 complex reasoning tasks on the topic of '{topic}' and sub-topic '{subtopic}'. Each task should include a prompt (a question or problem), a step-by-step reasoning (a logical explanation of how to arrive at the solution), and a solution (the final answer to the problem). The output format should be a list like this: ['prompt', 'step_by_step_reasoning', 'solution']. Do not deviate from the JSON format of {json.dumps({'id': 'string', 'task': [{'prompt': 'string', 'reasoning': 'string', 'solution': 'string'}]})}. Keep the tasks succinct, comprehensive, and avoid any unnecessary language. Keep all responses in JSON format and all on one line. Have these reasoning tasks on the PhD level and have high complexity factors."
            }
        ]

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=3000  # Adjust this as needed
        )

        # Try to parse the response as JSON
        try:
            response = json.loads(completion.choices[0].message['content'])
        except json.JSONDecodeError:
            # If it fails, handle the failure. For example, you might just write the
            # raw output or manually convert the result into the desired format.
            # The specific action depends on the specific requirements of your project.
            response = {
                "id": "fallback_id",
                "task": [{
                    "prompt": "Fallback prompt",
                    "reasoning": "Fallback reasoning",
                    "solution": "Fallback solution"
                }]
            }

        # Output the response to a text file named after the topic and subtopic
        with open(f'output/{topic}_{subtopic}.txt', 'w', encoding='utf-8') as f:
            f.write(json.dumps(response))

        print(f"Successful request for topic '{topic}' and subtopic '{subtopic}'. Writing to file.")
    except Exception as e:
        print(f"Exception occurred for topic '{topic}' and subtopic '{subtopic}'.")
        task["exception"] = e
    finally:
        return task

task_id_counter = 0  # Global counter for task IDs

def cleanse_text(line):
    global task_id_counter
    # Remove newlines
    clean_line = line.replace('\n', ' ')
    # Removing leading number and period
    clean_line = re.sub(r'^\d+\.\s*', '', clean_line)
    # Using regex to find and replace 'name' with modified 'name'
    match_name = re.search(r"'name': '([^']+)'", clean_line)
    if match_name:
        old_name = match_name.group(1)
        new_name = old_name.lower().replace(' ', '_')
        clean_line = clean_line.replace(old_name, new_name)
    # Replace 'id' with a new one
    match_id = re.search(r"'id': '([^']+)'", clean_line)
    if match_id:
        old_id = match_id.group(1)
        new_id = f'seed_task_{task_id_counter}'
        clean_line = clean_line.replace(old_id, new_id)
        task_id_counter += 1
    return clean_line


def text_to_csv(dir_path, output_file):
    files_list = os.listdir(dir_path)
    text_files_list = [file for file in files_list if file.endswith('.txt')]

    with open(output_file, 'w', encoding='utf-8', newline='') as csv_file:
        writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)  # Create a csv.writer
        writer.writerow(['id', 'Prompt', 'Step-by-step reasoning', 'Solution'])  # Write header

        for text_file in text_files_list:
            with open(os.path.join(dir_path, text_file), 'r', encoding='utf-8') as f:
                for line in f:
                    line = cleanse_text(line).strip()
                    # Ensure line isn't empty
                    if line:
                        # Load the JSON object from the line
                        try:
                            task = json.loads(line)
                            id = task["id"]
                            prompt = task["task"][0]["prompt"]
                            reasoning = task["task"][0]["reasoning"]
                            solution = task["task"][0]["solution"]

                            print(f"id: {id}")
                            print(f"Prompt: {prompt}")
                            print(f"Reasoning: {reasoning}")
                            print(f"Solution: {solution}")

                            # Write to CSV directly, avoiding triple quotes
                            writer.writerow([id, prompt, reasoning, solution])  # Use the writer to write the row
                        except json.JSONDecodeError:
                            print(f"Couldn't parse JSON from line: {line}")
            # os.remove(os.path.join(dir_path, text_file))  # delete the txt file after converting


def main():
    if not os.path.exists('output'):
        os.makedirs('output')
    generate_text_files()
    dir_path = 'output/'
    output_file = 'output.csv'
    text_to_csv(dir_path, output_file)


if __name__ == "__main__":
    main()
