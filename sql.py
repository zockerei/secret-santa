import logging
import sqlite3
from typing import Optional, List, Tuple, Dict, Any


class SqlStatements:
    """
    Class containing SQL statements and methods
    """
    # Logging setup
    _sql_logger = logging.getLogger(__name__)
    _sql_logger.info('Logging setup complete')

    def __init__(self, db_path):
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
        Execute a SQL query and return the result.
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
            CREATE TABLE IF NOT EXISTS Person (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
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

    def add_name(self, name: str):
        """
        Add a person's name to the Person table.
        """
        insert_query = """
            INSERT INTO Person (name) 
            VALUES (:name)
        """
        self._execute_query(
            insert_query,
            f'Name "{name}" added to Person table',
            f'Failed to add name "{name}"',
            {'name': name}
        )

    def add_receiver(self, person_id: int, receiver_name: str):
        """
        Add the past year's receiver's name to the receiver table.
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

    def get_all_participants(self) -> Optional[List[Tuple[int, str]]]:
        """
        Fetch all participants from the Person table.
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
        """
        query = """
            SELECT receiver_name FROM receiver
            WHERE person_id = :person_id
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
        """
        query = "SELECT COUNT(*) FROM Person"
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
        """
        query = "SELECT id FROM Person WHERE name = :name"
        person_id = self._execute_query(
            query,
            f'Fetched person_id for {name}',
            'Failed to fetch person_id',
            {'name': name},
            fetch_one=True
        )
        return person_id[0] if person_id else None
