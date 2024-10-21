import random
import logging
from typing import List, Dict, Any, Tuple

# Logging setup
_logic_logger = logging.getLogger(__name__)
_logic_logger.info('Logging setup complete')


def is_valid_pairing(assignments: dict, past_receivers: dict, participants: List[Dict[str, Any]]) -> bool:
    """
    Validates the current Secret Santa pairings. Ensures no one is paired
    with a recipient they had in the last two years or themselves.

    Parameters:
        assignments (dict): Mapping of givers to recipients (giver_id -> recipient_id).
        past_receivers (dict): Mapping of givers to their past recipients over the years (giver_id -> [recipient_name1, recipient_name2,...]).
        participants (List[Dict[str, Any]]): List of participant dictionaries with 'id' and 'name' keys.

    Returns:
        bool: True if pairings are valid, False otherwise.
    """
    for giver_id, recipient_id in assignments.items():
        if giver_id == recipient_id:
            return False
        
        # Get the recipient's name
        recipient_name = next((p['name'] for p in participants if p['id'] == recipient_id), None)
        
        if recipient_name in past_receivers.get(giver_id, []):
            return False
    return True


def generate_secret_santa(participants: List[Dict[str, Any]], sql_statements) -> List[Tuple[int, int]]:
    """
    Generates valid Secret Santa pairings, ensuring participants do not get the same recipient
    they had in the last two years and do not pair with themselves.

    Parameters:
        participants (List[Dict[str, Any]]): List of participant dictionaries with 'id' and 'name' keys.
        sql_statements (SqlStatements): Instance of SqlStatements to execute database queries.

    Returns:
        List[Tuple[int, int]]: List of (giver_id, receiver_id) tuples.
    """
    participant_ids = [p['id'] for p in participants]
    attempts = 1000

    # Fetch past receivers for all participants
    past_receivers = fetch_past_receivers(sql_statements)

    for _ in range(attempts):
        receiver_ids = random.sample(participant_ids, len(participant_ids))  # Shuffle IDs
        candidate_assignment = list(zip(participant_ids, receiver_ids))

        # Check if the assignment is valid
        if is_valid_pairing(dict(candidate_assignment), past_receivers, participants):
            _logic_logger.info(f'Successful Secret Santa pairings generated.')
            return candidate_assignment

    _logic_logger.error(f'Failed to generate valid Secret Santa pairings after {attempts} attempts.')
    raise ValueError("Unable to generate valid Secret Santa pairings after multiple attempts.")


def fetch_past_receivers(sql_statements) -> dict:
    """
    Retrieves past receiver data for each participant from the database.

    Parameters:
        sql_statements (SqlStatements): Instance of SqlStatements to execute database queries.

    Returns:
        dict: Mapping of participants' IDs to their list of past recipient IDs.
    """
    participants = sql_statements.get_all_participants()

    if not participants:
        _logic_logger.error("No participants found. Ensure participants exist in the database.")
        raise ValueError("No participants found")

    past_assignments = {}

    for participant in participants:
        person_id = participant['id']
        receivers = sql_statements.get_assignments_for_giver(person_id)

        if receivers is None:
            _logic_logger.debug(f'No receivers found for participant ID {person_id}, initializing empty list')
            past_assignments[person_id] = []
        else:
            # Collect the last two years of receiver names
            past_assignments[person_id] = [receiver['receiver_name'] for receiver in receivers][-2:]
            _logic_logger.debug(f'Fetched receivers for participant ID {person_id}: {past_assignments[person_id]}')

    return past_assignments


def store_new_receiver(receiver: dict, sql_statements, year: int):
    """
    Stores the new Secret Santa assignments into the database for the specified year.

    Parameters:
        receiver (dict): Mapping of givers' IDs to recipients' IDs (giver_id -> recipient_id).
        sql_statements (SqlStatements): Instance of SqlStatements for database interaction.
        year (int): The year of the Secret Santa assignment.
    """
    for giver_id, recipient_id in receiver.items():
        # Store the assignment
        sql_statements.add_or_assign_receiver(giver_id, recipient_id, year)
        _logic_logger.info(f'Assignment stored: giver ID {giver_id} -> recipient ID {recipient_id} for year {year}')
