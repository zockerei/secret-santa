import datetime
import logging
import sqlite3
from typing import Optional, List, Dict, Any, Union
import bcrypt
from enum import Enum


class DatabaseError(Exception):
    """
    Custom exception for database-related errors.

    Attributes:
        message (str): Explanation of the error.
        original_exception (Exception): The original exception that caused the error, if any.
    """
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        """
        Initialize the DatabaseError exception with a message and an optional original exception.

        Parameters:
            message (str): Explanation of the error.
            original_exception (Optional[Exception]): The original exception that caused the error.
        """
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)

    def log_error(self, logger: logging.Logger):
        """
        Log the error message and details of the original exception if available.

        Parameters:
            logger (logging.Logger): The logger to use for logging the error.
        """
        if self.original_exception:
            logger.error(f'{self.message}: {self.original_exception}')
        else:
            logger.error(self.message)

class SqlStatements:
    """
    Class containing SQL statements and methods to interact with the SQLite database.
    """
    _sql_logger = logging.getLogger(__name__)
    _sql_logger.info('Logging setup complete')

    def __init__(self, db_path: str):
        """
        Initialize the SqlStatements object with the path to the database.

        Parameters:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path

    @staticmethod
    def _convert_rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
        """
        Convert a list of sqlite3.Row objects to a list of dictionaries.

        Parameters:
            rows (List[sqlite3.Row]): The rows fetched from the database.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing each row.
        """
        return [dict(row) for row in rows]

    def _execute_query(
        self,
        query: str,
        success_message: str,
        error_message: str,
        params: Optional[Dict[str, Any]] = None,
        fetch_one: bool = False
    ) -> Optional[Union[sqlite3.Row, List[sqlite3.Row]]]:
        """
        Execute a SQL query and return the result if applicable.

        Raises:
            DatabaseError: If the query execution fails.

        Parameters:
            query (str): The SQL query to execute.
            success_message (str): Message to log upon successful execution.
            error_message (str): Message to log if an error occurs.
            params (Optional[Dict[str, Any]]): Parameters for the query.
            fetch_one (bool): Whether to fetch only one result or all.

        Returns:
            Optional[Union[sqlite3.Row, List[sqlite3.Row]]]: Query result or None on error.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params or {})
                result = cursor.fetchone() if fetch_one else cursor.fetchall()
                conn.commit()
            self._sql_logger.info(success_message)
            return result
        except sqlite3.Error as error:
            self._sql_logger.error(f'{error_message}: {error}')
            raise DatabaseError(f'{error_message}: {error}') from error

    def create_tables(self):
        """Create tables for the Participants, Past Receivers, Messages, and Assignments database."""
        participants_table_script = """
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL, 
                password TEXT NOT NULL,
                wishlist TEXT,
                admin BOOLEAN DEFAULT 0
            );
        """
        past_receivers_table_script = """
            CREATE TABLE IF NOT EXISTS past_receivers (
                participant_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                FOREIGN KEY (participant_id) REFERENCES participants(id),
                FOREIGN KEY (receiver_id) REFERENCES participants(id)
            );
        """
        messages_table_script = """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                year INTEGER NOT NULL,
                FOREIGN KEY (participant_id) REFERENCES participants(id)
            );
        """
        assignments_table_script = """
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                giver_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                message_id INTEGER,
                year INTEGER NOT NULL,
                FOREIGN KEY (giver_id) REFERENCES participants(id),
                FOREIGN KEY (receiver_id) REFERENCES participants(id),
                FOREIGN KEY (message_id) REFERENCES messages(id)
            );
        """
        self._execute_query(
            participants_table_script,
            'Participants table created',
            'Failed to create Participants table'
        )
        self._execute_query(
            past_receivers_table_script,
            'Past Receivers table created',
            'Failed to create Past Receivers table'
        )
        self._execute_query(
            messages_table_script,
            'Messages table created',
            'Failed to create Messages table'
        )
        self._execute_query(
            assignments_table_script,
            'Assignments table created',
            'Failed to create Assignments table'
        )

    def add_participant(self, name: str, password: str, role: str = "participant"):
        """
        Add a new participant to the database with a hashed password.

        Parameters:
            name (str): The name and username of the participant.
            password (str): The plain-text password of the participant.
            role (str): The role of the participant (default is 'participant').
        """
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')  # Decode to string
        insert_query = """
            INSERT INTO participants (name, password, admin)
            VALUES (:name, :password, :admin)
        """
        self._execute_query(
            insert_query,
            f'Participant "{name}" added with role {role}',
            f'Failed to add participant "{name}" with role {role}',
            {'name': name, 'password': hashed, 'admin': role == 'admin'}
        )

    def add_receiver(self, participant_id: int, receiver_id: int, year: int):
        """
        Add a receiver to the past_receivers table for a specific participant.

        Parameters:
            participant_id (int): The ID of the participant in the participants table.
            receiver_id (int): The ID of the receiver to add for the participant.
            year (int): The year for the assignment.
        """
        # First, check if the receiver is already assigned to any participant for this year
        check_query = """
            SELECT participant_id FROM past_receivers 
            WHERE receiver_id = :receiver_id AND year = :year
        """
        result = self._execute_query(
            check_query,
            f'Checked for existing assignment for receiver {receiver_id} in year {year}',
            f'Failed to check for existing assignment for receiver {receiver_id} in year {year}',
            {'receiver_id': receiver_id, 'year': year},
            fetch_one=True
        )

        if result:
            existing_participant_id = result['participant_id']
            raise DatabaseError(f'Receiver {receiver_id} is already assigned to participant {existing_participant_id} for year {year}')

        # If no existing assignment, proceed with insertion
        insert_query = """
            INSERT INTO past_receivers (participant_id, receiver_id, year) 
            VALUES (:participant_id, :receiver_id, :year)
        """
        self._execute_query(
            insert_query,
            f'Receiver with ID {receiver_id} added for participant with ID {participant_id} for year {year}',
            f'Failed to add receiver with ID {receiver_id} for participant with ID {participant_id} for year {year}',
            {'participant_id': participant_id, 'receiver_id': receiver_id, 'year': year}
        )

    def add_message(self, participant_id: int, message_text: str, year: int):
        """
        Add a new message from a participant to the database.

        Parameters:
            participant_id (int): The ID of the participant writing the message.
            message_text (str): The message text written by the participant.
            year (int): The year for the message.

        Raises:
            DatabaseError: If the query execution fails.
        """
        insert_query = """
            INSERT INTO messages (participant_id, message, year)
            VALUES (:participant_id, :message, :year)
        """
        self._execute_query(
            insert_query,
            success_message='Message added to the database',
            error_message='Failed to add message to the database',
            params={'participant_id': participant_id, 'message': message_text, 'year': year}
        )

    def assign_receiver(self, giver_id: int, receiver_id: int, message_id: Optional[int], year: int):
        """
        Create an assignment between a giver and a receiver.

        Parameters:
            giver_id (int): The ID of the participant giving the gift.
            receiver_id (int): The ID of the participant receiving the gift.
            message_id (Optional[int]): The ID of the associated message, if any.
            year (int): The year of the assignment.

        Raises:
            DatabaseError: If the query execution fails.
        """
        insert_query = """
            INSERT INTO assignments (giver_id, receiver_id, message_id, year)
            VALUES (:giver_id, :receiver_id, :message_id, :year)
        """
        self._execute_query(
            insert_query,
            success_message=f'Assignment created for giver {giver_id} and receiver {receiver_id}',
            error_message=f'Failed to create assignment for giver {giver_id} and receiver {receiver_id}',
            params={'giver_id': giver_id, 'receiver_id': receiver_id, 'message_id': message_id, 'year': year}
        )

    def remove_participant(self, participant_id: int):
        """
        Remove a participant from the database along with their past receivers.

        Parameters:
            participant_id (int): The ID of the participant to remove.
        """
        # Remove all past receivers associated with the participant
        self._execute_query(
            "DELETE FROM past_receivers WHERE participant_id = :participant_id",
            f'Removed past receivers for participant {participant_id}',
            'Failed to remove past receivers',
            {'participant_id': participant_id}
        )
        # Remove the participant
        self._execute_query(
            "DELETE FROM participants WHERE id = :participant_id",
            f'Removed participant {participant_id}',
            'Failed to remove participant',
            {'participant_id': participant_id}
        )

    def remove_receiver(self, person_id: int, receiver_name: str, year: int):
        """
        Remove a specific receiver for a participant for a given year from both past_receivers and assignments tables.

        Parameters:
            person_id (int): The ID of the participant.
            receiver_name (str): The name of the receiver to remove.
            year (int): The year of the receiver assignment.
        """
        # First, try to remove from past_receivers table
        query_past_receivers = """
            DELETE FROM past_receivers
            WHERE participant_id = :person_id
            AND receiver_id = (SELECT id FROM participants WHERE name = :receiver_name)
            AND year = :year
        """
        self._execute_query(
            query_past_receivers,
            f'Attempted to remove receiver "{receiver_name}" for participant {person_id} for year {year} from past_receivers',
            'Failed to remove receiver from past_receivers',
            {'person_id': person_id, 'receiver_name': receiver_name, 'year': year}
        )

        # Then, try to remove from assignments table
        query_assignments = """
            DELETE FROM assignments
            WHERE giver_id = :person_id
            AND receiver_id = (SELECT id FROM participants WHERE name = :receiver_name)
            AND year = :year
        """
        self._execute_query(
            query_assignments,
            f'Attempted to remove receiver "{receiver_name}" for participant {person_id} for year {year} from assignments',
            'Failed to remove receiver from assignments',
            {'person_id': person_id, 'receiver_name': receiver_name, 'year': year}
        )

    def verify_participant(self, name: str, password: str) -> bool:
        """
        Verify if a participant's name and password match a record in the participants table.

        Parameters:
            name (str): The name of the participant.
            password (str): The plain-text password to verify.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        query = """
            SELECT password FROM participants WHERE name = :name
        """
        result = self._execute_query(
            query,
            'Fetched password for participant',
            'Failed to fetch password for participant',
            {'name': name},
            fetch_one=True
        )
        if result and result['password']:
            stored_password = result['password']  # This should be bytes or str based on storage
            if isinstance(stored_password, str):
                stored_password = stored_password.encode('utf-8')  # Encode to bytes if stored as string
            is_match = bcrypt.checkpw(password.encode('utf-8'), stored_password)
            self._sql_logger.info(f'Password match for user "{name}": {is_match}')
            return is_match
        return False

    def is_participant(self, receiver_name: str, person_id: int) -> bool:
        """
        Check if a receiver is an existing participant in the system and ensure that
        the participant is not adding themselves as the receiver.

        Parameters:
            receiver_name (str): The name of the receiver.
            person_id (int): The ID of the participant trying to add the receiver.

        Returns:
            bool: True if the receiver exists and is not the same as the participant, False otherwise.
        """
        query = """
            SELECT 1 FROM Participant WHERE name = :receiver_name AND id != :person_id LIMIT 1
        """
        try:
            result = self._execute_query(
                query,
                f'Checked if "{receiver_name}" is a participant and not the same as the participant',
                f'Failed to check if "{receiver_name}" is a participant or is the same as the participant',
                {'receiver_name': receiver_name, 'person_id': person_id},
                fetch_one=True
            )
            return result is not None
        except DatabaseError:
            return False

    def check_duplicate_receiver(self, person_id: int, year: int) -> bool:
        """
        Check if a receiver for the given person_id already exists for the specified year.

        Parameters:
            person_id (int): The ID of the participant.
            year (int): The year to check for duplicates.

        Returns:
            bool: True if a duplicate receiver exists, False otherwise.
        """
        query = """
            SELECT COUNT(*) AS count FROM Receiver WHERE person_id = :person_id AND year = :year
        """
        try:
            result = self._execute_query(
                query,
                f'Checked for duplicate receiver for person_id {person_id} and year {year}',
                f'Error checking for duplicate receiver for person_id {person_id} and year {year}',
                {'person_id': person_id, 'year': year},
                fetch_one=True
            )
            return bool(result and result['count'] > 0)
        except DatabaseError:
            return False

    def get_messages_for_participant(self, participant_id: int, year: int) -> List[sqlite3.Row]:
        """
        Retrieve all messages written by the participant for a specific year.

        Parameters:
            participant_id (int): The ID of the participant whose messages to retrieve.
            year (int): The year for which to retrieve messages.

        Returns:
            List[sqlite3.Row]: A list of messages written by the participant.

        Raises:
            DatabaseError: If the query execution fails.
        """
        select_query = """
            SELECT id, message, year
            FROM messages
            WHERE participant_id = :participant_id AND year = :year
        """
        return self._execute_query(
            select_query,
            success_message=f'Fetched messages for participant {participant_id} for year {year}',
            error_message=f'Failed to fetch messages for participant {participant_id} for year {year}',
            params={'participant_id': participant_id, 'year': year}
        )

    def get_role(self, name: str) -> Optional[str]:
        """
        Get the role of a participant by name.

        Parameters:
            name (str): The name of the participant.

        Returns:
            Optional[str]: 'admin' if the participant is an admin, 'participant' otherwise.
        """
        query = """
            SELECT admin FROM participants WHERE name = :name
        """
        result = self._execute_query(
            query,
            f'Fetched role for participant "{name}".',
            f'Failed to fetch role for participant "{name}".',
            {'name': name},
            fetch_one=True
        )
        if result is not None:
            return 'admin' if result['admin'] else 'participant'
        return None

    def get_all_participants(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch all participants from the participants table excluding admins.

        Returns:
            Optional[List[Dict[str, Any]]]: A list of dictionaries where each dictionary contains the ID
            and name of a participant.
        """
        query = "SELECT id, name FROM participants WHERE admin = 0"
        try:
            results = self._execute_query(
                query,
                'Fetched participants',
                'Failed to fetch participants'
            )
            if results:
                return [dict(row) for row in results]
            return []
        except DatabaseError:
            return []

    def get_receivers_for_participant(self, person_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch all past receivers for a participant, including the year, from both past_receivers and assignments tables.
        """
        query = """
            SELECT p.name AS receiver_name, pr.year
            FROM (
                SELECT participant_id, receiver_id, year FROM past_receivers
                UNION ALL
                SELECT giver_id AS participant_id, receiver_id, year FROM assignments
            ) pr
            JOIN participants p ON pr.receiver_id = p.id
            WHERE pr.participant_id = :person_id
            ORDER BY pr.year DESC
        """
        try:
            results = self._execute_query(
                query,
                f'Fetched receivers for participant {person_id}',
                f'Failed to fetch receivers for participant {person_id}',
                {'person_id': person_id}
            )
            if results:
                return self._convert_rows_to_dicts(results)
            return None
        except DatabaseError:
            return None

    def get_participants_count(self) -> int:
        """
        Count the number of participants in the Participant table.

        Returns:
            int: The total number of participants in the Participant table.
        """
        query = "SELECT COUNT(*) AS count FROM Participant"
        try:
            result = self._execute_query(
                query,
                'Checked participants count',
                'Failed to get participants count',
                fetch_one=True
            )
            return result['count'] if result and 'count' in result else 0
        except DatabaseError:
            return 0

    def get_current_receiver(self, giver_id: int, year: int) -> Optional[Dict[str, Any]]:
        """
        Fetch the receiver for the participant for the specified year.

        Parameters:
            giver_id (int): The ID of the participant giving the gift.
            year (int): The year to check for the assignment.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the receiver's details if found,
            or None if not found.
        """
        query = """
            SELECT p.id, p.name, a.message_id
            FROM assignments a
            JOIN participants p ON a.receiver_id = p.id
            WHERE a.giver_id = :giver_id AND a.year = :year
        """
        try:
            result = self._execute_query(
                query,
                f'Fetched current receiver for giver {giver_id} for year {year}',
                f'Failed to fetch current receiver for giver {giver_id} for year {year}',
                {'giver_id': giver_id, 'year': year},
                fetch_one=True
            )
            if result:
                return dict(result)
            return None
        except DatabaseError:
            return None

    def get_participant_id(self, name: str) -> Optional[int]:
        """
        Fetch the ID of a participant by their name.

        Parameters:
            name (str): The name of the participant.

        Returns:
            Optional[int]: The ID of the participant, or None if not found.
        """
        query = "SELECT id FROM participants WHERE name = :name"
        try:
            result = self._execute_query(
                query,
                f'Fetched participant ID for {name}',
                'Failed to fetch participant ID',
                {'name': name},
                fetch_one=True
            )
            if result:
                return result['id']
            return None
        except DatabaseError:
            return None

    def get_participant_by_id(self, person_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a participant by their ID.

        Parameters:
            person_id (int): The participant's ID.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the participant's details or None if not found.
        """
        query = "SELECT id, name, admin FROM participants WHERE id = :person_id"
        try:
            result = self._execute_query(
                query,
                f'Fetched participant with ID {person_id}',
                f'Failed to fetch participant with ID {person_id}',
                {'person_id': person_id},
                fetch_one=True
            )
            if result:
                return dict(result)
            return None
        except DatabaseError:
            return None

    def update_participant(self, participant_id: int, name: str, password: str):
        """
        Update a participant's details in the database.

        Parameters:
            participant_id (int): The ID of the participant to update.
            name (str): The new name and username of the participant.
            password (str): The new password of the participant.
        """
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')  # Convert to string
        update_query = """
            UPDATE participants
            SET name = :name, password = :password
            WHERE id = :participant_id
        """
        try:
            self._execute_query(
                update_query,
                f'Updated participant "{name}" with ID {participant_id}',
                f'Failed to update participant with ID {participant_id}',
                {'name': name, 'password': hashed, 'participant_id': participant_id}
            )
        except DatabaseError:
            pass

    def admin_exists(self) -> bool:
        """
        Check if an admin user exists in the participants table.

        Returns:
            bool: True if an admin exists, False otherwise.
        """
        query = "SELECT 1 FROM participants WHERE admin = 1 LIMIT 1"
        try:
            result = self._execute_query(
                query,
                'Checked for existing admin user',
                'Failed to check for existing admin user',
                fetch_one=True
            )
            return result is not None
        except DatabaseError:
            return False

    def update_participant_name(self, participant_id: int, name: str):
        """
        Update a participant's name in the database.

        Parameters:
            participant_id (int): The ID of the participant to update.
            name (str): The new name of the participant.
        """
        update_query = """
            UPDATE participants
            SET name = :name
            WHERE id = :participant_id
        """
        try:
            self._execute_query(
                update_query,
                f'Updated participant name to "{name}" with ID {participant_id}',
                f'Failed to update participant name with ID {participant_id}',
                {'name': name, 'participant_id': participant_id}
            )
        except DatabaseError:
            pass

    def get_message_by_id(self, message_id: int, participant_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a message by its ID and participant ID.

        Parameters:
            message_id (int): The ID of the message.
            participant_id (int): The ID of the participant who wrote the message.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the message details or None if not found.
        """
        query = """
            SELECT id, message, year
            FROM messages
            WHERE id = :message_id AND participant_id = :participant_id
        """
        try:
            result = self._execute_query(
                query,
                f'Fetched message with ID {message_id} for participant {participant_id}',
                f'Failed to fetch message with ID {message_id} for participant {participant_id}',
                {'message_id': message_id, 'participant_id': participant_id},
                fetch_one=True
            )
            if result:
                return dict(result)
            return None
        except DatabaseError:
            return None

    def update_message(self, message_id: int, new_message_text: str):
        """
        Update a message's text in the database.

        Parameters:
            message_id (int): The ID of the message to update.
            new_message_text (str): The new text for the message.
        """
        update_query = """
            UPDATE messages
            SET message = :new_message_text
            WHERE id = :message_id
        """
        try:
            self._execute_query(
                update_query,
                f'Updated message with ID {message_id}',
                f'Failed to update message with ID {message_id}',
                {'new_message_text': new_message_text, 'message_id': message_id}
            )
        except DatabaseError:
            pass

    def delete_message(self, message_id: int):
        """
        Delete a message from the database.

        Parameters:
            message_id (int): The ID of the message to delete.
        """
        delete_query = """
            DELETE FROM messages
            WHERE id = :message_id
        """
        try:
            self._execute_query(
                delete_query,
                f'Deleted message with ID {message_id}',
                f'Failed to delete message with ID {message_id}',
                {'message_id': message_id}
            )
        except DatabaseError:
            pass

    def get_message_for_year(self, participant_id: int, year: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a message for a specific participant and year.

        Parameters:
            participant_id (int): The ID of the participant.
            year (int): The year for which to fetch the message.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the message details or None if not found.
        """
        query = """
            SELECT id, message, year
            FROM messages
            WHERE participant_id = :participant_id AND year = :year
            LIMIT 1
        """
        try:
            result = self._execute_query(
                query,
                f'Fetched message for participant {participant_id} and year {year}',
                f'Failed to fetch message for participant {participant_id} and year {year}',
                {'participant_id': participant_id, 'year': year},
                fetch_one=True
            )
            if result:
                return dict(result)
            return None
        except DatabaseError:
            return None
