EXTRACTOR_PROMPT = """
{}
---
Task: Above is a long text scraped from a bug bounty website. The text contains information about a disclosed bug bounty. The text is unstructured and contains a lot of irrelevant information.
Your task is to write a highly specified function that extracts the required information from this specific text input. You have to ensure that your function returns a dictionary with the following: 1) description: the description of the bug bounty, 2) proof: the proof of concept of the bug bounty. 3) bug_commit: the commit hash of the bug (can be empty if not found) 4) bug_tag: the tag of the bug (can be empty if not found) 5) patch_commit: the commit hash of the patch to the bug (can be empty if not found) 6) patch_tag: the tag of the patch to the bug (can be empty if not found) 7) extra: any other relevant information of the bounty, including metadata, cve, bounty value etc.
The output format should be purely the extraction function itself as it will be passed to the exec() function directly.

Output:
<extraction function>
"""
