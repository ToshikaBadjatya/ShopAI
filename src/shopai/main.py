#!/usr/bin/env python
import sys
import warnings

from shopai.crew import Shopai

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the crew.
    """
    inputs = {
        'shopping_request': 'Casual weekend brunch outfit',
        'location': 'Indore, India',
        'budget': '$300',
        'gender': 'female',
        'height': '5\'10"',
        'body_type': 'skinny',
        'style': 'casual',
    }

    try:
        result = Shopai().crew().kickoff(inputs=inputs)
        print(result)
        print("Crew execution completed")
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        'shopping_request': 'Casual weekend brunch outfit',
        'location': 'San Francisco, California',
        'budget': '$300',
        'gender': 'female',
        'height': '5\'10"',
        'body_type': 'skinny',
        'style': 'casual',
    }
    try:
        Shopai().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        Shopai().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        'shopping_request': 'Casual weekend brunch outfit',
        'location': 'San Francisco, California',
        'budget': '$300',
        'gender': 'female',
        'height': '5\'10"',
        'body_type': 'skinny',
        'style': 'casual',
    }

    try:
        Shopai().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "shopping_request": "",
        "location": "",
        "budget": "",
        "gender": "",
        "height": "",
        "body_type": "",
        "style": "",
    }

    try:
        result = Shopai().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")


if __name__ == "__main__":
    run()