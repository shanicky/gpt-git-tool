#!/usr/bin/env python3
import asyncio
import os
import subprocess
import sys

from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"],
                     base_url=os.environ["OPENAI_API_BASE"])

MODEL = os.environ.get("MODEL_NAME", "gpt-4o-mini")

DIFF_PROMPT = "Generate a succinct summary of the following code changes:"
COMMIT_MSG_PROMPT = "Using no more than 1024 characters, generate a github pull request title and summary (in markdown format) from these summaries:"
PROMPT_CUTOFF = 10000

async def complete(prompt):
    completion_resp = await client.chat.completions.create(model=MODEL,
                                                           messages=[{"role": "user",
                                                                      "content": prompt[: PROMPT_CUTOFF + 100]}],
                                                           max_tokens=512)
    completion = completion_resp.choices[0].message.content.strip()
    return completion


async def summarize_diff(diff):
    assert diff
    return await complete(DIFF_PROMPT + "\n\n" + diff + "\n\n")


async def summarize_summaries(summaries):
    assert summaries
    return await complete(COMMIT_MSG_PROMPT + "\n\n" + summaries + "\n\n")

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


async def generate_commit_message(diff, branch):
    if not diff:
        # no files staged or only whitespace diffs
        return "Fix whitespace"
    else:
        summaries = await summarize_diff(diff)
    return await summarize_summaries(summaries)

async def main():
    try:
        branch = sys.argv[1]
        diff = get_diff_from_branch(branch)
        commit_message = await generate_commit_message(diff, branch)
    except UnicodeDecodeError:
        print("gpt-commit does not support binary files", file=sys.stderr)
        commit_message = "# gpt-commit does not support binary files. Please enter a commit message manually or unstage any binary files."

    print("\n\n" + commit_message + "\n\n")

if __name__ == "__main__":
    asyncio.run(main())