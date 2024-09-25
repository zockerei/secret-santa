import random
import logging.config
import yaml

# Logging setup
with open('logging_config.yaml', 'rt') as config_file:
    logging_config = yaml.safe_load(config_file.read())
    logging.config.dictConfig(logging_config)

logger = logging.getLogger('main')
logger.info('Logging setup complete')


def secret_santa(participants, past_assignments=None):
    """
    Parameters:
        participants: list of names
        past_assignments: list of tuples from last year [(giver, receiver)]
    """

    # Copy list of participants to shuffle
    givers = participants[:]
    receivers = participants[:]

    # Initialize an empty list to store current assignments
    assignments = []

    # Shuffle the givers and receivers to randomize
    random.shuffle(givers)
    random.shuffle(receivers)

    # Try to assign givers to receivers
    for giver in givers:
        valid_receivers = [r for r in receivers if r != giver]

        # If past assignments exist, filter out repeated pairs
        if past_assignments:
            valid_receivers = [r for r in valid_receivers if (giver, r) not in past_assignments]

        # If no valid receiver is left, restart the process
        if not valid_receivers:
            return secret_santa(participants, past_assignments)

        # Randomly select a valid receiver
        receiver = random.choice(valid_receivers)
        assignments.append((giver, receiver))

        # Remove the assigned receiver from the list of receivers
        receivers.remove(receiver)

    return assignments


# Example usage
family_members = ["Alex", "Magda", "Kathi", "Steffi", "Martin", "Barbara"]
past_year_assignments = {
    "Alex": ["Babsi", "Kathi", "Kathi"],
    "Magda": ["Martin", "Alex", "Martin"],
    "Kathi": ["Alex", "Martin", "Babsi"],
    "Steffi": ["Magda", "Babsi", "Alex"],
    "Martin": ["Kathi", "Magda", "Magda"],
    "Barbara": ["Steffi", "Steffi", "Steffi"]
}

current_assignments = secret_santa(family_members, past_year_assignments)

# Print the results
for giver, receiver in current_assignments:
    print(f'{giver} will give a gift to {receiver}')
