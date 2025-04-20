import requests
from typing import List, Any
from openai import OpenAI
from dotenv import load_dotenv

def openai_model_list() -> List[Any]:
    load_dotenv()
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