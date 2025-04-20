import requests
from typing import List, Any
from dotenv import load_dotenv
import os
import anthropic
from openai import OpenAI

def openai_model_list() -> List[Any]:
    load_dotenv()
    if not os.getenv('OPENAI_API_KEY'):
        return [];

    client = OpenAI()
    current_models_list = [model 
                        for model in client.models.list().data
                        if (model.owned_by=='system') and
                            (model.object == 'model') and
                            ('audio' not in model.id) and
                            ('gpt' in model.id) or 
                            ('o1' in model.id) or
                            ('o3' in model.id)
                       ]
    return current_models_list;