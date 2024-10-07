import random
import logging

# Logging setup
_logic_logger = logging.getLogger(__name__)
_logic_logger.info('Logging setup complete')


# Function to check if the current pairing is valid
def is_valid_pairing(assignments: dict, past_receiver: dict) -> bool:
    """
    Check if the current Secret Santa pairings are valid by ensuring no one is paired
    with a recipient they had in the last two years.

    Parameters:
        assignments (dict): A dictionary where the key is the giver's name, and the value is the recipient's name.
        past_receiver (dict): A dictionary mapping givers' names to a list of recipients they had in past years.

    Returns:
        bool: True if the pairings are valid, False otherwise.
    """
    for giver, recipient in assignments.items():
        _logic_logger.debug(f'Checking {giver} with {recipient}')
        # Check last two years of assignments
        if recipient in past_receiver.get(giver, [])[-2:]:
            _logic_logger.debug(f'{giver} already had {recipient} in the last 2 years')
            return False
    return True


# Function to generate valid Secret Santa pairings
def generate_secret_santa(past_year_receiver: dict) -> dict:
    """
    Generate a valid Secret Santa assignment, ensuring no participant gets the same recipient
    they had in the last two years, and that no one is paired with themselves.

    Parameters:
        past_year_receiver (dict): A dictionary mapping participants' names to the list of their past recipients.

    Returns:
        dict: A valid Secret Santa assignment where each key is a giver, and the corresponding value is their recipient.
    """
    names = list(past_year_receiver.keys())
    recipients = names[:]
    assignment = {}

    for _ in range(100):
        random.shuffle(recipients)
        candidate_assignment = {giver: recipient for giver, recipient in zip(names, recipients)}

        # Ensure no one is paired with themselves
        if any(giver == recipient for giver, recipient in candidate_assignment.items()):
            continue

        # Check if the pairing is valid
        if is_valid_pairing(candidate_assignment, past_year_receiver):
            assignment = candidate_assignment
            break

    return assignment


# Fetch past assignments from the database
def fetch_past_receiver(sql_statements) -> dict:
    """
    Fetch past receiver data for each participant from the database.

    Parameters:
        sql_statements (SqlStatements): An instance of the SqlStatements class for executing SQL queries.

    Returns:
        dict: A dictionary where each key is a participant's name and the value is a list of past recipients they had.
    """
    participants = sql_statements.get_all_participants()
    past_assignments = {}
    for person_id, name, year in participants:
        receivers = sql_statements.get_receivers_for_participant(person_id)
        past_assignments[name] = receivers
    return past_assignments


def store_new_receiver(receiver: dict, sql_statements, year: int):
    """
    Store new Secret Santa assignments into the database.

    This function writes the new Secret Santa assignments to the database and logs the assignments.

    Parameters:
        receiver (dict): A dictionary where the keys are the givers and the values are the recipients.
        sql_statements: An instance of SqlStatements used to interact with the database.
        year (int): The year of the Secret Santa assignment.
    """
    participants = sql_statements.get_all_participants()
    participant_dict = {name: person_id for person_id, name in participants}

    # Store the new assignments in the database
    for giver, recipient in receiver.items():
        giver_id = participant_dict[giver]
        sql_statements.add_receiver(giver_id, recipient, year)  # Ensure to pass year to this method

    # Log the new Secret Santa assignments
    for giver, recipient in receiver.items():
        _logic_logger.info(f'{giver} -> {recipient} for year {year}')
