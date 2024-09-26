import random
import logging.config
import yaml
import sql

# Original dictionary for reference (used to initially populate the database)
past_year_assignments = {
    "Alex": ["Babsi", "Kathi", "Kathi"],
    "Magda": ["Martin", "Alex", "Martin"],
    "Kathi": ["Alex", "Martin", "Babsi"],
    "Steffi": ["Magda", "Babsi", "Alex"],
    "Martin": ["Kathi", "Magda", "Magda"],
    "Babsi": ["Steffi", "Steffi", "Steffi"]
}

sql_statements = sql.SqlStatements()
sql_statements.create_tables()

# Logging setup
with open('logging_config.yaml', 'r') as config_file:
    logging_config = yaml.safe_load(config_file.read())
    logging.config.dictConfig(logging_config)

logger = logging.getLogger('main')
logger.info('Logging setup complete')


# Function to check if the current pairing is valid
def is_valid_pairing(assignments: dict, past_receiver: dict) -> bool:
    """
    Checks if the current Secret Santa assignments are valid by ensuring that no one is
    paired with a recipient they had in the last two years.

    Parameters:
        assignments (dict): The proposed Secret Santa assignments with givers as keys and recipients as values.
        past_receiver (dict): A dictionary containing the past few years' assignments for each participant.

    Returns:
        bool: True if the assignments are valid, False otherwise.
    """
    for giver, recipient in assignments.items():
        logger.debug(f'Checking {giver} with {recipient}')

        # Check last two years of assignments
        if recipient in past_receiver.get(giver, [])[-2:]:
            logger.debug(f'{giver} already had {recipient} in the last 2 years')
            return False

    logger.debug(f'Pairings complete')
    return True


def generate_secret_santa(past_year_receiver: dict) -> dict:
    """
    Generates a valid Secret Santa assignment, ensuring no participant gets the same recipient they had
    in the last two years, and that no one is paired with themselves.

    Parameters:
        past_year_receiver (dict): A dictionary with participants as keys and a list of
                                      their recipients from the last few years as values.

    Returns:
        dict: A valid Secret Santa assignment where each giver (key) is assigned a recipient (value).
    """
    names = list(past_year_receiver.keys())
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
        if is_valid_pairing(candidate_assignment, past_year_receiver):
            assignment = candidate_assignment
            break

    return assignment


# Fetch past assignments from the database
def fetch_past_receiver() -> dict:
    """
    Fetch past receiver from the database and return them as a dictionary.

    Returns:
        dict: A dictionary where keys are participant names and values are lists of their past receiver.
    """
    participants = sql_statements.get_all_participants()
    past_assignments = {}

    for person_id, name in participants:
        # Get past receivers from the 'receiver' table for this person
        receivers = sql_statements.get_past_receivers_for_person(person_id)
        past_assignments[name] = receivers

    return past_assignments


# Store assignments into the database
def store_new_receiver(receiver: dict):
    """
    Store the new Secret Santa receiver in the database.

    Parameters:
        receiver (dict): The new receiver where keys are givers and values are recipients.
    """
    participants = sql_statements.get_all_participants()
    participant_dict = {name: person_id for person_id, name in participants}

    # Insert each new assignment into the 'receiver' table
    for giver, recipient in receiver.items():
        giver_id = participant_dict[giver]
        sql_statements.add_receiver(giver_id, recipient)


# Main logic
def main():
    # Populate the database with initial data if necessary
    participants_count = sql_statements.get_participants_count()

    # If there are no participants in the Person table, populate it with initial data
    if participants_count == 0:
        logger.info("Populating the database with initial data.")
        for name, receivers in past_year_assignments.items():
            sql_statements.add_name(name)
            person_id = sql_statements.get_person_id_by_name(name)

            # Store the past receivers for the person
            for receiver in receivers:
                sql_statements.add_receiver(person_id, receiver)

    # Fetch past assignments from the database
    past_receiver = fetch_past_receiver()

    # Generate new Secret Santa assignments
    new_receiver = generate_secret_santa(past_receiver)

    # Store the new assignments in the database
    store_new_receiver(new_receiver)

    # Output the result
    for giver, recipient in new_receiver.items():
        logger.info(f'{giver} -> {recipient}')


if __name__ == "__main__":
    main()
