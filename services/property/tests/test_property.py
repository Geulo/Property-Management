import pytest

from src.property import add_property, delete_property, get_property, list_properties
from src.task import add_task, list_tasks


def test_add_and_list_property(connection, user_id):
    add_property(connection, user_id, "Canal House", "Prinsengracht 1, Amsterdam")
    properties = list_properties(connection, user_id)
    assert len(properties) == 1
    assert properties[0]["property_name"] == "Canal House"


def test_input_is_trimmed(connection, user_id):
    property_id = add_property(connection, user_id, "  Canal House ", " Prinsengracht 1 ")
    found = get_property(connection, property_id, user_id)
    assert found["property_name"] == "Canal House"
    assert found["address"] == "Prinsengracht 1"


@pytest.mark.parametrize("name, address", [("", "Street 1"), ("House", ""), ("   ", "   "), (None, None)])
def test_missing_fields_rejected(connection, user_id, name, address):
    with pytest.raises(ValueError, match="required"):
        add_property(connection, user_id, name, address)


def test_name_too_long_rejected(connection, user_id):
    with pytest.raises(ValueError, match="at most"):
        add_property(connection, user_id, "x" * 51, "Street 1")


def test_list_is_sorted_by_name(connection, user_id):
    add_property(connection, user_id, "Zuid Flat", "Street 2")
    add_property(connection, user_id, "Amstel Loft", "Street 1")
    names = [p["property_name"] for p in list_properties(connection, user_id)]
    assert names == ["Amstel Loft", "Zuid Flat"]


def test_users_only_see_their_own_properties(connection, user_id, other_user_id):
    property_id = add_property(connection, user_id, "Canal House", "Street 1")
    assert list_properties(connection, other_user_id) == []
    assert get_property(connection, property_id, other_user_id) is None


def test_delete_property(connection, user_id):
    property_id = add_property(connection, user_id, "Canal House", "Street 1")
    assert delete_property(connection, property_id, user_id) is True
    assert list_properties(connection, user_id) == []


def test_cannot_delete_other_users_property(connection, user_id, other_user_id):
    property_id = add_property(connection, user_id, "Canal House", "Street 1")
    assert delete_property(connection, property_id, other_user_id) is False
    assert get_property(connection, property_id, user_id) is not None


def test_deleting_property_cascades_to_its_tasks(connection, user_id):
    property_id = add_property(connection, user_id, "Canal House", "Street 1")
    add_task(connection, property_id, "Fix boiler")
    delete_property(connection, property_id, user_id)
    assert list_tasks(connection, property_id) == []
