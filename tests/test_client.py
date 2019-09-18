from unittest.mock import Mock, patch
import pytest
import requests
import asynctest
import aiohttp
from fonz.client import LookerClient
from fonz.exceptions import ApiConnectionError

TEST_BASE_URL = "https://test.looker.com"
TEST_CLIENT_ID = "test_client_id"
TEST_CLIENT_SECRET = "test_client_secret"


@pytest.fixture
def client(monkeypatch):
    mock_authenticate = Mock(spec=LookerClient.authenticate)
    monkeypatch.setattr(LookerClient, "authenticate", mock_authenticate)
    return LookerClient(TEST_BASE_URL, TEST_CLIENT_ID, TEST_CLIENT_SECRET)


@pytest.fixture
def mock_response():
    mock = Mock(spec=requests.Response)
    mock.status_code = 404
    mock.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "An HTTP error occurred."
    )
    return mock


@patch("fonz.client.requests.Session.post")
def test_bad_authenticate_raises_connection_error(mock_post, mock_response):
    mock_post.return_value = mock_response
    with pytest.raises(ApiConnectionError):
        LookerClient(TEST_BASE_URL, TEST_CLIENT_ID, TEST_CLIENT_SECRET)
    mock_response.raise_for_status.assert_called_once()


@patch("fonz.client.requests.Session.post")
def test_authenticate_sets_session_headers(mock_post):
    mock_response = Mock(spec=requests.Response)
    mock_response.json.return_value = {"access_token": "test_access_token"}
    mock_post.return_value = mock_response
    client = LookerClient(TEST_BASE_URL, TEST_CLIENT_ID, TEST_CLIENT_SECRET)
    assert client.session.headers == {"Authorization": f"token test_access_token"}


@patch("fonz.client.requests.Session.patch")
def test_bad_update_session_patch_raises_connection_error(
    mock_patch, client, mock_response
):
    mock_patch.return_value = mock_response
    with pytest.raises(ApiConnectionError):
        client.update_session(project="test_project", branch="test_branch")
    mock_response.raise_for_status.assert_called_once()


@patch("fonz.client.requests.Session.patch")
@patch("fonz.client.requests.Session.put")
def test_bad_update_session_put_raises_connection_error(
    mock_put, mock_patch, client, mock_response
):
    mock_put.return_value = mock_response
    with pytest.raises(ApiConnectionError):
        client.update_session(project="test_project", branch="test_branch")
    mock_response.raise_for_status.assert_called_once()


@patch("fonz.client.requests.Session.get")
def test_bad_get_models_raises_connection_error(mock_get, client, mock_response):
    mock_get.return_value = mock_response
    with pytest.raises(ApiConnectionError):
        client.get_models()
    mock_response.raise_for_status.assert_called_once()


@patch("fonz.client.requests.Session.get")
def test_bad_get_dimensions_raises_connection_error(mock_get, client, mock_response):
    mock_get.return_value = mock_response
    with pytest.raises(ApiConnectionError):
        client.get_dimensions(model="test_model", explore="test_explore")
    mock_response.raise_for_status.assert_called_once()


@pytest.mark.asyncio
@asynctest.patch("aiohttp.ClientSession.post")
async def test_create_query(mock_post, client):
    QUERY_ID = 124950204921
    mock_post.return_value.__aenter__.return_value.json = asynctest.CoroutineMock(
        return_value={"id": QUERY_ID}
    )
    async with aiohttp.ClientSession() as session:
        query_id = await client.create_query(
            session,
            "test_model",
            "test_explore_one",
            ["dimension_one", "dimension_two"],
        )
    assert query_id == QUERY_ID
    mock_post.assert_called_once_with(
        url="https://test.looker.com:19999/api/3.1/queries",
        json={
            "model": "test_model",
            "view": "test_explore_one",
            "fields": ["dimension_one", "dimension_two"],
            "limit": 1,
        },
    )


@pytest.mark.asyncio
@asynctest.patch("aiohttp.ClientSession.post")
async def test_run_query(mock_post, client):
    QUERY_ID = 124950204921
    QUERY_TASK_ID = "a1ds2d49d5d02wdf0we4a921e"
    mock_post.return_value.__aenter__.return_value.json = asynctest.CoroutineMock(
        return_value={"id": QUERY_TASK_ID}
    )
    async with aiohttp.ClientSession() as session:
        query_task_id = await client.run_query(session, QUERY_ID)
    assert query_task_id == QUERY_TASK_ID
    mock_post.assert_called_once_with(
        url="https://test.looker.com:19999/api/3.1/query_tasks",
        json={"query_id": QUERY_ID, "result_format": "json"},
    )
