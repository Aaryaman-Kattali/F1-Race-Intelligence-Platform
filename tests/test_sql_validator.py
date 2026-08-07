import os
from src.agent.query_agent import validate_sql_is_select


def test_validate_sql_is_select():
    # Test valid queries
    assert (
        validate_sql_is_select("SELECT * FROM f1_raw_marts.driver_circuit_performance")
        == True
    )
    assert validate_sql_is_select("WITH cte AS (SELECT 1) SELECT * FROM cte") == True

    # Test invalid queries
    assert (
        validate_sql_is_select("DELETE FROM f1_raw_marts.driver_circuit_performance")
        == False
    )
    assert (
        validate_sql_is_select("DROP TABLE f1_raw_marts.driver_circuit_performance")
        == False
    )
    assert (
        validate_sql_is_select(
            "UPDATE f1_raw_marts.driver_circuit_performance SET avg_finish = 1"
        )
        == False
    )
    assert (
        validate_sql_is_select("SELECT * FROM my_table; DROP TABLE my_table;") == False
    )

    print("validate_sql_is_select passed all unit tests!")


if __name__ == "__main__":
    test_validate_sql_is_select()
