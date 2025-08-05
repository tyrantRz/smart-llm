import copy
import glob
import json
import os
import argparse
from pathlib import Path
from datetime import datetime
import random
import subprocess

from openai import OpenAI
import openai  

from httpx import Timeout                             
import ai2thor.controller

import sys
sys.path.append(".")

import resources.actions as actions
import resources.robots as robots

def build_client(api_key: str, project_id: str | None) -> OpenAI:
    """
    Return an OpenAI client bound to the given project-aware key.
    """
    project_id = project_id or os.getenv("OPENAI_PROJECT")
    if api_key.startswith("sk-proj-") and not project_id:
        raise ValueError(
            "Project Key detected but no project-id provided.\n"
            "· through CLI --openai-project-id proj_xxx\n"
            "· or export OPENAI_PROJECT=proj_xxx"
        )
    return OpenAI(
        api_key=api_key,
        project=project_id,
        timeout=Timeout(45)   
    )


def init_client(api_key_file: str, project_id: str | None) -> OpenAI:
    """
    Initialise OpenAI client from file/env variable.
    Works for both personal keys (sk-) and project keys (sk-proj-).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        api_key = Path(api_key_file).read_text().strip()
    return build_client(api_key, project_id)



def LM(client, prompt_or_msgs, model, max_tokens=128,
       temperature=0, stop=None, frequency_penalty=0):
    # ----- text completion -----
    if "gpt" not in model:
        rsp = client.completions.create(
            model=model,
            prompt=prompt_or_msgs,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
            frequency_penalty=frequency_penalty,
        )
        return rsp, rsp.choices[0].text.strip()

    # ----- chat completion -----
    rsp = client.chat.completions.create(
        model=model,
        messages=prompt_or_msgs,
        max_tokens=max_tokens,
        temperature=temperature,
        frequency_penalty=frequency_penalty,
        stop=stop,
    )
    return rsp, rsp.choices[0].message.content.strip()


def set_api_key(api_key_file: str, project_id: str | None = None) -> OpenAI:
    api_key = Path(api_key_file).read_text().strip()
    return build_client(api_key, project_id or os.getenv("OPENAI_PROJECT"))

# Function returns object list with name and properties.
def convert_to_dict_objprop(objs, obj_mass):
    objs_dict = []
    for i, obj in enumerate(objs):
        obj_dict = {'name': obj , 'mass' : obj_mass[i]}
        # obj_dict = {'name': obj , 'mass' : 1.0}
        objs_dict.append(obj_dict)
    return objs_dict

def get_ai2_thor_objects(floor_plan_id):
    # connector to ai2thor to get object list
    controller = ai2thor.controller.Controller(scene="FloorPlan"+str(floor_plan_id))
    obj = list([obj["objectType"] for obj in controller.last_event.metadata["objects"]])
    obj_mass = list([obj["mass"] for obj in controller.last_event.metadata["objects"]])
    controller.stop()
    obj = convert_to_dict_objprop(obj, obj_mass)
    return obj

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--floor-plan", type=int, required=True)
    parser.add_argument("--openai-api-key-file", default="api_key")        
    parser.add_argument("--openai-project-id",    default=None)            
    parser.add_argument("--gpt-version", default="gpt-4",
                        choices=['gpt-3.5-turbo', 'gpt-3.5-turbo-16k',       
                                'gpt-4', 'gpt-4o'])
    
    parser.add_argument("--prompt-decompse-set", type=str, default="train_task_decompose", 
                        choices=['train_task_decompose'])
    
    parser.add_argument("--prompt-allocation-set", type=str, default="train_task_allocation", 
                        choices=['train_task_allocation'])
    
    parser.add_argument("--test-set", type=str, default="final_test", 
                        choices=['final_test'])
    
    parser.add_argument("--log-results", type=bool, default=True)
    
    args = parser.parse_args()

    client = set_api_key(args.openai_api_key_file, args.openai_project_id)

    
    if not os.path.isdir(f"./logs/"):
        os.makedirs(f"./logs/")
        
    # read the tasks        
    test_tasks = []
    robots_test_tasks = []  
    gt_test_tasks = []    
    trans_cnt_tasks = []
    max_trans_cnt_tasks = []  
    with open (f"./data/{args.test_set}/FloorPlan{args.floor_plan}.json", "r") as f:
        for line in f.readlines():
            test_tasks.append(list(json.loads(line).values())[0])
            robots_test_tasks.append(list(json.loads(line).values())[1])
            gt_test_tasks.append(list(json.loads(line).values())[2])
            trans_cnt_tasks.append(list(json.loads(line).values())[3])
            max_trans_cnt_tasks.append(list(json.loads(line).values())[4])
                    
    print(f"\n----Test set tasks----\n{test_tasks}\nTotal: {len(test_tasks)} tasks\n")
    # prepare list of robots for the tasks
    available_robots = []
    for robots_list in robots_test_tasks:
        task_robots = []
        for i, r_id in enumerate(robots_list):
            rob = robots.robots [r_id-1]
            # rename the robot
            rob['name'] = 'robot' + str(i+1)
            task_robots.append(rob)
        available_robots.append(task_robots)
        
    
    ######## Train Task Decomposition ########
        
    # prepare train decompostion demonstration for ai2thor samples
    prompt = f"from skills import " + actions.ai2thor_actions
    prompt += f"\nimport time"
    prompt += f"\nimport threading"
    objects_ai = f"\n\nobjects = {get_ai2_thor_objects(args.floor_plan)}"
    prompt += objects_ai
    
    # read input train prompts
    decompose_prompt_file = open(os.getcwd() + "/data/pythonic_plans/" + args.prompt_decompse_set + ".py", "r")
    decompose_prompt = decompose_prompt_file.read()
    decompose_prompt_file.close()
    
    prompt += "\n\n" + decompose_prompt
    
    print ("Generating Decompsed Plans...")
    
    decomposed_plan = []
    for task in test_tasks:
        curr_prompt =  f"{prompt}\n\n# Task Description: {task}"
        
        if "gpt" not in args.gpt_version:
            # older gpt versions
            _, text = LM(client, curr_prompt, args.gpt_version, max_tokens=1000, stop=["def"], frequency_penalty=0.15)
        else:            
            messages = [{"role": "user", "content": curr_prompt}]
            _, text = LM(client, messages,args.gpt_version, max_tokens=1300, frequency_penalty=0.0)

        decomposed_plan.append(text)
        
    print ("Generating Allocation Solution...")

    ######## Train Task Allocation - SOLUTION ########
    prompt = f"from skills import " + actions.ai2thor_actions
    prompt += f"\nimport time"
    prompt += f"\nimport threading"
    
    prompt_file = os.getcwd() + "/data/pythonic_plans/" + args.prompt_allocation_set + "_solution.py"
    allocated_prompt_file = open(prompt_file, "r")
    allocated_prompt = allocated_prompt_file.read()
    allocated_prompt_file.close()
    
    prompt += "\n\n" + allocated_prompt + "\n\n"
    
    allocated_plan = []
    for i, plan in enumerate(decomposed_plan):
        no_robot  = len(available_robots[i])
        curr_prompt = prompt + plan
        curr_prompt += f"\n# TASK ALLOCATION"
        curr_prompt += f"\n# Scenario: There are {no_robot} robots available, The task should be performed using the minimum number of robots necessary. Robots should be assigned to subtasks that match its skills and mass capacity. Using your reasoning come up with a solution to satisfy all contraints."
        curr_prompt += f"\n\nrobots = {available_robots[i]}"
        curr_prompt += f"\n{objects_ai}"
        curr_prompt += f"\n\n# IMPORTANT: The AI should ensure that the robots assigned to the tasks have all the necessary skills to perform the tasks. IMPORTANT: Determine whether the subtasks must be performed sequentially or in parallel, or a combination of both and allocate robots based on availablitiy. "
        curr_prompt += f"\n# SOLUTION  \n"

        if "gpt" not in args.gpt_version:
            # older versions of GPT
            _, text = LM(client, curr_prompt, args.gpt_version, max_tokens=1000, stop=["def"], frequency_penalty=0.65)
        
        elif "gpt-3.5" in args.gpt_version:
            # gpt 3.5 and its variants
            messages = [{"role": "user", "content": curr_prompt}]
            _, text = LM(client, messages, args.gpt_version, max_tokens=1500, frequency_penalty=0.35)
        
        else:          
            # gpt 4.0
            messages = [{"role": "system", "content": "You are a Robot Task Allocation Expert. Determine whether the subtasks must be performed sequentially or in parallel, or a combination of both based on your reasoning. In the case of Task Allocation based on Robot Skills alone - First check if robot teams are required. Then Ensure that robot skills or robot team skills match the required skills for the subtask when allocating. Make sure that condition is met. In the case of Task Allocation based on Mass alone - First check if robot teams are required. Then Ensure that robot mass capacity or robot team combined mass capacity is greater than or equal to the mass for the object when allocating. Make sure that condition is met. In both the Task Task Allocation based on Mass alone and Task Allocation based on Skill alone, if there are multiple options for allocation, pick the best available option by reasoning to the best of your ability."},{"role": "system", "content": "You are a Robot Task Allocation Expert"},{"role": "user", "content": curr_prompt}]
            _, text = LM(client, messages, args.gpt_version, max_tokens=400, frequency_penalty=0.69)

        allocated_plan.append(text)
    
    print ("Generating Allocated Code...")
    
    ######## Train Task Allocation - CODE Solution ########

    prompt = f"from skills import " + actions.ai2thor_actions
    prompt += f"\nimport time"
    prompt += f"\nimport threading"
    prompt += objects_ai
    
    code_plan = []

    prompt_file1 = os.getcwd() + "/data/pythonic_plans/" + args.prompt_allocation_set + "_code.py"
    code_prompt_file = open(prompt_file1, "r")
    code_prompt = code_prompt_file.read()
    code_prompt_file.close()
    
    # -------- CODE-gen prompt --------------------------------------------------
prompt  = f"from skills import " + actions.ai2thor_actions
prompt += f"\nimport time\nimport threading"
prompt += objects_ai
prompt += "\n\n" + code_prompt + "\n\n"

# ★★ 强约束：让 LLM 只输出可执行 python ★★      ### <<<
prompt += (
    "# === RULES ===\n"
    "# 1. 只输出 _纯 Python 代码_ ，首行以 'def' 或 'import' 开头。\n"
    "# 2. 不要解释、Markdown、列表符号，结束时输出 '# END CODE'.\n"
    "# =========================================\n"
)                                            ### >>>
# ---------------------------------------------------------------------------

STOP_TOKENS = ["# END CODE", "```"]          ### <<< 终止符

for i, (plan, solution) in enumerate(zip(decomposed_plan, allocated_plan)):
    curr_prompt  = prompt + plan
    curr_prompt += "\n# TASK ALLOCATION"
    curr_prompt += f"\nrobots = {available_robots[i]}"
    curr_prompt += solution
    curr_prompt += "\n# CODE Solution\n"

    # ---------- 生成 ----------
    if "gpt" not in args.gpt_version:        # text 完成模型
        _, raw = LM(
            client, curr_prompt, args.gpt_version,
            max_tokens=2000, stop=STOP_TOKENS, frequency_penalty=0.30
        )
    else:                                    # chat 完成模型
        _, raw = LM(
            client,
            [{"role": "system", "content": "You are a Robot Task Allocation Expert"},
             {"role": "user",   "content": curr_prompt}],
            args.gpt_version,
            max_tokens=2000, stop=STOP_TOKENS, frequency_penalty=0.4
        )

    # ---------- 清洗 ----------
    clean = "\n".join(                       ### <<< 去掉空行 / markdown 列表
        l for l in raw.splitlines()
        if l.strip() and not l.lstrip().startswith(("-", "*", "•", "`"))
    )

    # ---------- 语法检查 ----------
    try:
        compile(clean, "<generated>", "exec")
    except SyntaxError as e:
        print(f"[WARN] code_plan 第 {i} 个任务语法错误:", e)

    code_plan.append(clean)                  ### >>>

    

# ------------------------------------------------------


    # save generated plan
exec_folders = []
if args.log_results:
    line = {}
    now = datetime.now() # current date and time
    date_time = now.strftime("%m-%d-%Y-%H-%M-%S")
        
    for idx, task in enumerate(test_tasks):
        task_name = "{fxn}".format(fxn = '_'.join(task.split(' ')))
        task_name = task_name.replace('\n','')
        folder_name = f"{task_name}_plans_{date_time}"
        exec_folders.append(folder_name)
            
        os.mkdir("./logs/"+folder_name)
     
        with open(f"./logs/{folder_name}/log.txt", 'w') as f:
            f.write(task)
            f.write(f"\n\nGPT Version: {args.gpt_version}")
            f.write(f"\n\nFloor Plan: {args.floor_plan}")
            f.write(f"\n{objects_ai}")
            f.write(f"\nrobots = {available_robots[idx]}")
            f.write(f"\nground_truth = {gt_test_tasks[idx]}")
            f.write(f"\ntrans = {trans_cnt_tasks[idx]}")
            f.write(f"\nmax_trans = {max_trans_cnt_tasks[idx]}")

        with open(f"./logs/{folder_name}/decomposed_plan.py", 'w') as d:
            d.write(decomposed_plan[idx])
                
        with open(f"./logs/{folder_name}/allocated_plan.py", 'w') as a:
            a.write(allocated_plan[idx])
                
        with open(f"./logs/{folder_name}/code_plan.py", 'w') as x:
            x.write(code_plan[idx])
            