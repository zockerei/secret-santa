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


class Role(Enum):
    ADMIN = 'admin'
    PARTICIPANT = 'participant'


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
                conn.row_factory = sqlite3.Row  # Enables name-based access
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
        """Create tables for the Participant and Receiver database."""
        participant_table_script = """
            CREATE TABLE IF NOT EXISTS Participant (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            );
        """
        receiver_table_script = """
            CREATE TABLE IF NOT EXISTS Receiver (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                receiver_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                FOREIGN KEY (person_id) REFERENCES Participant(id)
            );
        """
        self._execute_query(
            participant_table_script,
            'Participant table created',
            'Failed to create Participant table'
        )
        self._execute_query(
            receiver_table_script,
            'Receiver table created',
            'Failed to create Receiver table'
        )

    def add_participant(self, name: str, password: str, role: Role = Role.PARTICIPANT):
        """
        Add a participant to the participants table.

        Parameters:
            name (str): The name of the participant to add.
            password (str): The plain-text password to hash and store.
            role (Role): The role of the participant, either Role.ADMIN or Role.PARTICIPANT.
            Default is Role.PARTICIPANT.
        """
        # Check if the participant already exists (case-insensitive)
        existing_participant = self.get_participant_id(name)
        if existing_participant:
            raise ValueError(f"Participant '{name}' already exists.")

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')  # Convert to string
        insert_query = """
            INSERT INTO Participant (name, password, role)
            VALUES (:name, :password, :role)
        """
        self._execute_query(
            insert_query,
            f'Added participant "{name}" with role "{role.value}"',
            f'Failed to add participant "{name}"',
            {'name': name, 'password': hashed, 'role': role.value}
        )

    def add_receiver(self, person_id: int, receiver_name: str, year: int):
        """
        Add a receiver's name to the receiver table for a specific participant.

        Parameters:
            person_id (int): The ID of the participant in the Participant table.
            receiver_name (str): The name of the receiver to add for the participant.
            year (int): The year for the assignment.
        """
        insert_query = """
            INSERT INTO Receiver (person_id, receiver_name, year) 
            VALUES (:person_id, :receiver_name, :year)
        """
        self._execute_query(
            insert_query,
            f'Receiver "{receiver_name}" added for participant with ID {person_id} for year {year}',
            f'Failed to add receiver "{receiver_name}" for participant with ID {person_id} for year {year}',
            {'person_id': person_id, 'receiver_name': receiver_name, 'year': year}
        )

    def remove_participant(self, person_id: int):
        """
        Remove a participant from the database along with their receivers.

        Parameters:
            person_id (int): The ID of the participant to remove.
        """
        # Remove all receivers associated with the participant
        self._execute_query(
            "DELETE FROM Receiver WHERE person_id = :person_id",
            f'Removed receivers for participant {person_id}',
            'Failed to remove receivers',
            {'person_id': person_id}
        )
        # Remove the participant
        self._execute_query(
            "DELETE FROM Participant WHERE id = :person_id",
            f'Removed participant {person_id}',
            'Failed to remove participant',
            {'person_id': person_id}
        )

    def remove_receiver(self, person_id: int, receiver_name: str, year: int):
        """
        Remove a specific receiver for a participant for a given year.

        Parameters:
            person_id (int): The ID of the participant.
            receiver_name (str): The name of the receiver to remove.
            year (int): The year of the receiver assignment.
        """
        query = """
            DELETE FROM Receiver
            WHERE person_id = :person_id
            AND receiver_name = :receiver_name
            AND year = :year
        """
        self._execute_query(
            query,
            f'Removed receiver "{receiver_name}" for participant {person_id} for year {year}',
            'Failed to remove receiver',
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
            SELECT password FROM Participant WHERE name = :name
        """
        result = self._execute_query(
            query,
            f'Password fetched for participant "{name}"',
            f'Failed to fetch password for participant "{name}"',
            {'name': name},
            fetch_one=True
        )
        if result and result['password']:
            stored_password = result['password']  # This is a string
            return bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8'))
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

    def get_role(self, name: str) -> Optional[Role]:
        """
        Get the role (admin or participant) for a given participant by name.

        Parameters:
            name (str): The name of the participant.

        Returns:
            Optional[Role]: The role of the participant if found, or None if not found.
        """
        query = """
            SELECT role FROM Participant WHERE name = :name
        """
        try:
            result = self._execute_query(
                query,
                f'Role fetched for participant "{name}"',
                f'Failed to fetch role for participant "{name}"',
                {'name': name},
                fetch_one=True
            )
            if result:
                role_str = result['role']
                return Role(role_str) if role_str in Role.value2member_map_ else None
            return None
        except DatabaseError:
            return None

    def get_all_participants(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch all participants from the Participant table excluding admins.

        Returns:
            Optional[List[Dict[str, Any]]]: A list of dictionaries where each dictionary contains the ID,
            name, and role of a participant.
        """
        query = "SELECT id, name, role FROM Participant WHERE role != :admin_role"
        try:
            results = self._execute_query(
                query,
                'Fetched participants',
                'Failed to fetch participants',
                {'admin_role': Role.ADMIN.value}
            )
            if results:
                return self._convert_rows_to_dicts(results)
            return None
        except DatabaseError:
            return None

    def get_receivers_for_participant(self, person_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch all past receivers for a participant, including the year.

        Parameters:
            person_id (int): The ID of the participant.

        Returns:
            Optional[List[Dict[str, Any]]]: A list of dictionaries containing receiver names and years,
            or None on failure.
        """
        query = """
            SELECT receiver_name, year FROM Receiver WHERE person_id = :person_id
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

    def get_current_receiver(self, person_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch the receiver for the participant for the current year.

        Parameters:
            person_id (int): The ID of the participant.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the receiver's name and year if found,
            or None if not found.
        """
        current_year = datetime.datetime.now().year  # Get the current year
        query = """
            SELECT receiver_name, year FROM Receiver
            WHERE person_id = :person_id AND year = :current_year
        """
        try:
            result = self._execute_query(
                query,
                f'Fetched current receiver for participant {person_id} for year {current_year}',
                f'Failed to fetch current receiver for participant {person_id} for year {current_year}',
                {'person_id': person_id, 'current_year': current_year},
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
        query = "SELECT id FROM Participant WHERE name = :name"
        try:
            result = self._execute_query(
                query,
                f'Fetched person_id for {name}',
                'Failed to fetch person_id',
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
        query = "SELECT id, name, role FROM Participant WHERE id = :person_id"
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

    def update_participant(self, person_id: int, name: str, password: str):
        """
        Update a participant's details in the database.

        Parameters:
            person_id (int): The ID of the participant to update.
            name (str): The new name of the participant.
            password (str): The new password of the participant.
        """
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')  # Convert to string
        update_query = """
            UPDATE Participant
            SET name = :name, password = :password
            WHERE id = :person_id
        """
        try:
            self._execute_query(
                update_query,
                f'Updated participant "{name}" with ID {person_id}',
                f'Failed to update participant with ID {person_id}',
                {'name': name, 'password': hashed, 'person_id': person_id}
            )
        except DatabaseError:
            pass
