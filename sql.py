import logging
import sqlite3
from typing import Optional, List, Tuple, Dict, Any
import bcrypt


class SqlStatements:
    """
    Class containing SQL statements and methods.
    """
    # Logging setup
    _sql_logger = logging.getLogger(__name__)
    _sql_logger.info('Logging setup complete')

    def __init__(self, db_path):
        """
        Initialize the SqlStatements object with the path to the database.

        Parameters:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path
        self._sqlite_connection = None
        self.cursor = None

    def _connect(self):
        """
        Establishes a connection to the SQLite database and sets up the cursor.
        """
        try:
            self._sqlite_connection = sqlite3.connect(self.db_path)
            self.cursor = self._sqlite_connection.cursor()
            self._sql_logger.debug(f'Connected to database at {self.db_path}')
        except sqlite3.Error as error:
            self._sql_logger.error(f'Failed to connect to database: {error}')
            raise error

    def _disconnect(self):
        """
        Closes the SQLite connection and cursor.
        """
        if self.cursor:
            self.cursor.close()
        if self._sqlite_connection:
            self._sqlite_connection.close()
            self._sql_logger.debug('Disconnected from database')

    def _execute_query(
            self,
            query: str,
            success_message: str = 'Success',
            error_message: str = 'Error',
            params: Optional[Dict[str, Any]] = None,
            fetch_one: bool = False
    ) -> Optional[List[Tuple]]:
        """
        Execute a SQL query and return the result if applicable.

        Parameters:
            query (str): The SQL query to execute.
            success_message (str): Message to log upon successful execution.
            error_message (str): Message to log if an error occurs.
            params (Optional[Dict[str, Any]]): Dictionary of parameters to pass to the query.
            fetch_one (bool): Whether to fetch only one result (True) or all results (False).

        Returns:
            Optional[List[Tuple]]: Result of the query if applicable, or None if an error occurs.
        """
        try:
            self._connect()
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            if fetch_one:
                result = self.cursor.fetchone()
            else:
                result = self.cursor.fetchall()

            self._sqlite_connection.commit()
            self._sql_logger.info(success_message)
            if result:
                self._sql_logger.debug(f'Result: {result}')
            return result

        except sqlite3.Error as error:
            self._sql_logger.error(f'{error_message}: {error}')
            return None

        finally:
            self._disconnect()

    def create_tables(self):
        """ Create tables for the Participant and receiver database. """
        participant_table_script = """
            CREATE TABLE IF NOT EXISTS Participant (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,  -- Ensure unique and case-insensitive
                password TEXT NOT NULL,
                role TEXT NOT NULL -- "admin" or "participant"
            );
        """
        self._execute_query(
            participant_table_script,
            'Participant table created',
            'Failed to create Participant table'
        )

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
            receiver_table_script,
            'Receiver table created',
            'Failed to create receiver table'
        )

    def add_participant(self, name: str, password: str, role: str = 'participant'):
        """
        Add a participant to the participants table.

        Parameters:
            name (str): The name of the participant to add.
            password (str): The plain-text password to hash and store.
            role (str): The role of the participant, either 'admin' or 'participant'. Default is 'participant'.
        """
        # Check if the participant already exists (case-insensitive)
        existing_participant = self.get_participant_id(name)
        if existing_participant:
            raise ValueError(f"Participant '{name}' already exists.")

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        insert_query = """
            INSERT INTO Participant (name, password, role)
            VALUES (:name, :password, :role)
        """
        self._execute_query(
            insert_query,
            f'Added participant "{name}" with role "{role}"',
            f'Failed to add participant "{name}"',
            {'name': name, 'password': hashed, 'role': role}
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
            INSERT INTO receiver (person_id, receiver_name, year) 
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
        Remove a participant from the Participant table and associated receivers.

        Parameters:
            person_id (int): The ID of the participant to remove.
        """
        # Remove associated receivers first to maintain referential integrity
        delete_receivers_query = """
            DELETE FROM receiver WHERE person_id = :person_id
        """
        self._execute_query(
            delete_receivers_query,
            f'Removed receivers for participant_id {person_id}',
            f'Failed to remove receivers for participant_id {person_id}',
            {'person_id': person_id}
        )

        # Now remove the participant from the Participant table
        delete_person_query = """
            DELETE FROM Participant WHERE id = :person_id
        """
        self._execute_query(
            delete_person_query,
            f'Removed participant with ID {person_id} from Participant table',
            f'Failed to remove participant with ID {person_id}',
            {'person_id': person_id}
        )

    def remove_receiver(self, person_id: int, receiver_name: str, year: int):
        """
        Remove a specific receiver for a given participant from the receiver table.

        Parameters:
            person_id (int): The ID of the participant whose receiver should be removed.
            receiver_name (str): The name of the receiver to remove.
            year (int): The year of the receiver assignment.
        """
        delete_receiver_query = """
            DELETE FROM receiver WHERE person_id = :person_id AND receiver_name = :receiver_name AND year = :year
        """
        self._execute_query(
            delete_receiver_query,
            f'Removed receiver "{receiver_name}" for participant_id {person_id} for year {year}',
            f'Failed to remove receiver "{receiver_name}" for participant_id {person_id} for year {year}',
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
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0]):
            return True
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
        result = self._execute_query(
            query,
            success_message=f'Checked if "{receiver_name}" is a participant and not the same as the participant',
            error_message=f'Failed to check if "{receiver_name}" is a participant or is the same as the participant',
            params={'receiver_name': receiver_name, 'person_id': person_id},
            fetch_one=True
        )

        # If the result is None, either the receiver doesn't exist or is the same as the participant
        return result is not None

    def check_duplicate_receiver(self, person_id: int, year: int) -> bool:
        """
        Check if a receiver for the given person_id already exists for the specified year.
        """
        query = """
            SELECT COUNT(*) FROM Receiver WHERE person_id = :person_id AND year = :year
        """
        result = self._execute_query(
            query,
            f'Checked for duplicate receiver for person_id {person_id} and year {year}',
            f'Error checking for duplicate receiver for person_id {person_id} and year {year}',
            {'person_id': person_id, 'year': year},
            fetch_one=True
        )

        return result[0] if result[0] > 0 else False

    def get_role(self, name: str) -> Optional[str]:
        """
        Get the role (admin or participant) for a given participant by name.

        Parameters:
            name (str): The name of the participant.

        Returns:
            Optional[str]: The role of the participant if found, or None if not found.
        """
        query = """
            SELECT role FROM Participant WHERE name = :name
        """
        result = self._execute_query(
            query,
            f'Role fetched for participant "{name}"',
            f'Failed to fetch role for participant "{name}"',
            {'name': name},
            fetch_one=True
        )
        return result[0] if result else None

    def get_all_participants(self) -> Optional[List[Tuple[int, str]]]:
        """
        Fetch all participants from the Participant table.

        Returns:
            Optional[List[Tuple[int, str]]]: A list of tuples where each tuple contains the ID and name of a participant.
        """
        query = "SELECT id, name, role FROM Participant"
        return self._execute_query(
            query,
            'Fetched participants',
            'Failed to fetch participants'
        )

    def get_receivers_for_participant(self, person_id: int) -> list[tuple] | None:
        """
        Fetch all past receivers for a participant, including the year.
        """
        query = """
            SELECT receiver_name, year FROM Receiver WHERE person_id = :person_id
        """
        return self._execute_query(
            query,
            f'Fetched receivers for participant {person_id}',
            f'Failed to fetch receivers for participant {person_id}',
            {'person_id': person_id}
        )

    def get_participants_count(self) -> int:
        """
        Count the number of participants in the Participant table.

        Returns:
            int: The total number of participants in the Participant table.
        """
        query = "SELECT count(*) FROM Participant"
        count = self._execute_query(
            query,
            'Checked participants count',
            'Failed to get participants count',
            fetch_one=True
        )
        return count[0] if count else 0

    def get_participant_id(self, name: str) -> Optional[int]:
        """
        Fetch the ID of a participant by their name from the Participant table.

        Parameters:
            name (str): The name of the participant to look up.

        Returns:
            Optional[int]: The ID of the participant if found, or None if not found.
        """
        query = "SELECT id FROM Participant WHERE name = :name"
        person_id = self._execute_query(
            query,
            f'Fetched person_id for {name}',
            'Failed to fetch person_id',
            {'name': name},
            fetch_one=True
        )
        return person_id[0] if person_id else None

    def get_participant_by_id(self, person_id: int) -> Optional[Tuple[int, str, str]]:
        """
        Fetch a participant by their ID.

        Parameters:
            person_id (int): The persons id

        Returns:
            Optional[Tuple[int, str, str]]: A tuple containing the ID, name, and role of the participant.
        """
        query = "SELECT id, name, role FROM Participant WHERE id = :person_id"
        result = self._execute_query(
            query,
            f'Fetched participant with ID {person_id}',
            f'Failed to fetch participant with ID {person_id}',
            {'person_id': person_id},
            fetch_one=True
        )
        return result

    def update_participant(self, person_id: int, name: str, password: str, role: str):
        """
        Update a participant's details in the database.

        Parameters:
            person_id (int): The ID of the participant to update.
            name (str): The new name of the participant.
            password (str): The new password of the participant.
            role (str): The new role of the participant.
        """
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        update_query = """
            UPDATE Participant
            SET name = :name, password = :password, role = :role
            WHERE id = :person_id
        """
        self._execute_query(
            update_query,
            f'Updated participant "{name}" with ID {person_id}',
            f'Failed to update participant with ID {person_id}',
            {'name': name, 'password': hashed, 'role': role, 'person_id': person_id}
        )
