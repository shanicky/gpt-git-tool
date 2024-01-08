#!/usr/bin/env python3

import openai
import os
import subprocess
import sys

DIFF_PROMPT = "Generate a succinct summary of the following code changes:"
COMMIT_MSG_PROMPT = "Using no more than 5000 characters, generate a github pull request title and summary (in markdown format) from these summaries:"
PROMPT_CUTOFF = 10000
openai.organization = os.getenv("OPENAI_ORG_ID")
openai.api_key = os.environ["OPENAI_API_KEY"]
openai.api_base = os.environ["OPENAI_API_BASE"]


def complete(prompt):
    completion_resp = openai.ChatCompletion.create(model="gpt-4-1106-preview",
                                                   messages=[{
                                                       "role":
                                                       "user",
                                                       "content":
                                                       prompt[:PROMPT_CUTOFF]
                                                   }],
                                                   max_tokens=512)
    completion = completion_resp.choices[0].message.content.strip()
    return completion


def summarize_diff(diff):
    assert diff
    return complete(DIFF_PROMPT + "\n\n" + diff + "\n\n")


def summarize_summaries(summaries):
    assert summaries
    return complete(COMMIT_MSG_PROMPT + "\n\n" + summaries + "\n\n")


def get_diff_from_branch(branch, path=".", diff_filter="ACDMRTUXB", name_only=False):
    arguments = [
        "git", "--no-pager", "diff", f"{branch}", "--staged", "--ignore-space-change",
        "--ignore-all-space", "--ignore-blank-lines",
        f"--diff-filter={diff_filter}"
    ]
    if name_only:
        arguments.append("--name-only")
    
    diff_process = subprocess.run(arguments + [path],
                                  capture_output=True,
                                  text=True)
    diff_process.check_returncode()
    return diff_process.stdout.strip()

def generate_commit_message(diff, branch):
    if not diff:
        # no files staged or only whitespace diffs
        return "Fix whitespace"
    else:
        summaries = summarize_diff(diff)
    return summarize_summaries(summaries)

if __name__ == "__main__":
    try:
        branch = sys.argv[1]
        diff = get_diff_from_branch(branch)
        commit_message = generate_commit_message(diff, branch)
    except UnicodeDecodeError:
        print("gpt-commit does not support binary files", file=sys.stderr)
        commit_message = "# gpt-commit does not support binary files. Please enter a commit message manually or unstage any binary files."

    print("\n\n" + commit_message + "\n\n")
