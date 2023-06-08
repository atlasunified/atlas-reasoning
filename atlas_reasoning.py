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

    with concurrent.futures.ThreadPoolExecutor() as executor:
        tasks = []
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
                future = executor.submit(make_request, task)
                tasks.append(future)

        while tasks:
            done, tasks = concurrent.futures.wait(tasks, return_when=concurrent.futures.FIRST_COMPLETED)

            for future in done:
                if future.exception():
                    task = future.result()
                    if task["retries"] > 0:
                        task["retries"] -= 1
                        print(f"Error on topic '{task['topic']}' and subtopic '{task['subtopic']}', retrying. {task['retries']} retries left.")
                        tasks.add(executor.submit(make_request, task))
                    else:
                        print(f"Error on topic '{task['topic']}' and subtopic '{task['subtopic']}', no retries left.")
                else:
                    print(f"Completed topic '{future.result()['topic']}' and subtopic '{future.result()['subtopic']}'.")

def make_request(task):
    topic = task["topic"]
    subtopic = task["subtopic"]
    retries = task["retries"]

    print(f"\nInitiating request for topic '{topic}' and subtopic '{subtopic}' with {retries} retries left.")

    try:
        messages=[
            {
                "role": "system", 
                "content": "You are a language model capable of creating reasoning tasks. Each task should consist of a prompt, a step-by-step reasoning, and a final solution."
            },
            {
                "role": "user", 
                "content": f"Given the topic '{topic}' and sub-topic '{subtopic}', generate 10 reasoning tasks of high complexity. Each task should include a prompt (a question or problem), a step-by-step reasoning (a logical explanation of how to arrive at the solution), and a solution (the final answer to the problem). Remember, the output format should be a list like this: ['prompt', 'step_by_step_reasoning', 'solution']."
            }
        ]
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=3000  # Adjust this as needed
        )
        # Prepare the response
        response = f"{completion.choices[0].message['content']}"

        # Output the response to a text file named after the topic and subtopic
        with open(f'output/{topic}_{subtopic}.txt', 'w', encoding='utf-8') as f:
            f.write(response)

        print(f"Successful request for topic '{topic}' and subtopic '{subtopic}'. Writing to file.")
    except Exception as e:
        print(f"Exception occurred for topic '{topic}' and subtopic '{subtopic}'.")
        task["exception"] = e
    finally:
        return task

task_id_counter = 0  # Global counter for task IDs

def cleanse_text(line):
    global task_id_counter
    # Removing leading number and period
    clean_line = re.sub(r'^\d+\.\s*', '', line)
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

import csv

def text_to_csv(dir_path, output_file):
    files_list = os.listdir(dir_path)
    text_files_list = [file for file in files_list if file.endswith('.txt')]

    with open(output_file, 'w', encoding='utf-8') as csv_file:
        csv_file.write('Prompt,Step-by-step reasoning,Solution\n')  # Write header

        for text_file in text_files_list:
            with open(os.path.join(dir_path, text_file), 'r', encoding='utf-8') as f:
                content = f.read()

                # join multiple lines into a single line and split by solutions
                entries = content.replace('\n', ' ').split('Solution:')
                for entry in entries:
                    if entry.strip():  # ignore empty lines or lines only consisting of whitespace
                        entry = entry.replace('=', '')  # remove any '=' sign
                        _, _, after_prompt = entry.partition('Prompt:')
                        prompt, _, after_reasoning = after_prompt.partition('Step-by-step reasoning:')
                        reasoning = after_reasoning.strip()
                        # As solutions were used as separator, they will be in the next entry in entries list
                        try:
                            solution = entries[entries.index(entry) + 1].split('Prompt:')[0] if (entries.index(entry) + 1) < len(entries) else ''
                        except ValueError:
                            print(f"Could not find entry in entries: {entry}")
                            solution = ''  # or whatever default value makes sense in your case
                        # strip everything past the period on the solution
                        solution = solution.split('.')[0] 

                        # Check if all parts are non-empty
                        if all([prompt.strip(), reasoning.strip(), solution.strip()]):  
                            # Write to CSV directly, avoiding triple quotes
                            csv_file.write(f'"{prompt.strip()}","{reasoning.strip()}","{solution.strip()}"\n')

            os.remove(os.path.join(dir_path, text_file))  # delete the txt file after converting


def main():
    generate_text_files()
    dir_path = 'output/'
    output_file = 'output.csv'
    text_to_csv(dir_path, output_file)


if __name__ == "__main__":
    main()
