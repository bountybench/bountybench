EXTRACTOR_PROMPT = """
{}
---
Task: Above is a long text scraped from a bug bounty website. The text contains information about a disclosed bug bounty. The text is unstructured and contains a lot of irrelevant information.
Your task is to write a highly specified function that extracts the required information from this specific text input. You have to ensure that your function returns 1) bounty_description: the description of the bug bounty, 2) bounty_proof: the proof of concept of the bug bounty. 3) extra: any other relevant information of the bounty, including metadata, cve, bounty value etc.
The output format should be purely the extraction function itself as it will be passed to the exec() function directly.

Output:
<extraction function>
"""