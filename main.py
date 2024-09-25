import random
import logging.config
import yaml

# Dictionary with participants and last couple years of givers
past_year_assignments = {
    "Alex": ["Babsi", "Kathi", "Kathi"],
    "Magda": ["Martin", "Alex", "Martin"],
    "Kathi": ["Alex", "Martin", "Babsi"],
    "Steffi": ["Magda", "Babsi", "Alex"],
    "Martin": ["Kathi", "Magda", "Magda"],
    "Babsi": ["Steffi", "Steffi", "Steffi"]
}

# Logging setup
with open('logging_config.yaml', 'r') as config_file:
    logging_config = yaml.safe_load(config_file.read())
    logging.config.dictConfig(logging_config)

logger = logging.getLogger('main')
logger.info('Logging setup complete')


# Function to check if the current pairing is valid
def is_valid_pairing(assignments: dict, past_assignments: dict) -> bool:
    """
    Checks if the current Secret Santa assignments are valid by ensuring that no one is
    paired with a recipient they had in the last two years.

    Parameters:
        assignments (dict): The proposed Secret Santa assignments with givers as keys and recipients as values.
        past_assignments (dict): A dictionary containing the past few years' assignments for each participant.

    Returns:
        bool: True if the assignments are valid, False otherwise.
    """
    for giver, recipient in assignments.items():
        logger.debug(f'Checking {giver} with {recipient}')

        # Check last two years of assignments
        if recipient in past_assignments.get(giver, [])[-2:]:
            logger.debug(f'{giver} already had {recipient} in the last 2 years')
            return False

    logger.debug(f'Pairings complete')
    return True


def generate_secret_santa(past_year_assignments: dict) -> dict:
    """
    Generates a valid Secret Santa assignment, ensuring no participant gets the same recipient they had
    in the last two years, and that no one is paired with themselves.

    Parameters:
        past_year_assignments (dict): A dictionary with participants as keys and a list of
                                      their recipients from the last few years as values.

    Returns:
        dict: A valid Secret Santa assignment where each giver (key) is assigned a recipient (value).
    """
    names = list(past_year_assignments.keys())
    recipients = names[:]
    assignment = {}

    # Try generating a valid assignment within 100 attempts
    for _ in range(100):
        # Shuffle the names randomly for pairing
        random.shuffle(recipients)

        # Create a candidate assignment (assign each giver a recipient)
        candidate_assignment = {giver: recipient for giver, recipient in zip(names, recipients)}

        # Make sure no one is assigned to themselves
        if any(giver == recipient for giver, recipient in candidate_assignment.items()):
            continue

        # Check if the current candidate satisfies the "no last two years" rule
        if is_valid_pairing(candidate_assignment, past_year_assignments):
            assignment = candidate_assignment
            break

    return assignment


# Generate the new Secret Santa assignments
new_assignments = generate_secret_santa(past_year_assignments)

# Output the result
for giver, recipient in new_assignments.items():
    logger.info(f'{giver} -> {recipient}')
