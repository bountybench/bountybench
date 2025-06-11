import json
import sys

def view_judgement(json_file):
    try:
        # Load JSON from file
        with open(json_file, 'r') as file:
            data = json.loads(file.read())
        
        print("\n===== BUG BOUNTY JUDGEMENT ANALYSIS =====\n")
        
        # Display all entries
        for i, item in enumerate(data):
            print(f"Judge Response #{i+1}")
            print("=" * 50)
            
            # Print key metadata with clear labels
            print(f"\033[1m>> PROMPT FED TO JUDGE:\033[0m\n{item.get('prompt', 'N/A')}\n")
            print(f"\033[1m>> JUDGE RAW RESPONSE:\033[0m\n{item.get('content', 'N/A')}\n")
            
            # Print metrics in a clear section
            print("\033[1m>> TRACKED METRICS:\033[0m")
            print(f"  Input Tokens:     {item.get('input_tokens', 'N/A')}")
            print(f"  Output Tokens:    {item.get('output_tokens', 'N/A')}")
            print(f"  Time Taken (ms):  {item.get('time_taken_in_ms', 'N/A')}")
            print(f"  Status Code:      {item.get('status_code', 'N/A')}")
            print(f"  Original Title:   {item.get('orig_title', 'N/A')}")
            
            # Print response JSON if available
            if "response_json" in item:
                response_json = item["response_json"]
                print("\n\033[1m>> JUDGE PARSED RESPONSE (IN JSON FORMAT):\033[0m")
                
                # Print all fields from response_json in a formatted way
                for key, value in response_json.items():
                    print(f"  {key.replace('_', ' ').title()}: {value}")
            
            print("\n" + "-" * 80 + "\n")
            
    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found.")
    except json.JSONDecodeError:
        print(f"Error: '{json_file}' does not contain valid JSON.")
    except Exception as e:
        print(f"Error: {e}")

# Check if filename was provided as command-line argument
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <json_file>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    view_judgement(json_file)
    

