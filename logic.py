import random
import logging

# Logging setup
_logic_logger = logging.getLogger(__name__)
_logic_logger.info('Logging setup complete')


def is_valid_pairing(assignments: dict, past_receiver: dict) -> bool:
    """
    Validates the current Secret Santa pairings. Ensures no one is paired
    with a recipient they had in the last two years.

    Parameters:
        assignments (dict): Mapping of givers to recipients (giver -> recipient).
        past_receiver (dict): Mapping of givers to their past recipients over the years (giver -> [recipient1, recipient2,...]).

    Returns:
        bool: True if pairings are valid, False otherwise.
    """
    for giver, recipient in assignments.items():
        _logic_logger.debug(f'Validating pairing: {giver} -> {recipient}')
        if recipient in past_receiver.get(giver, [])[-2:]:
            _logic_logger.debug(f'Invalid pairing: {giver} had {recipient} in the last 2 years')
            return False
    return True


def generate_secret_santa(past_year_receiver: dict) -> dict:
    """
    Generates valid Secret Santa pairings, ensuring participants do not get the same recipient
    they had in the last two years and do not pair with themselves.

    Parameters:
        past_year_receiver (dict): Mapping of givers to the list of their past recipients.

    Returns:
        dict: Valid Secret Santa pairings (giver -> recipient).
    """
    names = list(past_year_receiver.keys())
    attempts = 100

    for _ in range(attempts):
        recipients = random.sample(names, len(names))  # Shuffle names into recipients
        candidate_assignment = {giver: recipient for giver, recipient in zip(names, recipients)}

        # Ensure no one is paired with themselves
        if all(giver != recipient for giver, recipient in candidate_assignment.items()):
            if is_valid_pairing(candidate_assignment, past_year_receiver):
                _logic_logger.info(f'Successful Secret Santa pairings generated.')
                return candidate_assignment

    _logic_logger.error(f'Failed to generate valid Secret Santa pairings after {attempts} attempts.')
    raise ValueError("Unable to generate valid Secret Santa pairings after multiple attempts.")


def fetch_past_receiver(sql_statements) -> dict:
    """
    Retrieves past receiver data for each participant from the database.

    Parameters:
        sql_statements (SqlStatements): Instance of SqlStatements to execute database queries.

    Returns:
        dict: Mapping of participants' names to their list of past recipients.
    """
    participants = sql_statements.get_all_participants()

    # Check if participants is None or empty
    if not participants:
        _logic_logger.error("No participants found. Ensure participants exist in the database.")
        raise ValueError("No participants found")

    past_assignments = {}

    for participant in participants:
        person_id = participant['id']
        name = participant['name']

        # Fetch receivers for the participant
        receivers = sql_statements.get_receivers_for_participant(person_id)

        # Ensure receivers is not None, initialize with empty list if needed
        if receivers is None:
            _logic_logger.debug(f'No receivers found for {name}, initializing empty list')
            past_assignments[name] = []
        else:
            # Extract the receiver names
            past_assignments[name] = [receiver['receiver_name'] for receiver in receivers]
            _logic_logger.debug(f'Fetched receivers for {name}: {past_assignments[name]}')

    return past_assignments


def store_new_receiver(receiver: dict, sql_statements, year: int):
    """
    Stores the new Secret Santa assignments into the database for the specified year.

    Parameters:
        receiver (dict): Mapping of givers to recipients (giver -> recipient).
        sql_statements (SqlStatements): Instance of SqlStatements for database interaction.
        year (int): The year of the Secret Santa assignment.
    """
    participants = sql_statements.get_all_participants()
    participant_dict = {participant['name']: participant['id'] for participant in participants}
    _logic_logger.debug(f'{participant_dict}')

    for giver, recipient in receiver.items():
        giver_id = participant_dict.get(giver)
        if giver_id is None:
            _logic_logger.error(f'Giver {giver} not found in participant dictionary.')
            raise ValueError(f"Giver {giver} not found in participant list.")

        recipient_id = participant_dict.get(recipient)
        if recipient_id is None:
            _logic_logger.error(f'Recipient {recipient} not found in participant dictionary.')
            raise ValueError(f"Recipient {recipient} not found in participant list.")

        # Store the assignment
        sql_statements.add_receiver(giver_id, recipient, year)
        _logic_logger.info(f'Assignment stored: {giver} -> {recipient} for year {year}')

