import logging
import sqlite3
from typing import Optional, List, Tuple, Dict, Any
import bcrypt


class SqlStatements:
    """
    Class containing SQL statements and methods
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
        """
        Create tables for the Person and Assignment database.
        """
        person_table_script = """
            CREATE TABLE IF NOT EXISTS Participant (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL -- "admin" or "member"
            );
        """
        self._execute_query(
            person_table_script,
            'Person table created',
            'Failed to create Person table'
        )

        receiver_table_script = """
            CREATE TABLE IF NOT EXISTS receiver (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                receiver_name TEXT NOT NULL,
                FOREIGN KEY (person_id) REFERENCES Person(id)
            );
        """
        self._execute_query(
            receiver_table_script,
            'Receiver table created',
            'Failed to create receiver table'
        )

    def add_member(self, name: str, password: str, role: str = 'member'):
        """
        Add a member to the participants table.

        Parameters:
            name (str): The name of the member to add.
            password (str): The plain-text password to hash and store.
            role (str): The role of the member, either 'admin' or 'member'. Default is 'member'.
        """
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        insert_query = """
            INSERT INTO participants (name, password, role)
            VALUES (:name, :password, :role)
        """
        self._execute_query(
            insert_query,
            f'Added member "{name}" with role "{role}"',
            f'Failed to add member "{name}"',
            {'name': name, 'password': hashed, 'role': role}
        )

    def add_receiver(self, person_id: int, receiver_name: str):
        """
        Add a receiver's name to the receiver table for a specific person.

        Parameters:
            person_id (int): The ID of the person in the Person table.
            receiver_name (str): The name of the receiver to add for the person.
        """
        insert_query = """
            INSERT INTO receiver (person_id, receiver_name) 
            VALUES (:person_id, :receiver_name)
        """
        self._execute_query(
            insert_query,
            f'Receiver "{receiver_name}" added for person with ID {person_id}',
            f'Failed to add receiver "{receiver_name}" for person with ID {person_id}',
            {'person_id': person_id, 'receiver_name': receiver_name}
        )

    def remove_member(self, person_id: int):
        """
        Remove a member from the Person table and associated receivers.

        Parameters:
            person_id (int): The ID of the person to remove.
        """
        # Remove associated receivers first to maintain referential integrity
        delete_receivers_query = """
            delete from receiver where person_id = :person_id
        """
        self._execute_query(
            delete_receivers_query,
            f'Removed receivers for person_id {person_id}',
            f'Failed to remove receivers for person_id {person_id}',
            {'person_id': person_id}
        )

        # Now remove the member from the Person table
        delete_person_query = """
            delete from Person where id = :person_id
        """
        self._execute_query(
            delete_person_query,
            f'Removed person with ID {person_id} from Person table',
            f'Failed to remove person with ID {person_id}',
            {'person_id': person_id}
        )

    def remove_receiver(self, person_id: int, receiver_name: str):
        """
        Remove a specific receiver for a given person from the receiver table.

        Parameters:
            person_id (int): The ID of the person whose receiver should be removed.
            receiver_name (str): The name of the receiver to remove.
        """
        delete_receiver_query = """
            DELETE FROM receiver WHERE person_id = :person_id AND receiver_name = :receiver_name
        """
        self._execute_query(
            delete_receiver_query,
            f'Removed receiver "{receiver_name}" for person_id {person_id}',
            f'Failed to remove receiver "{receiver_name}" for person_id {person_id}',
            {'person_id': person_id, 'receiver_name': receiver_name}
        )

    def verify_member(self, name: str, password: str) -> bool:
        """
        Verify if a member's name and password match a record in the participants table.

        Parameters:
            name (str): The name of the member.
            password (str): The plain-text password to verify.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        query = """
            SELECT password FROM participants WHERE name = :name
        """
        result = self._execute_query(
            query,
            f'Password fetched for member "{name}"',
            f'Failed to fetch password for member "{name}"',
            {'name': name},
            fetch_one=True
        )
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0]):
            return True
        return False

    def get_role(self, name: str) -> Optional[str]:
        """
        Get the role (admin or member) for a given member by name.

        Parameters:
            name (str): The name of the member.

        Returns:
            Optional[str]: The role of the member if found, or None if not found.
        """
        query = """
            SELECT role FROM participants WHERE name = :name
        """
        result = self._execute_query(
            query,
            f'Role fetched for member "{name}"',
            f'Failed to fetch role for member "{name}"',
            {'name': name},
            fetch_one=True
        )
        return result[0] if result else None

    def get_all_participants(self) -> Optional[List[Tuple[int, str]]]:
        """
        Fetch all participants from the Person table.

        Returns:
            Optional[List[Tuple[int, str]]]: A list of tuples where each tuple contains the ID and name of a person.
        """
        query = "SELECT id, name FROM Person"
        return self._execute_query(
            query,
            'Fetched participants',
            'Failed to fetch participants'
        )

    def get_past_receivers_for_person(self, person_id: int) -> List[str]:
        """
        Fetch past receivers for a specific person from the receiver table.

        Parameters:
            person_id (int): The ID of the person to fetch receivers for.

        Returns:
            List[str]: A list of receiver names associated with the given person ID.
        """
        query = """
            select receiver_name from receiver
            where person_id = :person_id
        """
        past_receivers = self._execute_query(
            query,
            f'Fetched past receivers for person_id {person_id}',
            f'Failed to fetch past receivers for person_id {person_id}',
            {'person_id': person_id}
        )
        return [row[0] for row in past_receivers] if past_receivers else []

    def get_participants_count(self) -> int:
        """
        Count the number of participants in the Person table.

        Returns:
            int: The total number of participants in the Person table.
        """
        query = "select count(*) from Person"
        count = self._execute_query(
            query,
            'Checked participants count',
            'Failed to get participants count',
            fetch_one=True
        )
        return count[0] if count else 0

    def get_person_id_by_name(self, name: str) -> Optional[int]:
        """
        Fetch the ID of a person by their name from the Person table.

        Parameters:
            name (str): The name of the person to look up.

        Returns:
            Optional[int]: The ID of the person if found, or None if not found.
        """
        query = "select id from Person where name = :name"
        person_id = self._execute_query(
            query,
            f'Fetched person_id for {name}',
            'Failed to fetch person_id',
            {'name': name},
            fetch_one=True
        )
        return person_id[0] if person_id else None
