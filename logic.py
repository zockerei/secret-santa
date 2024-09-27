import random
import logging
import sql

# Logging setup
_logic_logger = logging.getLogger(__name__)
_logic_logger.info('Logging setup complete')


# Function to check if the current pairing is valid
def is_valid_pairing(assignments: dict, past_receiver: dict) -> bool:
    """
    Checks if the current Secret Santa assignments are valid by ensuring that no one is
    paired with a recipient they had in the last two years.
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
    Generates a valid Secret Santa assignment, ensuring no participant gets the same recipient they had
    in the last two years, and that no one is paired with themselves.
    """
    names = list(past_year_receiver.keys())
    recipients = names[:]
    assignment = {}

    for _ in range(100):
        random.shuffle(recipients)
        candidate_assignment = {giver: recipient for giver, recipient in zip(names, recipients)}

        if any(giver == recipient for giver, recipient in candidate_assignment.items()):
            continue

        if is_valid_pairing(candidate_assignment, past_year_receiver):
            assignment = candidate_assignment
            break

    return assignment


# Fetch past assignments from the database
def fetch_past_receiver(sql_statements) -> dict:
    participants = sql_statements.get_all_participants()
    past_assignments = {}
    for person_id, name in participants:
        receivers = sql_statements.get_past_receivers_for_person(person_id)
        past_assignments[name] = receivers
    return past_assignments


# Store new assignments into the database
def store_new_receiver(receiver: dict, sql_statements):
    participants = sql_statements.get_all_participants()
    participant_dict = {name: person_id for person_id, name in participants}
    for giver, recipient in receiver.items():
        giver_id = participant_dict[giver]
        sql_statements.add_receiver(giver_id, recipient)

    past_receiver = fetch_past_receiver(sql_statements)
    new_receiver = generate_secret_santa(past_receiver)
    store_new_receiver(new_receiver, sql_statements)

    for giver, recipient in new_receiver.items():
        _logic_logger.info(f'{giver} -> {recipient}')
