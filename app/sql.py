import logging
import sqlite3
from typing import Optional, List, Tuple, Dict, Any


class SqlStatements:
    """
    Class containing SQL statements and methods
    """
    # logging setup
    _sql_logger = logging.getLogger('sql')
    _sql_logger.info('Logging setup complete')

    # sqlite connection
    try:
        _sql_logger.debug('Setting up sql connection')
        _sqlite_connection = sqlite3.connect('../instance/secret_santa.db')
        cursor = _sqlite_connection.cursor()
        _sql_logger.info('Setup of sql connection complete')
    except sqlite3.Error as error:
        _sql_logger.error(f'Connection to database failed: {error}')

    @staticmethod
    def _execute_query(
            query: str,
            success_message: str = 'Success',
            error_message: str = 'Error',
            params: Optional[Dict[str, Any]] = None,
            fetch_one: bool = False,
    ) -> Optional[List[Tuple]]:
        """
        Execute a SQL query and return the result.

        Parameters:
            query (str): The SQL query to execute.
            success_message (str, optional): Success message to log. Defaults to 'Success'.
            error_message (str, optional): Error message to log. Defaults to 'Error'.
            params (Dict[str, Any], optional): Parameters for the query as a dictionary of parameter names
                and values. Defaults to None.
            fetch_one (bool, optional): Whether to fetch only one result. Defaults to False.

        Returns:
            Optional[List[Tuple]]: A list of tuples containing the result of the query, or None if an error occurred.
        """
        try:
            with SqlStatements._sqlite_connection:
                if params:
                    SqlStatements.cursor.execute(query, params)
                else:
                    SqlStatements.cursor.execute(query)

                if fetch_one:
                    result = SqlStatements.cursor.fetchone()
                else:
                    result = SqlStatements.cursor.fetchall()

                SqlStatements._sql_logger.info(success_message)
                if result:
                    SqlStatements._sql_logger.debug(f'Result: {result}')
                return result

        except sqlite3.Error as error:
            SqlStatements._sql_logger.error(f'{error_message}: {error}')
            return None

    @staticmethod
    def create_tables():
        """
        Create tables for the Person and Assignment database.
        """

        # Create Person table
        person_table_script = """
            create table if not exists Person (
                id integer primary key autoincrement,
                name text unique not null
            );"""
        SqlStatements._execute_query(
            person_table_script,
            'Person table created',
            'Failed to create Person table'
        )

        # Create Assignment table
        receiver_table_script = """
            create table if not exists receiver (
                id integer primary key autoincrement,
                person_id integer not null,
                receiver_name text not null,
                foreign key (person_id) references Person(id)
            );"""
        SqlStatements._execute_query(
            receiver_table_script,
            'Assignment table created',
            'Failed to create Assignment table'
        )

    @staticmethod
    def add_name(name: str):
        """
        Add a person's name to the Person table.

        Parameters:
            name (str): The name of the person to add.
        """
        insert_query = """
            insert into Person (name) 
            values (:name)
        """
        SqlStatements._execute_query(
            insert_query,
            f'Name "{name}" added to Person table',
            f'Failed to add name "{name}"',
            {'name': name}
        )

    @staticmethod
    def add_receiver(person_id: int, receiver_name: str):
        """
        Add the past year's receiver's name to the receiver table.

        Parameters:
            person_id (int): The ID of the person.
            receiver_name (str): The name of the person they were assigned in the previous year.
        """
        insert_query = """
            insert into receiver (person_id, receiver_name) 
            values (:person_id, :receiver_name)
        """
        SqlStatements._execute_query(
            insert_query,
            f'Receiver "{receiver_name}" added for person with ID {person_id}',
            f'Failed to add receiver "{receiver_name}" for person with ID {person_id}',
            {'person_id': person_id, 'receiver_name': receiver_name}
        )

    @staticmethod
    def get_all_participants() -> list | None:
        """
        Fetch all participants from the Person table.

        Returns:
            list: A list of tuples where each tuple contains the ID and name of a participant.
        """
        query = "select id, name from Person"

        participants = SqlStatements._execute_query(
            query,
            'Fetched participants',
            'Failed to fetch participants'
        )

        return participants

    @staticmethod
    def get_past_receivers_for_person(person_id: int) -> List[str]:
        """
        Fetch past receivers for a specific person from the receiver table.

        Parameters:
            person_id (int): The ID of the person to fetch receivers for.

        Returns:
            List[str]: A list of past receiver names for the given person.
        """
        query = """
            select receiver_name from receiver
            where person_id = :person_id
        """
        past_receivers = SqlStatements._execute_query(
            query,
            f"Fetched past receivers for person_id {person_id}",
            f'Failed to fetch past receivers for person_id {person_id}',
            {'person_id': person_id}
        )
        return [row[0] for row in past_receivers] if past_receivers else []

    @staticmethod
    def get_participants_count() -> tuple:
        """
        Count the number of participants in the Person table.

        Returns:
            int: The number of participants.
        """
        query = "select count(*) from Person"
        count = SqlStatements._execute_query(
            query,
            f'Checked participants count',
            f'Failed to get participants count',
            fetch_one=True
        )
        return count[0]

    @staticmethod
    def get_person_id_by_name(name: str) -> tuple:
        """
        Fetch the ID of a person by their name from the Person table.

        Parameters:
            name (str): The name of the person to fetch the ID for.

        Returns:
            Optional[int]: The ID of the person, or None if not found.
        """
        query = "select id from Person where name = :name"
        person_id = SqlStatements._execute_query(
            query,
            f"Fetched person_id for {name}",
            f'Fetching of person_id',
            {'name': name},
            True
        )

        return person_id[0]
