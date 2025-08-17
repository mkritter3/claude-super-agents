
import json
import sys
import subprocess
import os

TASKS_FILE = os.path.join(os.path.dirname(__file__), "..", "tasks.json")

def run_subagent(agent_name, prompt):
    full_prompt = f"Use the {agent_name} for the following task: {prompt}"
    command = ["claude", "--no-interactive", full_prompt]
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, cwd=project_dir)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_message = f"Subagent '{agent_name}' failed.\nExit Code: {e.returncode}\nStderr: {e.stderr}\nStdout: {e.stdout}"
        raise Exception(error_message)

def process_next_task():
    if not os.path.exists(TASKS_FILE):
        print("SYSTEM: Task file not found. No tasks to process.")
        return

    with open(TASKS_FILE, 'r+') as f:
        data = json.load(f)
        
        task_to_process = next((task for task in data['tasks'] if "PENDING" in task['status']), None)
        
        if not task_to_process:
            print("SYSTEM: All tasks are complete.")
            return

        task_id = task_to_process['task_id']
        status = task_to_process['status']
        
        print(f"ORCHESTRATOR: Found task {task_id} with status {status}. Dispatching to relevant agent...")
        
        try:
            if status == "PENDING_PLAN":
                plan = run_subagent("pm-agent", f"Create a plan for the task: '{task_to_process['title']}'")
                task_to_process['payload']['plan'] = plan
                task_to_process['status'] = "PENDING_CONTRACT_REVIEW"

            elif status == "PENDING_CONTRACT_REVIEW":
                plan = task_to_process['payload']['plan']
                review_json = run_subagent("contract-guardian", f"Review the following plan for contract changes: {plan}")
                review = json.loads(review_json)
                if review['decision'] == "APPROVED":
                    task_to_process['status'] = "PENDING_IMPLEMENTATION"
                else:
                    task_to_process['status'] = "FAILED"
                    task_to_process['payload']['contract_feedback'] = review['reason']

            elif status == "PENDING_IMPLEMENTATION":
                plan = task_to_process['payload']['plan']
                feedback = task_to_process['payload'].get('review_feedback', '')
                prompt = f"Implement the plan: '{plan}'. Address this feedback if any: '{feedback}'"
                files_changed_str = run_subagent("developer-agent", prompt)
                task_to_process['payload']['files_changed'] = json.loads(files_changed_str)
                task_to_process['status'] = "PENDING_REVIEW"

            elif status == "PENDING_REVIEW":
                files_str = json.dumps(task_to_process['payload']['files_changed'])
                review_result = run_subagent("reviewer-agent", f"Review the files listed in this JSON array: {files_str}")
                if review_result == "APPROVED":
                    task_to_process['status'] = "PENDING_INTEGRATION_TEST"
                else:
                    task_to_process['status'] = "PENDING_IMPLEMENTATION"
                    task_to_process['payload']['review_feedback'] = review_result
            
            elif status == "PENDING_INTEGRATION_TEST":
                files_str = json.dumps(task_to_process['payload']['files_changed'])
                test_result = run_subagent("integration-tester-agent", f"Run integration tests for the changes in these files: {files_str}")
                if test_result == "INTEGRATION_TESTS_PASSED":
                    task_to_process['status'] = "COMPLETE"
                else:
                    task_to_process['status'] = "FAILED"
                    task_to_process['payload']['test_failures'] = test_result

            task_to_process['history'].append(f"Successfully processed {status}.")
            print(f"ORCHESTRATOR: Task {task_id} has been successfully advanced to status: {task_to_process['status']}")

        except Exception as e:
            error_str = str(e)
            print(f"ORCHESTRATOR: Error processing {task_id} at status {status}.\n{error_str}", file=sys.stderr)
            task_to_process['status'] = "FAILED"
            task_to_process['history'].append(f"Failed on status {status}: {error_str}")

        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()

def create_task(title):
    if not os.path.exists(TASKS_FILE):
        data = {"tasks": []}
    else:
        with open(TASKS_FILE, 'r') as f:
            data = json.load(f)
    
    new_task_id = f"TICKET-{len(data['tasks']) + 1}"
    data['tasks'].append({
        "task_id": new_task_id, "title": title, "status": "PENDING_PLAN",
        "dependencies": [], "payload": {}, "history": ["Task created"]
    })
    
    with open(TASKS_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"ORCHESTRATOR: Created new task: {new_task_id} - {title}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "process-next":
            process_next_task()
        elif command == "create" and len(sys.argv) > 2:
            create_task(" ".join(sys.argv[2:]))
